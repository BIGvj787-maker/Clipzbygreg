# TikTok LIVE AI Clipping Bot — Starter

A real starter backend for automatic TikTok LIVE recording, Drive storage, Make events, timestamp-grounded AI moment selection, FFmpeg clipping, and Telegram delivery.

**Important:** TikTok LIVE detection/capture is deliberately provider-neutral. There is no assumed official recording API here. You must plug in a current, authorized capture/status implementation. This project does not bypass authentication, DRM, access controls, or other protections.

## 1. Install

Python 3.11+ is recommended.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Install FFmpeg and ensure `ffmpeg` is on PATH.

## 2. Configure .env

Copy `.env.example` to `.env` and set Telegram, OpenAI, Google Drive, Make, and storage values. Never commit `.env`.

## 3. Telegram

Create a bot with Telegram's BotFather, copy its token to `TELEGRAM_BOT_TOKEN`, start a chat with the bot, and set `TELEGRAM_CHAT_ID` to the destination chat ID if you add your own notification/delivery handler.

The command handlers included here cover the requested management commands. Wire your preferred Telegram delivery code into the pipeline for automatic videos.

## 4. Google Drive

Create a Google Cloud project, enable Google Drive API, create a service account, download its JSON key, and set `GOOGLE_SERVICE_ACCOUNT_JSON` to its local path. Share the target Drive folder with the service-account email. Optionally set `GOOGLE_DRIVE_ROOT_FOLDER_ID`.

The server, not Make, uploads original recordings. The Drive tree is creator/recordings, creator/analysis, creator/clips.

## 5. OpenAI

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL`. The analyzer uses structured JSON and only accepts moments grounded in timestamped transcript segments.

## 6. Make

Create a custom webhook in Make and put its URL in `MAKE_WEBHOOK_URL`. Set `MAKE_WEBHOOK_SECRET` to a strong random secret. Outgoing events use `X-Webhook-Signature` HMAC-SHA256 and an `Idempotency-Key`.

## 7. FFmpeg

Install FFmpeg through your OS package manager or official distribution, then verify:

```bash
ffmpeg -version
```

## 8. Authorized TikTok LIVE capture

Implement `TikTokLiveCaptureAdapter` in `recorder/capture_adapter.py`. The adapter must write the original LIVE to `output_path` and honor `stop_event`.

Implement `is_live(username)` in `recorder/live_detector.py` using the authorized/current status source available to you.

After these two provider-specific integrations are connected, `/add @username` is intended to be sufficient: the detector monitors enabled creators, starts a DB session and capture when LIVE is detected, and stops/finalizes when LIVE is no longer live.

## 9. Run

```bash
python main.py
```

For the HTTP webhook receiver:

```bash
uvicorn webhooks.server:app --host 0.0.0.0 --port 8000
```

## 10. Local MP4 pipeline test

The included `LocalFileCaptureAdapter` lets you test capture without TikTok:

```python
from recorder.capture_adapter import LocalFileCaptureAdapter
adapter = LocalFileCaptureAdapter("./test.mp4")
```

Then wire that adapter into `RecordingManager`. For a complete end-to-end test, provide a timestamped transcription implementation in `ai/transcription.py`, run analysis, and call `Clipper.create()`.

## Current integration points

- TikTok LIVE status: `recorder/live_detector.py`
- TikTok recording: `recorder/capture_adapter.py`
- Transcription: `ai/transcription.py`
- Automatic orchestration: `recorder/recorder.py`
- AI analysis: `ai/analyzer.py`
- FFmpeg: `clips/clipper.py`
- Drive: `storage/google_drive.py`
- Make events: `pipeline/events.py`
- Telegram commands: `bot/commands.py`

The starter intentionally fails loudly at missing provider boundaries instead of claiming a LIVE was recorded/analyzed/clipped when it was not.
