import asyncio
from dotenv import load_dotenv
load_dotenv()
from database.database import init_db
from bot.telegram_bot import build_bot
from recorder.capture_adapter import TikTokLiveCaptureAdapter
from recorder.recorder import RecordingManager

class NotConfiguredCapture(TikTokLiveCaptureAdapter):
    async def record(self, username, output_path, stop_event):
        raise RuntimeError("Authorized TikTok LIVE capture adapter is not configured.")

async def main():
    init_db()
    app=build_bot()
    # Detector/capture wiring is intentionally provider-neutral.
    # Replace NotConfiguredCapture and unavailable_live_status with authorized integrations.
    await app.initialize(); await app.start(); await app.updater.start_polling()
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop(); await app.stop(); await app.shutdown()

if __name__=="__main__": asyncio.run(main())
