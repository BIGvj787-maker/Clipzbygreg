from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timezone
import uuid
import shutil
import subprocess

app = FastAPI(title="Clipz by Greg API", version="1.0.0")

# -----------------------------
# Storage
# -----------------------------

RECORDINGS_DIR = Path("recordings")
CLIPS_DIR = Path("clips")

RECORDINGS_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)

monitored_creators = set()
recordings = {}
recording_sessions = {}
clips = {}


# -----------------------------
# Models
# -----------------------------

class CreatorRequest(BaseModel):
    username: str


class RecordingRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    recording_id: str
    start_time: int = 0
    duration: int = 30


# -----------------------------
# Main Website
# -----------------------------

@app.get("/", response_class=HTMLResponse)
def homepage():

    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Clipz by Greg</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background:
        radial-gradient(circle at 20% 10%, rgba(124,58,237,.22), transparent 30%),
        radial-gradient(circle at 90% 20%, rgba(168,85,247,.16), transparent 25%),
        #08070d;
    color: white;
    min-height: 100vh;
}

nav {
    height: 75px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 7%;
    border-bottom: 1px solid rgba(255,255,255,.08);
    background: rgba(8,7,13,.75);
    backdrop-filter: blur(15px);
}

.logo {
    font-size: 22px;
    font-weight: 800;
}

.logo span {
    color: #9b6cff;
}

.navlinks {
    display: flex;
    gap: 30px;
}

.navlinks a {
    color: #aaa5b5;
    text-decoration: none;
    font-size: 14px;
}

.navlinks a:hover {
    color: white;
}

.hero {
    max-width: 1100px;
    margin: auto;
    padding: 110px 25px 80px;
    text-align: center;
}

.badge {
    display: inline-block;
    padding: 8px 14px;
    border: 1px solid rgba(167,139,250,.35);
    border-radius: 999px;
    background: rgba(139,92,246,.10);
    color: #c4b5fd;
    font-size: 13px;
    margin-bottom: 25px;
}

h1 {
    font-size: clamp(45px, 8vw, 82px);
    line-height: .95;
    margin: 0;
    letter-spacing: -4px;
}

