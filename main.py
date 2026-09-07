import os
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Clipz by Greg")

monitored_creators = set()
recordings = {}
recording_sessions = {}
clips = {}

RECORDINGS_DIR = Path("recordings")
CLIPS_DIR = Path("clips")

RECORDINGS_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)


class CreatorRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    username: str


class RecordingRequest(BaseModel):
    username: str


def now():
    return datetime.now(timezone.utc).isoformat()


@app.get("/", response_class=HTMLResponse)
def home():
    creator_count = len(monitored_creators)
    recording_count = len(recordings)
    active_count = len(recording_sessions)
    clip_count = len(clips)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clipz by Greg</title>

<style>
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    font-family: Arial, Helvetica, sans-serif;
    background:
        radial-gradient(circle at top left, #39206b 0%, transparent 35%),
        radial-gradient(circle at bottom right, #142b55 0%, transparent 35%),
        #08080d;
    color: white;
    min-height: 100vh;
}}

.nav {{
    height: 76px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 7%;
    border-bottom: 1px solid rgba(255,255,255,.08);
    background: rgba(8,8,13,.72);
    backdrop-filter: blur(14px);
}}

.logo {{
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -1px;
}}

.logo span {{
    color: #8b5cf6;
}}

.nav a {{
    color: #aaa;
    text-decoration: none;
    margin-left: 25px;
    font-size: 14px;
}}

.nav a:hover {{
    color: white;
}}

.hero {{
    padding: 85px 7% 55px;
    max-width: 1200px;
    margin: auto;
}}

.badge {{
    display: inline-block;
    padding: 8px 13px;
    border: 1px solid rgba(139,92,246,.4);
    background: rgba(139,92,246,.1);
    color: #b99cff;
    border-radius: 999px;
    font-size: 13px;
    margin-bottom: 22px;
}}

h1 {{
    font-size: clamp(45px, 7vw, 78px);
    line-height: .98;
    letter-spacing: -4px;
    max-width: 850px;
}}

.gradient {{
    background: linear-gradient(90deg, #fff, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    color: transparent;
}}

.subtitle {{
    color: #a4a4b2;
    font-size: 18px;
    line-height: 1.6;
    max-width: 650px;
    margin-top: 25px;
}}

.buttons {{
    display: flex;
    gap: 12px;
    margin-top: 32px;
    flex-wrap: wrap;
}}

.button {{
    text-decoration: none;
    padding: 14px 21px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 14px;
}}

.primary {{
    background: white;
    color: #08080d;
}}

.secondary {{
    border: 1px solid #30303c;
    color: white;
    background: rgba(255,255,255,.04);
}}

.stats {{
    max-width: 1200px;
    margin: 20px auto 70px;
    padding: 0 7%;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}}

.card {{
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.09);
    border-radius: 20px;
    padding: 25px;
    backdrop-filter: blur(12px);
}}

.stat-number {{
    font-size: 32px;
    font-weight: 800;
}}

.stat-label {{
    color: #858592;
    margin-top: 7px;
    font-size: 13px;
}}

.section {{
    max-width: 1200px;
    margin: auto;
    padding: 0 7% 80px;
}}

.section h2 {{
    font-size: 30px;
    margin-bottom: 10px;
}}

.section p {{
    color: #858592;
}}

.features {{
    margin-top: 25px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}}

.feature h3 {{
    margin-bottom: 10px;
}}

.feature p {{
    line-height: 1.5;
    font-size: 14px;
}}

.icon {{
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border-radius: 12px;
    background: rgba(139,92,246,.15);
    margin-bottom: 18px;
    color: #a78bfa;
    font-weight: 800;
}}

footer {{
    border-top: 1px solid rgba(255,255,255,.08);
    padding: 25px 7%;
    color: #666673;
    font-size: 13px;
}}

@media (max-width: 750px) {{
    .stats,
    .features {{
        grid-template-columns: 1fr;
    }}

    .nav {{
        padding: 0 5%;
    }}

    .nav-links {{
        display: none;
    }}

    .hero {{
        padding-top: 60px;
    }}

    h1 {{
        letter-spacing: -2px;
    }}
}}
</style>
</head>

<body>

<nav class="nav">
    <div class="logo">Clipz <span>by Greg</span></div>

    <div class="nav-links">
        <a href="/docs">API</a>
        <a href="/creators">Creators</a>
        <a href="/recordings">Recordings</a>
        <a href="/clips">Clips</a>
    </div>
</nav>

<section class="hero">
    <div class="badge">● CLIPZ BY GREG IS ONLINE</div>

    <h1>
        Turn moments into
        <span class="gradient">clips.</span>
    </h1>

    <p class="subtitle">
        A creator-focused recording and clipping platform built to organize
        recordings, find the best moments, and turn them into shareable clips.
    </p>

    <div class="buttons">
        <a class="button primary" href="/docs">Open Dashboard API</a>
        <a class="button secondary" href="/creators">View Creators</a>
    </div>
</section>

<section class="stats">

    <div class="card">
        <div class="stat-number">{creator_count}</div>
        <div class="stat-label">Creators monitored</div>
    </div>

    <div class="card">
        <div class="stat-number">{recording_count}</div>
        <div class="stat-label">Recordings saved</div>
    </div>

    <div class="card">
        <div class="stat-number">{active_count}</div>
        <div class="stat-label">Active sessions</div>
    </div>

    <div class="card">
        <div class="stat-number">{clip_count}</div>
        <div class="stat-label">Clips created</div>
    </div>

</section>

