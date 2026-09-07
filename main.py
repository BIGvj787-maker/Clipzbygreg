import os
import uuid
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Clipz by Greg")

# =========================
# STORAGE
# =========================

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))

RECORDINGS_DIR = DATA_DIR / "recordings"
CLIPS_DIR = DATA_DIR / "clips"
TEMP_DIR = DATA_DIR / "temp"

for folder in (RECORDINGS_DIR, CLIPS_DIR, TEMP_DIR):
    folder.mkdir(parents=True, exist_ok=True)

creators = {}
recordings = {}
clips = {}
live_processes = {}
live_sessions = {}


# =========================
# MODELS
# =========================

class CreatorRequest(BaseModel):
    username: str


class LiveRecordingRequest(BaseModel):
    username: str
    stream_url: str


class ClipRequest(BaseModel):
    recording_id: str
    start_time: float = 0
    duration: float = 30


class AIClipRequest(BaseModel):
    recording_id: str
    moment_rank: int = 1


class TwoClipRequest(BaseModel):
    recording_id: str
    start_time: float = 0
    duration: float = 30


# =========================
# HELPERS
# =========================

def now():
    return datetime.now(timezone.utc).isoformat()


def clean_username(username):
    username = username.strip().lstrip("@")

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )

    return username


def validate_stream_url(stream_url):
    parsed = urlparse(stream_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Only HTTP and HTTPS stream URLs are supported"
        )

    if not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Invalid stream URL"
        )


