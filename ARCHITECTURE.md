# Architecture

Telegram commands -> SQLite -> provider-neutral LIVE detector -> RecordingManager -> capture adapter -> original MP4 -> Google Drive -> Make webhook -> timestamped transcription -> OpenAI structured analysis -> FFmpeg -> Telegram.

## Provider boundaries

`recorder/live_detector.py` exposes `is_live(username)`. Implement it with an authorized/current TikTok LIVE status mechanism.

`recorder/capture_adapter.py` exposes `TikTokLiveCaptureAdapter.record()`. Implement it with a capture mechanism you are authorized to use. No authentication bypass, DRM circumvention, or access-control evasion is included.

`ai/transcription.py` requires a transcription provider that returns timestamped segments. The analyzer rejects ungrounded/no-segment input.

## Idempotency

LIVE sessions receive unique database session IDs. The database prevents duplicate session IDs. Make events include an HMAC signature and deterministic idempotency key.

## Production note

Run a persistent worker/process supervisor and move webhook idempotency keys into SQLite/Redis rather than in-memory state for multi-instance deployments.
