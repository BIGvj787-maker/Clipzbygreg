import asyncio, logging
from typing import Callable
from database.database import SessionLocal, Creator
from recorder.recorder import RecordingManager

log = logging.getLogger(__name__)

class LiveDetector:
    """Provider-neutral detector. Plug in an authorized TikTok LIVE status provider."""
    def __init__(self, recorder: RecordingManager, is_live: Callable[[str], bool]):
        self.recorder, self.is_live = recorder, is_live

    async def run(self, stop_event):
        while not stop_event.is_set():
            with SessionLocal() as db:
                creators = [c.username for c in db.query(Creator).filter_by(enabled=True).all()]
            for username in creators:
                try:
                    live = await asyncio.to_thread(self.is_live, username)
                    if live:
                        await self.recorder.ensure_started(username)
                    else:
                        await self.recorder.mark_not_live(username)
                except Exception:
                    log.exception("LIVE detection failed for %s", username)
            await asyncio.sleep(30)

def unavailable_live_status(username: str) -> bool:
    raise RuntimeError("No authorized LIVE status provider configured for TikTok: " + username)
