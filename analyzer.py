import json, re
from openai import AsyncOpenAI
from database.database import SessionLocal, Session, Creator, Moment
from config import settings
from pipeline.events import emit_event

def _seconds(ts):
    p=[float(x) for x in ts.split(":")]
    return p[-1] + (p[-2] if len(p)>1 else 0)*60 + (p[-3] if len(p)>2 else 0)*3600

class AIAnalyzer:
    def __init__(self, transcriber):
        self.transcriber=transcriber
        self.client=AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(self, db_session_id):
        with SessionLocal() as db:
            s=db.get(Session, db_session_id); creator=db.get(Creator, s.creator_id)
            video=s.source_path; username=creator.username; sid=s.session_id
            s.analysis_status="running"; db.commit()
        try:
            segments=await self.transcriber.transcribe(video)
            if not segments: raise RuntimeError("Transcription returned no timestamped segments.")
            transcript="\n".join(f"[{x.start:.2f}-{x.end:.2f}] {x.text}" for x in segments)
            schema={
              "type":"object","additionalProperties":False,
              "properties":{"creator":{"type":"string"},"recording_id":{"type":"string"},
                "best_moments":{"type":"array","items":{"type":"object","additionalProperties":False,
                  "properties":{"rank":{"type":"integer"},"start":{"type":"string"},"end":{"type":"string"},
                    "description":{"type":"string"},"reason":{"type":"string"},"score":{"type":"number"}},
                  "required":["rank","start","end","description","reason","score"]}}},
              "required":["creator","recording_id","best_moments"]}
            prompt=("Select the strongest short-form moments. Use ONLY timestamp ranges that appear in the transcript. "
                    "Do not invent or extrapolate timestamps. Keep clips <= 90 seconds and prefer self-contained moments. "
                    "Return JSON matching the schema.\nTRANSCRIPT:\n"+transcript)
            resp=await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role":"system","content":"You are a precise video editor. Timestamps must be grounded in supplied segments."},
                          {"role":"user","content":prompt}],
                response_format={"type":"json_schema","json_schema":{"name":"moments","strict":True,"schema":schema}})
            data=json.loads(resp.choices[0].message.content)
            valid=[]
            for m in data["best_moments"]:
                st,en=_seconds(m["start"]),_seconds(m["end"])
                if en>st and en-st<=settings.max_clip_seconds:
                    if any(st >= x.start-0.25 and en <= x.end+0.25 for x in segments) or any(st>=x.start and en<=max(y.end for y in segments if y.start<=en) for x in segments):
                        valid.append(m)
            with SessionLocal() as db:
                s=db.get(Session,db_session_id)
                for m in valid:
                    db.add(Moment(session_id=db_session_id, **m))
                s.analysis_status="completed"; db.commit()
            await emit_event("analysis_completed", username, sid, {"count":len(valid)})
            return valid
        except Exception as exc:
            with SessionLocal() as db:
                s=db.get(Session,db_session_id); s.analysis_status="failed"; s.error=str(exc); db.commit()
            await emit_event("analysis_completed", username, sid, {"status":"failed","error":str(exc)})
            raise
