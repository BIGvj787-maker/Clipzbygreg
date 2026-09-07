import os
import uuid
import subprocess
from pathlib import Path
from datetime import datetime, timezone

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


class RecordingRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    username: str


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_username(username):
    return username.lstrip("@").strip()


@app.get("/", response_class=HTMLResponse)
def home():

    creator_count = len(monitored_creators)
    recording_count = len(recordings)
    clip_count = len(clips)
    active_count = len(recording_sessions)

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
    font-family: Inter, Arial, sans-serif;
    background: #07070b;
    color: white;
    min-height: 100vh;
}}

body:before {{
    content: "";
    position: fixed;
    width: 500px;
    height: 500px;
    background: #713cff;
    filter: blur(180px);
    opacity: .18;
    top: -200px;
    left: -150px;
    pointer-events: none;
}}

nav {{
    height: 78px;
    padding: 0 6%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,.08);
    background: rgba(7,7,11,.75);
    backdrop-filter: blur(20px);
    position: sticky;
    top: 0;
    z-index: 10;
}}

.logo {{
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -1px;
}}

.logo span {{
    color: #8b5cf6;
}}

.navlinks {{
    display: flex;
    gap: 28px;
}}

.navlinks a {{
    color: #9999a7;
    text-decoration: none;
    font-size: 14px;
}}

.navlinks a:hover {{
    color: white;
}}

.hero {{
    max-width: 1150px;
    margin: auto;
    padding: 95px 6% 75px;
}}

.pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 13px;
    border-radius: 999px;
    background: rgba(139,92,246,.1);
    border: 1px solid rgba(139,92,246,.3);
    color: #bda9ff;
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 25px;
}}

.dot {{
    width: 7px;
    height: 7px;
    background: #8b5cf6;
    border-radius: 50%;
}}

h1 {{
    font-size: clamp(48px, 7vw, 82px);
    line-height: .95;
    letter-spacing: -5px;
    max-width: 850px;
}}

.gradient {{
    background: linear-gradient(90deg,#ffffff,#a78bfa,#60a5fa);
    -webkit-background-clip: text;
    color: transparent;
}}

.hero-text {{
    margin-top: 25px;
    max-width: 650px;
    color: #9b9ba8;
    font-size: 18px;
    line-height: 1.65;
}}

.actions {{
    margin-top: 32px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}}

.button {{
    padding: 14px 20px;
    border-radius: 12px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 700;
}}

.primary {{
    background: white;
    color: #08080c;
}}

.secondary {{
    color: white;
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.1);
}}

.dashboard {{
    max-width: 1150px;
    margin: auto;
    padding: 0 6% 80px;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 15px;
}}

.card {{
    border: 1px solid rgba(255,255,255,.09);
    background: rgba(255,255,255,.045);
    border-radius: 18px;
    padding: 23px;
    backdrop-filter: blur(15px);
}}

.stat-title {{
    color: #858592;
    font-size: 12px;
}}

.stat {{
    font-size: 32px;
    font-weight: 800;
    margin-top: 8px;
}}

.section {{
    margin-top: 55px;
}}

.section-title {{
    font-size: 27px;
    font-weight: 800;
}}

.section-sub {{
    color: #777783;
    margin-top: 7px;
}}

.features {{
    margin-top: 22px;
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 15px;
}}

.feature-icon {{
    width: 43px;
    height: 43px;
    display: grid;
    place-items: center;
    border-radius: 12px;
    background: rgba(139,92,246,.12);
    color: #a78bfa;
    font-weight: 800;
    margin-bottom: 18px;
}}

.feature h3 {{
    margin-bottom: 9px;
}}

.feature p {{
    color: #858592;
    line-height: 1.55;
    font-size: 14px;
}}

footer {{
    padding: 28px 6%;
    border-top: 1px solid rgba(255,255,255,.08);
    color: #5f5f6b;
    font-size: 12px;
}}

@media(max-width:750px) {{

    .navlinks {{
        display: none;
    }}

    .stats {{
        grid-template-columns: repeat(2,1fr);
    }}

    .features {{
        grid-template-columns: 1fr;
    }}

    h1 {{
        letter-spacing: -3px;
    }}
}}

</style>
</head>

<body>

<nav>

<div class="logo">
Clipz <span>by Greg</span>
</div>

<div class="navlinks">
<a href="/docs">API</a>
<a href="/creators">Creators</a>
<a href="/recordings">Recordings</a>
</div>

</nav>


<section class="hero">

<div class="pill">
<div class="dot"></div>
CLIPZ BY GREG IS ONLINE
</div>

<h1>
Your content.
<br>
<span class="gradient">Your best moments.</span>
</h1>

<p class="hero-text">
Capture recordings, organize creators, find standout moments,
and turn long videos into clips ready to share.
</p>

<div class="actions">

<a class="button primary" href="/docs">
Open Dashboard
</a>

<a class="button secondary" href="/recordings">
View Recordings
</a>

</div>

</section>


<section class="dashboard">

<div class="stats">

<div class="card">
<div class="stat-title">CREATORS</div>
<div class="stat">{creator_count}</div>
</div>

<div class="card">
<div class="stat-title">RECORDINGS</div>
<div class="stat">{recording_count}</div>
</div>

<div class="card">
<div class="stat-title">CLIPS</div>
<div class="stat">{clip_count}</div>
</div>

<div class="card">
<div class="stat-title">ACTIVE</div>
<div class="stat">{active_count}</div>
</div>

</div>


<div class="section">

<div class="section-title">
Built for clipping.
</div>

