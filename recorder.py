import asyncio, uuid
from pathlib import Path
from datetime import datetime, timezone
from database.database import SessionLocal, Creator, Session
from pipeline.events import emit_event
from config import settings

class RecordingManager:
    def __init__(self, adapter, notifier=None):
        self.adapter = adapter
        self.notifier = notifier
        self.active = {}
        self._locks = {}

    async def ensure_started(self, username):
        with SessionLocal() as db:
            creator = db.query(Creator).filter_by(username=username).first()
            if not creator: return
            existing = db.query(Session).filter_by(creator_id=creator.id).filter(Session.status.in_(["recording","finalizing"])).first()
            if existing: return
            sid = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            path = Path(settings.media_dir) / username.lstrip("@") / f"{sid}.mp4"
            path.parent.mkdir(parents=True, exist_ok=True)
            s = Session(creator_id=creator.id, session_id=sid, status="recording", source_path=str(path))
            db.add(s); db.commit(); db.refresh(s)
            self.active[username] = (s.id, asyncio.Event())
        await emit_event("live_started", username, sid)
        await emit_event("recording_started", username, sid)
        if self.notifier: await self.notifier(f"{username} is now LIVE. Recording started automatically.")
        asyncio.create_task(self._record(username, s.id, sid, path, self.active[username][1]))

    async def _record(self, username, db_id, sid, path, stop_event):
        try:
            await self.adapter.record(username, path, stop_event)
            await self._finish(username, db_id, sid)
        except Exception as exc:
            with SessionLocal() as db:
                s=db.get(Session, db_id); s.status="failed"; s.error=str(exc); db.commit()
            await emit_event("recording_failed", username, sid, {"error": str(exc)})
            if self.notifier: await self.notifier(f"Recording failed for {username}: {exc}")
            self.active.pop(username, None)

    async def mark_not_live(self, username):
        item = self.active.get(username)
        if item:
            item[1].set()

    async def stop(self, username):
        item = self.active.get(username)
        if item: item[1].set(); return True
        return False

    async def _finish(self, username, db_id, sid):
        with SessionLocal() as db:
            s=db.get(Session, db_id)
            s.status="completed"; s.ended_at=datetime.now(timezone.utc); db.commit()
            path=Path(s.source_path)
        self.active.pop(username, None)
        await emit_event("recording_completed", username, sid)
        if self.notifier: await self.notifier(f"{username}'s LIVE has ended. Recording saved. AI analysis starting…")
