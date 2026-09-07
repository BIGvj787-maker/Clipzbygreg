import os
import json
import uuid
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Clipz by Greg")

# Persistent storage location.
# On Render, point a persistent disk at /var/data if you want files
# to survive restarts/deploys.
DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))
RECORDINGS_DIR = DATA_DIR / "recordings"
CLIPS_DIR = DATA_DIR / "clips"
CREATORS_FILE = DATA_DIR / "creators.json"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

lock = threading.Lock()
live_processes = {}


def now():
    return datetime.now(timezone.utc).isoformat()


def load_creators():
    if not CREATORS_FILE.exists():
        return {}

    try:
        return json.loads(CREATORS_FILE.read_text())
    except Exception:
        return {}


def save_creators(creators):
    temp = CREATORS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(creators, indent=2))
    temp.replace(CREATORS_FILE)


creators = load_creators()


class CreatorRequest(BaseModel):
    username: str
    profile_url: Optional[str] = None


class LiveRecordingRequest(BaseModel):
    username: str
    stream_url: str


class ManualRecordingRequest(BaseModel):
    username: str


def normalize_username(username: str):
    username = username.strip()

    if username.startswith("@"):
        username = username[1:]

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    return username


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clipz by Greg</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 850px;
                margin: 50px auto;
                padding: 20px;
            }
            h1 { margin-bottom: 5px; }
            .card {
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 20px;
                margin-top: 20px;
            }
            code {
                background: #f3f3f3;
                padding: 3px 6px;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Clipz by Greg</h1>
        <p>Creator monitoring and AI clipping system.</p>

        <div class="card">
            <h2>API</h2>
            <p><a href="/docs">Open API Docs</a></p>
        </div>

        <div class="card">
            <h2>Pipeline</h2>
            <p>
                Creator → monitoring → supported LIVE source →
                recording → AI moments → clips
            </p>
        </div>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {
        "status": "ok",
        "creators": len(creators),
        "active_recordings": len(live_processes)
    }


@app.post("/add-creator")
def add_creator(data: CreatorRequest):
    username = normalize_username(data.username)

    with lock:
        creators[username] = {
            "username": username,
            "profile_url": data.profile_url
            or f"https://www.tiktok.com/@{username}",
            "monitoring": True,
            "live_status": "unknown",
            "recording": False,
            "recording_id": None,
            "added_at": creators.get(username, {}).get("added_at", now()),
            "updated_at": now(),
            "source_status": "pending_source"
        }

        save_creators(creators)

    return {
        "status": "creator added",
        "username": username,
        "monitoring": True,
        "source_status": "pending_source"
    }


@app.get("/creators")
def get_creators():
    return list(creators.values())


@app.get("/creator/{username}")
def get_creator(username: str):
    username = normalize_username(username)

    creator = creators.get(username)

    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    return creator


@app.delete("/remove-creator/{username}")
def remove_creator(username: str):
    username = normalize_username(username)

    with lock:
        if username not in creators:
            raise HTTPException(
                status_code=404,
                detail="Creator is not being monitored"
            )

        if creators[username].get("recording"):
            raise HTTPException(
                status_code=400,
                detail="Stop the active recording before removing creator"
            )

        del creators[username]
        save_creators(creators)

    return {
        "status": "creator removed",
        "username": username
    }


@app.post("/start-live-recording")
def start_live_recording(data: LiveRecordingRequest):
    username = normalize_username(data.username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    stream_url = data.stream_url.strip()

    if not (
        stream_url.startswith("http://")
        or stream_url.startswith("https://")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only HTTP and HTTPS stream URLs are supported"
        )

    if creators[username].get("recording"):
        raise HTTPException(
            status_code=400,
            detail="Creator is already being recorded"
        )

    recording_id = str(uuid.uuid4())

    temp_file = RECORDINGS_DIR / f"{username}_{recording_id}.mkv"
    final_file = RECORDINGS_DIR / f"{username}_{recording_id}.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        stream_url,
        "-c",
        "copy",
        str(temp_file)
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not start FFmpeg: {e}"
        )

    live_processes[username] = {
        "process": process,
        "recording_id": recording_id,
        "temp_file": str(temp_file),
        "final_file": str(final_file),
        "started_at": now()
    }

    with lock:
        creators[username]["recording"] = True
        creators[username]["live_status"] = "live"
        creators[username]["recording_id"] = recording_id
        creators[username]["updated_at"] = now()
        creators[username]["source_status"] = "connected"
        save_creators(creators)

    return {
        "status": "live recording started",
        "recording_id": recording_id,
        "username": username,
        "started_at": live_processes[username]["started_at"]
    }


@app.get("/live-recording-status/{username}")
def live_recording_status(username: str):
    username = normalize_username(username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    active = live_processes.get(username)

    if not active:
        return {
            "username": username,
            "recording": False,
            "status": "not_recording",
            "creator": creators[username]
        }

    process = active["process"]

    if process.poll() is not None:
        finish_live_recording(username)

        return {
            "username": username,
            "recording": False,
            "status": "recording_process_ended"
        }

    return {
        "username": username,
        "recording": True,
        "status": "recording",
        "recording_id": active["recording_id"],
        "started_at": active["started_at"]
    }


def finish_live_recording(username):
    active = live_processes.get(username)

    if not active:
        return None

    process = active["process"]

    if process.poll() is None:
        process.terminate()

        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    temp_file = Path(active["temp_file"])
    final_file = Path(active["final_file"])

    if temp_file.exists() and temp_file.stat().st_size > 0:
        remux_command = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_file),
            "-c",
            "copy",
            str(final_file)
        ]

        subprocess.run(
            remux_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        temp_file.unlink(missing_ok=True)

    recording_id = active["recording_id"]

    live_processes.pop(username, None)

    with lock:
        if username in creators:
            creators[username]["recording"] = False
            creators[username]["live_status"] = "offline"
            creators[username]["recording_id"] = None
            creators[username]["updated_at"] = now()
            save_creators(creators)

    return {
        "recording_id": recording_id,
        "username": username,
        "filename": final_file.name if final_file.exists() else None,
        "path": str(final_file) if final_file.exists() else None
    }


@app.post("/stop-live-recording")
def stop_live_recording(data: ManualRecordingRequest):
    username = normalize_username(data.username)

    if username not in live_processes:
        raise HTTPException(
            status_code=404,
            detail="No active LIVE recording"
        )

    result = finish_live_recording(username)

    return {
        "status": "live recording stopped",
        **result
    }


@app.get("/recordings")
def recordings():
    results = []

    for file in sorted(RECORDINGS_DIR.glob("*"), key=lambda x: x.stat().st_mtime):
        if file.suffix.lower() not in [".mp4", ".mkv", ".mov"]:
            continue

        results.append({
            "filename": file.name,
            "path": str(file),
            "size": file.stat().st_size
        })

    return results


@app.get("/recording/{filename}")
def get_recording(filename: str):
    safe_name = Path(filename).name
    file = RECORDINGS_DIR / safe_name

    if not file.exists():
        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    return FileResponse(file)


@app.post("/upload-recording")
async def upload_recording(
    username: str,
    recording_id: str,
    file: UploadFile = File(...)
):
    username = normalize_username(username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    filename = f"{username}_{recording_id}_{Path(file.filename).name}"
    destination = RECORDINGS_DIR / filename

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    return {
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename
    }


@app.get("/monitoring-summary")
def monitoring_summary():
    total = len(creators)
    monitoring = sum(
        1 for c in creators.values()
        if c.get("monitoring")
    )
    recording = sum(
        1 for c in creators.values()
        if c.get("recording")
    )

    return {
        "total_creators": total,
        "monitoring": monitoring,
        "currently_recording": recording,
        "creators": list(creators.values())
    }


@app.post("/set-source-status/{username}")
def set_source_status(username: str, status: str):
    username = normalize_username(username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    allowed = {
        "pending_source",
        "connected",
        "offline",
        "error"
    }

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(sorted(allowed))}"
        )

    creators[username]["source_status"] = status
    creators[username]["updated_at"] = now()

    save_creators(creators)

    return {
        "username": username,
        "source_status": status
    }