<div class="section-sub">
Everything you need to turn recordings into moments.
</div>


<div class="features">

<div class="card feature">

<div class="feature-icon">01</div>

<h3>Creator Manager</h3>

<p>
Keep your authorized creators organized and connect
their recordings to the right account.
</p>

</div>


<div class="card feature">

<div class="feature-icon">02</div>

<h3>Recording Engine</h3>

<p>
Track recording sessions and attach uploaded video
files to the correct creator automatically.
</p>

</div>


<div class="card feature">

<div class="feature-icon">03</div>

<h3>AI Clipping</h3>

<p>
Analyze recordings for standout moments and generate
short clips from selected timestamps.
</p>

</div>

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

    username = clean_username(request.username)

    monitored_creators.add(username)

    return {{
        "status": "creator added",
        "username": username,
        "monitoring": True
    }}


@app.get("/creators")
def get_creators():

    return {{
        "creators": sorted(monitored_creators)
    }}


@app.post("/start-recording")
def start_recording(request: RecordingRequest):

    username = clean_username(request.username)

    if username not in monitored_creators:
        return {{
            "status": "error",
            "message": f"@{username} is not in the creator list"
        }}

    if username in recording_sessions:
        return {{
            "status": "already recording",
            "recording_id": recording_sessions[username]["recording_id"]
        }}

    recording_id = str(uuid.uuid4())

    session = {{
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "status": "recording",
        "filename": None
    }}

    recording_sessions[username] = session

    return session


@app.post("/upload-recording")
async def upload_recording(
    username: str = Form(...),
    file: UploadFile = File(...)
):

    username = clean_username(username)

    if username not in monitored_creators:
        return {{
            "status": "error",
            "message": f"@{username} is not in the creator list"
        }}

    recording_id = str(uuid.uuid4())

    extension = Path(file.filename or "").suffix.lower()

    if extension not in [".mp4", ".mov", ".mkv", ".webm"]:
        extension = ".mp4"

    filename = f"{username}_{recording_id}{extension}"

    filepath = RECORDINGS_DIR / filename

    content = await file.read()

    with open(filepath, "wb") as output:
        output.write(content)

    session = recording_sessions.get(username)

    if session:

        session["filename"] = filename
        session["file_path"] = str(filepath)
        session["file_size"] = len(content)
        session["uploaded_at"] = now()

        recordings[session["recording_id"]] = session

        return {{
            "status": "recording uploaded",
            "recording_id": session["recording_id"],
            "username": username,
            "filename": filename,
            "linked_to_session": True
        }}

    recordings[recording_id] = {{
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "file_path": str(filepath),
        "file_size": len(content),
        "status": "uploaded",
        "uploaded_at": now()
    }}

    return {{
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "linked_to_session": False
    }}


@app.post("/stop-recording")
def stop_recording(request: RecordingRequest):

    username = clean_username(request.username)

    session = recording_sessions.get(username)

    if not session:
        return {{
            "status": "error",
            "message": f"No active recording for @{username}"
        }}

    session["status"] = "stopped"
    session["stopped_at"] = now()

    recordings[session["recording_id"]] = session

    del recording_sessions[username]

    return {{
        "status": "stopped",
        **session
    }}


@app.get("/recordings")
def get_recordings():

    return {{
        "recordings": list(recordings.values())
    }}


@app.post("/create-clip")
def create_clip(request: ClipRequest):

    username = clean_username(request.username)

    creator_recordings = [
        r for r in recordings.values()
        if r["username"] == username
        and r.get("file_path")
    ]

    if not creator_recordings:
        return {{
            "status": "error",
            "username": username,
            "message": "No video recording is available."
        }}

    recording = creator_recordings[-1]

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {{
            "status": "error",
            "message": "Recording file could not be found."
        }}

    clip_id = str(uuid.uuid4())

    output_file = CLIPS_DIR / f"{username}_{clip_id}.mp4"

    # First version: create a short preview clip.
    # Later this section can be replaced with AI-selected timestamps.

    command = [
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
    ]

    try:

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    except FileNotFoundError:

        return {{
            "status": "error",
            "message": "FFmpeg is not installed on the server yet."
        }}

    except subprocess.CalledProcessError:

        return {{
            "status": "error",
            "message": "FFmpeg could not create the clip."
        }}

    clips[clip_id] = {{
        "clip_id": clip_id,
        "username": username,
        "recording_id": recording["recording_id"],
        "filename": output_file.name,
        "file_path": str(output_file),
        "created_at": now(),
        "duration_seconds": 30
    }}

    return {{
        "status": "clip created",
        "clip_id": clip_id,
        "username": username,
        "filename": output_file.name,
        "duration_seconds": 30,
        "message": "Clip successfully created."
    }}


@app.get("/clips")
def get_clips():

    return {{
        "clips": list(clips.values())
    }}


@app.get("/clip/{clip_id}")
def download_clip(clip_id: str):

    clip = clips.get(clip_id)

    if not clip:
        return {{
            "status": "error",
            "message": "Clip not found."
        }}

    path = Path(clip["file_path"])

    if not path.exists():
        return {{
            "status": "error",
            "message": "Clip file not found."
        }}

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=clip["filename"]
    )


@app.get("/recording-status/{username}")
def recording_status(username: str):

    username = clean_username(username)

    session = recording_sessions.get(username)

    if session:
        return session

    return {{
        "username": username,
        "status": "not recording"
    }}


@app.get("/health")
def health():

    return {{
        "status": "ok"
    }}


if __name__ == "__main__":

    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