.gradient {
    background: linear-gradient(90deg,#fff,#a78bfa,#7c3aed);
    -webkit-background-clip: text;
    color: transparent;
}

.hero p {
    max-width: 650px;
    margin: 25px auto;
    color: #aaa5b5;
    font-size: 18px;
    line-height: 1.6;
}

.buttons {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 30px;
}

.btn {
    padding: 14px 22px;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 700;
    font-size: 14px;
}

.primary {
    background: #7c3aed;
    color: white;
}

.primary:hover {
    background: #8b5cf6;
}

.secondary {
    border: 1px solid #30283c;
    background: #12101a;
    color: white;
}

.stats {
    max-width: 900px;
    margin: 20px auto 80px;
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 15px;
    padding: 0 25px;
}

.stat {
    background: rgba(18,16,27,.8);
    border: 1px solid #292333;
    border-radius: 18px;
    padding: 25px;
}

.stat strong {
    display: block;
    font-size: 30px;
}

.stat span {
    color: #858090;
    font-size: 13px;
}

.section {
    max-width: 1100px;
    margin: auto;
    padding: 30px 25px 100px;
}

.section-title {
    text-align: center;
    margin-bottom: 35px;
}

.section-title h2 {
    font-size: 34px;
    margin-bottom: 10px;
}

.section-title p {
    color: #888290;
}

.features {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 18px;
}

.feature {
    background: linear-gradient(145deg,#15121e,#0e0c14);
    border: 1px solid #292333;
    border-radius: 20px;
    padding: 28px;
}

.icon {
    width: 45px;
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 13px;
    background: rgba(139,92,246,.15);
    color: #a78bfa;
    font-size: 20px;
    margin-bottom: 20px;
}

.feature h3 {
    margin: 0 0 10px;
}

.feature p {
    color: #8d8797;
    line-height: 1.6;
    font-size: 14px;
}

.workflow {
    margin-top: 70px;
    padding: 30px;
    border-radius: 22px;
    border: 1px solid #292333;
    background: #100d17;
}

.steps {
    display: grid;
    grid-template-columns: repeat(4,1fr);
    gap: 15px;
}

.step {
    padding: 20px;
}

.step-number {
    color: #a78bfa;
    font-weight: 800;
    font-size: 13px;
}

.step h3 {
    margin-bottom: 7px;
}

.step p {
    color: #817a8c;
    font-size: 13px;
    line-height: 1.5;
}

footer {
    border-top: 1px solid #292333;
    padding: 30px 7%;
    color: #716b78;
    font-size: 12px;
    display: flex;
    justify-content: space-between;
}

@media(max-width:800px) {

    .navlinks {
        display: none;
    }

    .stats,
    .features,
    .steps {
        grid-template-columns: 1fr;
    }

    .hero {
        padding-top: 75px;
    }

    h1 {
        letter-spacing: -2px;
    }

    .buttons {
        flex-direction: column;
    }

    .btn {
        width: 100%;
    }

}

</style>
</head>

<body>

<nav>

<div class="logo">
Clipz <span>by Greg</span>
</div>

<div class="navlinks">
<a href="/">Home</a>
<a href="/creators">Creators</a>
<a href="/recordings">Recordings</a>
<a href="/clips">Clips</a>
<a href="/docs">API</a>
</div>

</nav>


<section class="hero">

<div class="badge">
AI-Powered Content Clipping
</div>

<h1>
Turn moments<br>
into <span class="gradient">clips.</span>
</h1>

<p>
Clipz by Greg helps creators organize recordings,
find the best moments and turn them into ready-to-use
short-form clips.
</p>

<div class="buttons">

<a class="btn primary" href="/docs">
Open API
</a>

<a class="btn secondary" href="/creators">
View Creators
</a>

</div>

</section>


<section class="stats">

<div class="stat">
<strong id="creatorCount">0</strong>
<span>Creators monitored</span>
</div>

<div class="stat">
<strong id="recordingCount">0</strong>
<span>Recordings</span>
</div>

<div class="stat">
<strong id="clipCount">0</strong>
<span>Clips created</span>
</div>

</section>


<section class="section">

<div class="section-title">

<h2>Everything for your clipping workflow</h2>

<p>
Keep creators, recordings and clips organized in one place.
</p>

</div>


<div class="features">

<div class="feature">

<div class="icon">◉</div>

<h3>Creator Monitoring</h3>

<p>
Add creators to your monitoring list and keep their
recording sessions organized.
</p>

</div>


<div class="feature">

<div class="icon">●</div>

<h3>Recording Library</h3>

<p>
Upload and organize recordings while automatically
linking files to the creator they belong to.
</p>

</div>


<div class="feature">

<div class="icon">✂</div>

<h3>Smart Clipping</h3>

<p>
Turn sections of recordings into short clips ready
for editing and publishing.
</p>

</div>

</div>


<div class="workflow">

<div class="section-title">
<h2>How it works</h2>
</div>

<div class="steps">

<div class="step">
<div class="step-number">01</div>
<h3>Add creator</h3>
<p>Add the creator username you want to manage.</p>
</div>

<div class="step">
<div class="step-number">02</div>
<h3>Record</h3>
<p>Connect an authorized recording source and save the session.</p>
</div>

<div class="step">
<div class="step-number">03</div>
<h3>Find moments</h3>
<p>Analyze recordings to identify strong moments for clips.</p>
</div>

<div class="step">
<div class="step-number">04</div>
<h3>Create clips</h3>
<p>Generate clips from the moments you choose.</p>
</div>

</div>

</div>

</section>


<footer>

<div>
© 2026 Clipz by Greg
</div>

<div>
Creator clipping platform
</div>

</footer>


<script>

async function loadStats() {

    try {

        const creators = await fetch("/creators").then(r => r.json());
        const recordings = await fetch("/recordings").then(r => r.json());
        const clips = await fetch("/clips").then(r => r.json());

        document.getElementById("creatorCount").textContent =
            creators.creators ? creators.creators.length : 0;

        document.getElementById("recordingCount").textContent =
            recordings.recordings ? recordings.recordings.length : 0;

        document.getElementById("clipCount").textContent =
            clips.clips ? clips.clips.length : 0;

    } catch (error) {

        console.log("Stats unavailable");

    }

}

loadStats();

</script>

</body>
</html>
"""


# -----------------------------
# Creator API
# -----------------------------

@app.post("/add-creator")
def add_creator(request: CreatorRequest):

    username = request.username.strip().lstrip("@")

    if not username:
        return {"error": "Username is required."}

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


# -----------------------------
# Recording API
# -----------------------------

@app.post("/start-recording")
def start_recording(request: RecordingRequest):

    username = request.username.strip().lstrip("@")

    if username not in monitored_creators:
        return {
            "error": "Creator is not being monitored."
        }

    recording_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc).isoformat()

    recording_sessions[recording_id] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now,
        "status": "recording",
        "filename": None
    }

    return recording_sessions[recording_id]


@app.post("/upload-recording")
async def upload_recording(
    recording_id: str,
    file: UploadFile = File(...)
):

    session = recording_sessions.get(recording_id)

    if not session:
        return {
            "error": "Recording session not found."
        }

    username = session["username"]

    safe_name = Path(file.filename or "recording.mp4").name

    filename = f"{username}_{uuid.uuid4()}_{safe_name}"

    output_path = RECORDINGS_DIR / filename

    with output_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    recordings[recording_id] = {
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "file_path": str(output_path),
        "file_size": output_path.stat().st_size,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }

    session["filename"] = filename

    return {
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "linked_to_session": True
    }


@app.post("/stop-recording")
def stop_recording(request: RecordingRequest):

    username = request.username.strip().lstrip("@")

    matches = [
        session for session in recording_sessions.values()
        if session["username"] == username
        and session["status"] == "recording"
    ]

    if not matches:
        return {
            "error": "No active recording found."
        }

    session = matches[-1]

    session["status"] = "stopped"
    session["stopped_at"] = datetime.now(timezone.utc).isoformat()

    recording = recordings.get(session["recording_id"])

    if recording:
        return {
            "status": "stopped",
            **session,
            **recording
        }

    return session


@app.get("/recordings")
def get_recordings():

    return {
        "recordings": list(recordings.values())
    }


@app.get("/recording-status/{username}")
def recording_status(username: str):

    username = username.strip().lstrip("@")

    active = [
        session for session in recording_sessions.values()
        if session["username"] == username
        and session["status"] == "recording"
    ]

    return {
        "username": username,
        "recording": bool(active),
        "sessions": active
    }


# -----------------------------
# Clip API
# -----------------------------

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    recording = recordings.get(request.recording_id)

    if not recording:
        return {
            "error": "Recording not found."
        }

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {
            "error": "Recording file does not exist on the server."
        }

    clip_id = str(uuid.uuid4())

    output_file = CLIPS_DIR / f"clip_{clip_id}.mp4"

    try:

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(request.start_time),
                "-i",
                str(input_file),
                "-t",
                str(request.duration),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(output_file)
            ],
            check=True,
            capture_output=True,
            text=True
        )

    except FileNotFoundError:

        return {
            "error": "FFmpeg is not installed on the server yet."
        }

    except subprocess.CalledProcessError as error:

        return {
            "error": "FFmpeg could not create the clip.",
            "details": error.stderr[-1000:]
        }

    clips[clip_id] = {
        "clip_id": clip_id,
        "recording_id": request.recording_id,
        "username": recording["username"],
        "filename": output_file.name,
        "file_path": str(output_file),
        "start_time": request.start_time,
        "duration": request.duration,
        "created_at": datetime.now(timezone.utc).isoformat()
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
            "error": "Clip not found."
        }

    path = Path(clip["file_path"])

    if not path.exists():
        return {
            "error": "Clip file no longer exists."
        }

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=clip["filename"]
    )


# -----------------------------
# Health Check
# -----------------------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "Clipz by Greg"
    }
