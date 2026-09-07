# Local MP4 smoke test

1. Put a short MP4 at `./test.mp4`.
2. Use `LocalFileCaptureAdapter("./test.mp4")`.
3. Use a real timestamped transcription provider or a fixture implementing `Transcriber`.
4. Call `AIAnalyzer(transcriber).analyze(session_id)`.
5. Call `Clipper().create(session_id, 3)`.
6. Confirm clips are under the recording directory and the source MP4 is unchanged.

A transcription fixture can return segments such as:

```text
0.0-12.0: Intro
12.0-28.0: Argument starts
28.0-44.0: Strong reaction
```

Do not let the AI create timestamps independently; the analyzer's input must always be timestamped segments from the actual media.