def get_duration(path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            return float(result.stdout.strip())

    except Exception:
        pass

    return 0


# =========================
# HOME
# =========================

@app.get("/", response_class=HTMLResponse)
def home():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clipz by Greg</title>

        <style>
            body {
                margin: 0;
                background: #090611;
                color: white;
                font-family: Arial, sans-serif;
            }

            nav {
                padding: 22px 7%;
                border-bottom: 1px solid #241b35;
                display: flex;
                justify-content: space-between;
            }

            .logo {
                font-size: 24px;
                font-weight: bold;
            }

            .hero {
                text-align: center;
                padding: 90px 7%;
            }

            h1 {
                font-size: 60px;
            }

            .purple {
                color: #a855f7;
            }

            p {
                color: #aaa;
                font-size: 18px;
            }

            .cards {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                padding: 20px 7%;
            }

            .card {
                padding: 25px;
                background: #120d1d;
                border: 1px solid #2c2140;
                border-radius: 18px;
            }

            a {
                color: #c084fc;
                text-decoration: none;
            }
        </style>
    </head>

    <body>

        <nav>
            <div class="logo">
                Clipz by Greg
            </div>

            <a href="/docs">
                API Docs
            </a>
        </nav>

        <section class="hero">

            <h1>
                <span class="purple">Clipz</span> by Greg
            </h1>

            <p>
                Record authorized live feeds, find the best moments,
                and create short-form clips.
            </p>

        </section>

        <section class="cards">

            <div class="card">
                <h2>Any Creator</h2>
                <p>
                    Add and manage any creator by username.
                </p>
            </div>

            <div class="card">
                <h2>LIVE Recording</h2>
                <p>
                    Record an authorized live feed with FFmpeg.
                </p>
            </div>

            <div class="card">
                <h2>AI Moments</h2>
                <p>
                    Find high-energy moments in recordings.
                </p>
            </div>

            <div class="card">
                <h2>Two Clips</h2>
                <p>
                    Generate a clear version and a vertical
                    blurred-background version.
                </p>
            </div>

        </section>

    </body>
    </html>
    """


# =========================
# HEALTH
# =========================

@app.get("/health")
def health():

    return {
        "status": "online",
        "service": "Clipz by Greg"
    }


# =========================
# CREATORS
# =========================

@app.post("/add-creator")
def add_creator(request: CreatorRequest):

    username = clean_username(request.username)

    creators[username] = {
        "username": username,
        "monitoring": True,
        "added_at": now()
    }

    return {
        "status": "creator added",
        "username": username,
        "monitoring": True
    }


@app.get("/creators")
def get_creators():

    return list(creators.values())


@app.post("/remove-creator")
def remove_creator(request: CreatorRequest):

    username = clean_username(request.username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    creators.pop(username)

    return {
        "status": "creator removed",
        "username": username
    }


# =========================
# AUTHORIZED LIVE RECORDER
# =========================

@app.post("/start-live-recording")
def start_live_recording(request: LiveRecordingRequest):

    username = clean_username(request.username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    if username in live_processes:
        raise HTTPException(
            status_code=409,
            detail="Creator is already being recorded"
        )

    validate_stream_url(request.stream_url)

    recording_id = str(uuid.uuid4())

    temp_path = TEMP_DIR / (
        f"{username}_{recording_id}.mkv"
    )

    final_path = RECORDINGS_DIR / (
        f"{username}_{recording_id}.mp4"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-y",

        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",

        "-i",
        request.stream_url,

        "-map", "0",
        "-c", "copy",

        "-f", "matroska",

        str(temp_path)
    ]

    try:

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except FileNotFoundError:

        raise HTTPException(
            status_code=500,
            detail="FFmpeg is unavailable"
        )

    live_processes[username] = process

    live_sessions[username] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "temp_path": str(temp_path),
        "final_path": str(final_path)
    }

    threading.Thread(
        target=watch_live,
        args=(username, recording_id, process),
        daemon=True
    ).start()

    return {
        "status": "live recording started",
        "recording_id": recording_id,
        "username": username,
        "started_at": live_sessions[username]["started_at"]
    }


def watch_live(username, recording_id, process):

    process.wait()

    finalize_live(
        username,
        recording_id
    )


def finalize_live(username, recording_id):

    session = live_sessions.get(username)

    if not session:
        return

    temp_path = Path(
        session["temp_path"]
    )

    final_path = Path(
        session["final_path"]
    )

    if not temp_path.exists():
        live_processes.pop(username, None)
        live_sessions.pop(username, None)
        return

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_path),
            "-c", "copy",
            "-movflags", "+faststart",
            str(final_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        final_path = temp_path

    duration = get_duration(final_path)

    size = final_path.stat().st_size if final_path.exists() else 0

    recordings[recording_id] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": session["started_at"],
        "stopped_at": now(),
        "filename": final_path.name,
        "file_path": str(final_path),
        "file_size": size,
        "duration": duration,
        "status": "completed",
        "source": "authorized_live_feed"
    }

    if temp_path.exists() and temp_path != final_path:

        try:
            temp_path.unlink()
        except Exception:
            pass

    live_processes.pop(username, None)
    live_sessions.pop(username, None)


@app.get("/live-recording-status/{username}")
def live_status(username: str):

    username = clean_username(username)

    if username not in live_processes:

        return {
            "username": username,
            "recording": False,
            "status": "not_recording"
        }

    process = live_processes[username]
    session = live_sessions[username]

    return {
        "username": username,
        "recording": True,
        "status": "recording",
        "recording_id": session["recording_id"],
        "started_at": session["started_at"],
        "process_running": process.poll() is None
    }


@app.post("/stop-live-recording")
def stop_live(request: CreatorRequest):

    username = clean_username(request.username)

    if username not in live_processes:

        raise HTTPException(
            status_code=404,
            detail="No LIVE recording found"
        )

    process = live_processes[username]

    recording_id = live_sessions[username]["recording_id"]

    process.terminate()

    try:
        process.wait(timeout=15)

    except subprocess.TimeoutExpired:

        process.kill()
        process.wait()

    finalize_live(
        username,
        recording_id
    )

    return {
        "status": "live recording stopped",
        "recording": recordings.get(recording_id)
    }


# =========================
# RECORDINGS
# =========================

@app.get("/recordings")
def get_recordings():

    return list(recordings.values())


# =========================
# AI MOMENT DETECTION
# =========================

def analyze_audio(file_path):

    duration = get_duration(file_path)

    if duration <= 0:
        return []

    window = 5
    moments = []

    position = 0

    while position < duration:

        end = min(
            position + window,
            duration
        )

        result = subprocess.run(
            [
                "ffmpeg",
                "-ss", str(position),
                "-t", str(end - position),
                "-i", str(file_path),
                "-af", "volumedetect",
                "-f", "null",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        volume = -60

        for line in result.stderr.splitlines():

            if "mean_volume" in line:

                try:
                    volume = float(
                        line.split(":")[-1]
                        .strip()
                        .replace(" dB", "")
                    )
                except Exception:
                    pass

        score = max(
            0,
            min(
                100,
                (volume + 60) * 2
            )
        )

        moments.append({
            "start_time": round(position, 2),
            "end_time": round(end, 2),
            "duration": round(end - position, 2),
            "score": round(score, 1)
        })

        position += window

    moments.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best = moments[:3]

    for i, moment in enumerate(best, 1):
        moment["rank"] = i

    return best


@app.post("/find-best-moments")
def find_best_moments(request: CreatorRequest):

    username = clean_username(request.username)

    matches = [
        r for r in recordings.values()
        if r["username"] == username
        and r.get("file_path")
    ]

    if not matches:

        raise HTTPException(
            status_code=404,
            detail="No recording found for this creator"
        )

    recording = matches[-1]

    path = Path(
        recording["file_path"]
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found"
        )

    moments = analyze_audio(path)

    return {
        "username": username,
        "recording_id": recording["recording_id"],
        "analyzed_at": now(),
        "moments": moments
    }


# =========================
# NORMAL CLIP
# =========================

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    recording = recordings.get(
        request.recording_id
    )

    if not recording:

        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    input_path = Path(
        recording["file_path"]
    )

    if not input_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found"
        )

    clip_id = str(uuid.uuid4())

    username = recording["username"]

    filename = (
        f"{username}_{clip_id}.mp4"
    )

    output_path = CLIPS_DIR / filename

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-i", str(input_path),
            "-t", str(request.duration),
            "-c", "copy",
            str(output_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="FFmpeg failed to create clip"
        )

    clip = {
        "clip_id": clip_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": filename,
        "file_path": str(output_path),
        "created_at": now(),
        "duration": request.duration,
        "type": "full_clear"
    }

    clips[clip_id] = clip

    return {
        "status": "clip created",
        **clip
    }


# =========================
# VERTICAL CLIP
# =========================

def create_vertical(
    input_path,
    output_path,
    start,
    duration
):

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=30:10[bg];"

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease[fg];"

        "[bg][fg]"
        "overlay=(W-w)/2:(H-h)/2"
    )

    return subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", str(input_path),
            "-t", str(duration),

            "-filter_complex",
            filter_complex,

            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",

            "-c:a", "aac",
            "-b:a", "192k",

            "-movflags",
            "+faststart",

            str(output_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


# =========================
# TWO CLIPS
# =========================

@app.post("/create-two-clips")
def create_two_clips(request: TwoClipRequest):

    recording = recordings.get(
        request.recording_id
    )

    if not recording:

        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    input_path = Path(
        recording["file_path"]
    )

    if not input_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found"
        )

    username = recording["username"]

    # Full clear version

    full_id = str(uuid.uuid4())

    full_filename = (
        f"{username}_{full_id}.mp4"
    )

    full_path = CLIPS_DIR / full_filename

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-i", str(input_path),
            "-t", str(request.duration),
            "-c", "copy",
            str(full_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="Failed to create full clip"
        )

    full_clip = {
        "clip_id": full_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": full_filename,
        "file_path": str(full_path),
        "created_at": now(),
        "duration": request.duration,
        "type": "full_clear"
    }

    clips[full_id] = full_clip

    # Vertical blurred version

    vertical_id = str(uuid.uuid4())

    vertical_filename = (
        f"{username}_{vertical_id}.mp4"
    )

    vertical_path = CLIPS_DIR / vertical_filename

    result = create_vertical(
        input_path,
        vertical_path,
        request.start_time,
        request.duration
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="Failed to create vertical clip"
        )

    vertical_clip = {
        "clip_id": vertical_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": vertical_filename,
        "file_path": str(vertical_path),
        "created_at": now(),
        "duration": request.duration,
        "type": "vertical_blurred"
    }

    clips[vertical_id] = vertical_clip

    return {
        "status": "two clips created",
        "full_clip": full_clip,
        "vertical_clip": vertical_clip
    }


# =========================
# CLIPS
# =========================

@app.get("/clips")
def get_clips():

    return list(clips.values())


@app.get("/clip/{clip_id}")
def get_clip(clip_id: str):

    clip = clips.get(clip_id)

    if not clip:

        raise HTTPException(
            status_code=404,
            detail="Clip not found"
        )

    path = Path(
        clip["file_path"]
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Clip file not found"
        )

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=clip["filename"]
    )


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
