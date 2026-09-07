import asyncio, subprocess
from pathlib import Path
from database.database import SessionLocal, Session, Creator, Moment
from config import settings

def sec(ts):
    p=[float(x) for x in ts.split(":")]
    return p[-1]+(p[-2] if len(p)>1 else 0)*60+(p[-3] if len(p)>2 else 0)*3600

class Clipper:
    async def create(self, db_session_id, count=None):
        count=count or settings.default_clips
        with SessionLocal() as db:
            s=db.get(Session,db_session_id); creator=db.get(Creator,s.creator_id)
            moments=db.query(Moment).filter_by(session_id=db_session_id).order_by(Moment.rank).limit(count).all()
            source=Path(s.source_path)
            outdir=source.parent/"clips"; outdir.mkdir(exist_ok=True)
        results=[]
        for i,m in enumerate(moments,1):
            out=outdir/f"{creator.username}_clip_{i:02d}.mp4"
            cmd=["ffmpeg","-y","-ss",str(sec(m.start)),"-i",str(source),"-t",str(sec(m.end)-sec(m.start)),
                 "-c:v","libx264","-c:a","aac","-movflags","+faststart",str(out)]
            p=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE)
            _,err=await p.communicate()
            if p.returncode: raise RuntimeError(f"FFmpeg failed for {out.name}: {err.decode()[-1500:]}")
            results.append(out)
        with SessionLocal() as db:
            s=db.get(Session,db_session_id); s.clipping_status="completed"; db.commit()
        return results