<section class="section">

    <h2>Everything in one place.</h2>
    <p>Built to make the clipping workflow simple.</p>

    <div class="features">

        <div class="card feature">
            <div class="icon">01</div>
            <h3>Creator Tracking</h3>
            <p>
                Keep your authorized creators organized and connected
                to their recordings.
            </p>
        </div>

        <div class="card feature">
            <div class="icon">02</div>
            <h3>Recording Manager</h3>
            <p>
                Start and stop recording sessions and connect uploaded
                video files to the correct creator.
            </p>
        </div>

        <div class="card feature">
            <div class="icon">03</div>
            <h3>Smart Clipping</h3>
            <p>
                Create clips from recordings and prepare the system
                for future AI moment detection.
            </p>
        </div>

    </div>
</section>

<footer>
    © 2026 Clipz by Greg · Creator clipping platform
</footer>

</body>
</html>
"""


@app.post("/add-creator")
def add_creator(request: CreatorRequest):
    username = request.username.lstrip("@").strip()

    monitored_creators.add(username)

    return {
        "status": "creator added",
        "username": username,
        "monitoring": True
    }


@app.get("/creators")
def get_creators():
    return {
        "creators": sorted(monitored_creators)
    }


@app.post("/start-recording")
def start_recording(request: RecordingRequest):
    username = request.username.lstrip("@").strip()

    if username not in monitored_creators:
        return {
            "status": "error",
            "message": f"@{username} is not in the creator list"
        }

    if username in recording_sessions:
        return {
            "status": "already recording",
            "username": username,
            "recording_id": recording_sessions[username]["recording_id"]
        }

    recording_id = str(uuid.uuid4())

    recording_sessions[username] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "status": "recording",
        "filename": None
    }

    return recording_sessions[username]


@app.post("/stop-recording")
def stop_recording(request: RecordingRequest):
    username = request.username.lstrip("@").strip()

    session = recording_sessions.get(username)

    if not session:
        return {
            "status": "error",
            "message": f"No active recording for @{username}"
        }

    session["status"] = "stopped"
    session["stopped_at"] = now()

    recordings[session["recording_id"]] = session
    del recording_sessions[username]

    return {
        "status": "recording stopped",
        **session
    }


@app.post("/upload-recording")
async def upload_recording(
    username: str = Form(...),
    file: UploadFile = File(...)
):
    username = username.lstrip("@").strip()

    if username not in monitored_creators:
        return {
            "status": "error",
            "message": f"@{username} is not in the creator list"
        }

    recording_id = str(uuid.uuid4())

    extension = Path(file.filename or "").suffix.lower()

    if extension not in [".mp4", ".mov", ".mkv", ".webm"]:
        extension = ".mp4"

    filename = f"{username}_{recording_id}{extension}"
    filepath = RECORDINGS_DIR / filename

    content = await file.read()

    with open(filepath, "wb") as output:
        output.write(content)

    active_session = recording_sessions.get(username)

    if active_session:
        active_session["filename"] = filename
        active_session["file_path"] = str(filepath)
        active_session["file_size"] = len(content)
        active_session["uploaded_at"] = now()

        recordings[active_session["recording_id"]] = active_session

        return {
            "status": "recording uploaded",
            "recording_id": active_session["recording_id"],
            "username": username,
            "filename": filename,
            "linked_to_session": True
        }

    recordings[recording_id] = {
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "file_path": str(filepath),
        "file_size": len(content),
        "status": "uploaded",
        "uploaded_at": now()
    }

    return {
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "linked_to_session": False
    }


@app.get("/recordings")
def get_recordings():
    return {
        "recordings": list(recordings.values())
    }


# -----------------------------------
# CLIP TEST
# -----------------------------------

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    username = request.username.lstrip("@").strip()

    creator_recordings = [
        r for r in recordings.values()
        if r.get("username") == username
    ]

    if not creator_recordings:
        return {
            "status": "error",
            "message": f"No recordings found for @{username}"
        }

    recording = creator_recordings[-1]

    if "file_path" not in recording:
        return {
            "status": "error",
            "message": "Recording has no video file attached."
        }

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {
            "status": "error",
            "message": "Recording file does not exist on the server."
        }

    clip_id = str(uuid.uuid4())

    output_file = CLIPS_DIR / f"{username}_{clip_id}.mp4"

    try:

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_file),
                "-t",
                "30",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(output_file)
            ],
            capture_output=True,
            text=True
        )

    except FileNotFoundError:

        return {
            "status": "error",
            "message": "FFmpeg is not installed on the server yet."
        }

    if result.returncode != 0:

        return {
            "status": "error",
            "message": "FFmpeg failed to create the clip.",
            "details": result.stderr[-1000:]
        }

    clips[clip_id] = {
        "clip_id": clip_id,
        "username": username,
        "recording_id": recording["recording_id"],
        "filename": output_file.name,
        "file_path": str(output_file),
        "created_at": now(),
        "duration": 30
    }

    return {
        "status": "clip created",
        **clips[clip_id]
    }


@app.get("/clips")
def get_clips():
    return {
        "clips": list(clips.values())
    }


@app.get("/clip/{clip_id}")
def get_clip(clip_id: str):

    clip = clips.get(clip_id)

    if not clip:
        return {
            "status": "error",
            "message": "Clip not found."
        }

    filepath = Path(clip["file_path"])

    if not filepath.exists():
        return {
            "status": "error",
            "message": "Clip file no longer exists."
        }

    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=clip["filename"]
    )


@app.get("/recording-status/{username}")
def recording_status(username: str):
    username = username.lstrip("@").strip()

    session = recording_sessions.get(username)

    if session:
        return session

    return {
        "username": username,
        "status": "not recording"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Clipz by Greg"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
