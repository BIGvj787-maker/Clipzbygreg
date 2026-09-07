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

# --------------------------------------------------
# DIRECTORIES
# --------------------------------------------------

RECORDINGS_DIR = Path("recordings")
CLIPS_DIR = Path("clips")
TEMP_DIR = Path("temp")

RECORDINGS_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# IN-MEMORY DATA
# --------------------------------------------------

creators = {}
recordings = {}
clips = {}

# Active FFmpeg processes
live_processes = {}

# Metadata for active LIVE recordings
live_sessions = {}


# --------------------------------------------------
# MODELS
# --------------------------------------------------

class CreatorRequest(BaseModel):
    username: str


class StartRecordingRequest(BaseModel):
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


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def clean_username(username: str):
    username = username.strip().lstrip("@")

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    return username


def validate_stream_url(stream_url: str):
    """
    Only accepts a URL supplied by the user/service.
    No TikTok page scraping or hidden URL extraction.
    """

    parsed = urlparse(stream_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="stream_url must be an http:// or https:// URL"
        )

    if not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Invalid stream URL"
        )


def run_ffmpeg(args):
    try:
        return subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not available on this server"
        )


def get_video_duration(file_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path)
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


def finalize_live_recording(username, recording_id):
    """
    Called when FFmpeg naturally exits or is stopped.
    Converts the temporary MKV recording into MP4.
    """

    session = live_sessions.get(username)

    if not session:
        return

    temp_path = Path(session["temp_path"])
    final_path = Path(session["final_path"])

    if not temp_path.exists():
        return

    # Remux MKV -> MP4
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(final_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        # If remux fails, keep the MKV so the recording isn't immediately lost.
        final_path = temp_path

    duration = get_video_duration(final_path)

    file_size = 0

    if final_path.exists():
        file_size = final_path.stat().st_size

    recording = {
        "recording_id": recording_id,
        "username": username,
        "started_at": session["started_at"],
        "stopped_at": now(),
        "filename": final_path.name,
        "file_path": str(final_path),
        "file_size": file_size,
        "duration": duration,
        "status": "completed",
        "source": "authorized_live_feed"
    }

    recordings[recording_id] = recording

    if temp_path.exists() and temp_path != final_path:
        try:
            temp_path.unlink()
        except Exception:
            pass

    live_processes.pop(username, None)
    live_sessions.pop(username, None)


def watch_live_process(username, recording_id, process):
    """
    Watches FFmpeg.

    If the supplied live feed ends by itself,
    FFmpeg exits and the recording is finalized automatically.
    """

    process.wait()

    finalize_live_recording(
        username,
        recording_id
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

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
                font-family: Arial, sans-serif;
                background: #090611;
                color: white;
            }

            nav {
                padding: 22px 7%;
                display: flex;
                justify-content: space-between;
                border-bottom: 1px solid #251c38;
            }

            .logo {
                font-size: 24px;
                font-weight: bold;
            }

            .hero {
                padding: 100px 7%;
                text-align: center;
            }

            h1 {
                font-size: 64px;
                margin-bottom: 15px;
            }

            .purple {
                color: #a855f7;
            }

            .hero p {
                color: #aaa;
                font-size: 20px;
                max-width: 650px;
                margin: auto;
            }

            .cards {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(220px, 1fr));

                gap: 20px;
                padding: 30px 7%;
            }

            .card {
                background: #120d1d;
                border: 1px solid #2c2140;
                border-radius: 18px;
                padding: 25px;
            }

            .card h2 {
                color: #c084fc;
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

            <div>
                <a href="/docs">API Docs</a>
            </div>
        </nav>

        <section class="hero">

            <h1>
                Turn <span class="purple">LIVE moments</span>
                into clips.
            </h1>

            <p>
                Record authorized live feeds, find the best moments,
                and create ready-to-use vertical clips.
            </p>

        </section>

        <section class="cards">

            <div class="card">
                <h2>LIVE Recording</h2>
                <p>
                    Record an authorized live feed with FFmpeg.
                </p>
            </div>

            <div class="card">
                <h2>AI Moments</h2>
                <p>
                    Analyze recordings and find high-energy moments.
                </p>
            </div>

            <div class="card">
                <h2>Two Clips</h2>
                <p>
                    Create a normal version and a vertical
                    blurred-background version.
                </p>
            </div>

            <div class="card">
                <h2>Creator System</h2>
                <p>
                    Organize recordings and clips by creator.
                </p>
            </div>

        </section>

    </body>
    </html>
    """


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "Clipz by Greg"
    }


# --------------------------------------------------
# CREATOR MANAGEMENT
# --------------------------------------------------

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


# --------------------------------------------------
# MANUAL RECORDING SYSTEM
# --------------------------------------------------

@app.post("/start-recording")
def start_recording(request: StartRecordingRequest):

    username = clean_username(request.username)

    if username not in creators:
        raise HTTPException(
            status_code=404,
            detail="Creator is not being monitored"
        )

    recording_id = str(uuid.uuid4())

    recordings[recording_id] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "status": "recording",
        "filename": None
    }

    return recordings[recording_id]


@app.post("/upload-recording")
async def upload_recording(
    recording_id: str = Form(...),
    file: UploadFile = File(...)
):

    if recording_id not in recordings:
        raise HTTPException(
            status_code=404,
            detail="Recording session not found"
        )

    recording = recordings[recording_id]

    username = recording["username"]

    extension = Path(file.filename or ".mp4").suffix

    if not extension:
        extension = ".mp4"

    filename = f"{username}_{uuid.uuid4()}{extension}"

    file_path = RECORDINGS_DIR / filename

    with open(file_path, "wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)

            if not chunk:
                break

            output.write(chunk)

    recording["filename"] = filename
    recording["file_path"] = str(file_path)
    recording["file_size"] = file_path.stat().st_size
    recording["uploaded_at"] = now()

    return {
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename,
        "linked_to_session": True
    }


@app.post("/stop-recording")
def stop_recording(request: StartRecordingRequest):

    username = clean_username(request.username)

    matches = [
        r for r in recordings.values()
        if r["username"] == username
        and r["status"] == "recording"
    ]

    if not matches:
        raise HTTPException(
            status_code=404,
            detail="No active recording found"
        )

    recording = matches[-1]

    recording["status"] = "completed"
    recording["stopped_at"] = now()

    if recording.get("file_path"):
        path = Path(recording["file_path"])

        if path.exists():
            recording["file_size"] = path.stat().st_size
            recording["duration"] = get_video_duration(path)

    return recording


# --------------------------------------------------
# LIVE FEED RECORDING
# --------------------------------------------------

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
            detail="A LIVE recording is already running for this creator"
        )

    validate_stream_url(request.stream_url)

    recording_id = str(uuid.uuid4())

    temp_filename = (
        f"{username}_{recording_id}.mkv"
    )

    final_filename = (
        f"{username}_{recording_id}.mp4"
    )

    temp_path = TEMP_DIR / temp_filename
    final_path = RECORDINGS_DIR / final_filename

    # Record the supplied authorized feed.
    #
    # MKV is used while recording because it is safer
    # for an interrupted/long-running recording.
    ffmpeg_command = [
        "ffmpeg",

        "-hide_banner",
        "-loglevel", "warning",

        "-y",

        # Reconnect for HTTP-based streams when possible.
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
            ffmpeg_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except FileNotFoundError:

        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed on the server"
        )

    live_processes[username] = process

    live_sessions[username] = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "temp_path": str(temp_path),
        "final_path": str(final_path)
    }

    watcher = threading.Thread(
        target=watch_live_process,
        args=(
            username,
            recording_id,
            process
        ),
        daemon=True
    )

    watcher.start()

    return {
        "status": "live recording started",
        "recording_id": recording_id,
        "username": username,
        "started_at": live_sessions[username]["started_at"]
    }


@app.get("/live-recording-status/{username}")
def live_recording_status(username: str):

    username = clean_username(username)

    if username not in live_processes:

        return {
            "username": username,
            "recording": False,
            "status": "not_recording"
        }

    process = live_processes[username]

    session = live_sessions.get(username)

    return {
        "username": username,
        "recording": True,
        "status": "recording",
        "recording_id": session["recording_id"],
        "started_at": session["started_at"],
        "process_running": process.poll() is None
    }


@app.post("/stop-live-recording")
def stop_live_recording(request: StartRecordingRequest):

    username = clean_username(request.username)

    if username not in live_processes:
        raise HTTPException(
            status_code=404,
            detail="No active LIVE recording found"
        )

    process = live_processes[username]

    session = live_sessions[username]

    recording_id = session["recording_id"]

    # Ask FFmpeg to stop gracefully.
    process.terminate()

    try:
        process.wait(timeout=15)

    except subprocess.TimeoutExpired:

        process.kill()
        process.wait()

    # Finalize the recording.
    finalize_live_recording(
        username,
        recording_id
    )

    recording = recordings.get(recording_id)

    return {
        "status": "live recording stopped",
        "recording": recording
    }


# --------------------------------------------------
# RECORDINGS
# --------------------------------------------------

@app.get("/recordings")
def get_recordings():

    return list(recordings.values())


@app.get("/recording-status/{username}")
def recording_status(username: str):

    username = clean_username(username)

    matches = [
        r for r in recordings.values()
        if r["username"] == username
    ]

    if not matches:
        return {
            "username": username,
            "recordings": []
        }

    return {
        "username": username,
        "recordings": matches
    }


# --------------------------------------------------
# VIDEO INFO
# --------------------------------------------------

def analyze_audio_energy(file_path):

    duration = get_video_duration(file_path)

    if duration <= 0:
        return []

    # Simple best-moment analysis.
    # Divides the video into windows and uses FFmpeg
    # audio statistics to estimate high-energy sections.

    window = 5

    moments = []

    current = 0

    while current < duration:

        end = min(
            current + window,
            duration
        )

        result = subprocess.run(
            [
                "ffmpeg",
                "-ss", str(current),
                "-t", str(end - current),
                "-i", str(file_path),
                "-af", "volumedetect",
                "-f", "null",
                "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stderr = result.stderr

        mean_volume = -60

        for line in stderr.splitlines():

            if "mean_volume" in line:

                try:
                    value = line.split(":")[-1].strip()
                    mean_volume = float(
                        value.replace(" dB", "")
                    )
                except Exception:
                    pass

        score = max(
            0,
            min(
                100,
                (mean_volume + 60) * 2
            )
        )

        moments.append({
            "start_time": round(current, 2),
            "end_time": round(end, 2),
            "duration": round(end - current, 2),
            "score": round(score, 1)
        })

        current += window

    moments.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best = moments[:3]

    for index, moment in enumerate(best, start=1):

        moment["rank"] = index

    return best


# --------------------------------------------------
# AI BEST MOMENTS
# --------------------------------------------------

@app.post("/find-best-moments")
def find_best_moments(request: StartRecordingRequest):

    recording_id = request.username

    # Allows either recording ID directly or username lookup.

    if recording_id in recordings:

        recording = recordings[recording_id]

    else:

        username = clean_username(request.username)

        matches = [
            r for r in recordings.values()
            if r["username"] == username
            and r.get("file_path")
        ]

        if not matches:
            raise HTTPException(
                status_code=404,
                detail="Recording not found"
            )

        recording = matches[-1]

    if not recording.get("file_path"):

        raise HTTPException(
            status_code=400,
            detail="Recording has no video file"
        )

    file_path = Path(recording["file_path"])

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file does not exist"
        )

    moments = analyze_audio_energy(
        file_path
    )

    return {
        "username": recording["username"],
        "recording_id": recording["recording_id"],
        "analyzed_at": now(),
        "moments": moments
    }


# --------------------------------------------------
# CREATE NORMAL CLIP
# --------------------------------------------------

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    if request.recording_id not in recordings:

        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    recording = recordings[request.recording_id]

    if not recording.get("file_path"):

        raise HTTPException(
            status_code=400,
            detail="Recording has no video file"
        )

    input_path = Path(recording["file_path"])

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

    result = run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-i", str(input_path),
            "-t", str(request.duration),
            "-c", "copy",
            str(output_path)
        ]
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
        "type": "normal"
    }

    clips[clip_id] = clip

    return {
        "status": "clip created",
        **clip
    }


# --------------------------------------------------
# VERTICAL BLURRED BACKGROUND CLIP
# --------------------------------------------------

def create_vertical_clip(
    input_path,
    output_path,
    start_time,
    duration
):

    filter_complex = (
        "[0:v]scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=30:10[bg];"

        "[0:v]scale=1080:1920:"
        "force_original_aspect_ratio=decrease[fg];"

        "[bg][fg]overlay="
        "(W-w)/2:(H-h)/2"
    )

    result = run_ffmpeg(
        [
            "ffmpeg",
            "-y",

            "-ss",
            str(start_time),

            "-i",
            str(input_path),

            "-t",
            str(duration),

            "-filter_complex",
            filter_complex,

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "20",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-movflags",
            "+faststart",

            str(output_path)
        ]
    )

    return result


# --------------------------------------------------
# CREATE AI CLIP
# --------------------------------------------------

@app.post("/create-ai-clip")
def create_ai_clip(request: AIClipRequest):

    if request.recording_id not in recordings:

        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    recording = recordings[request.recording_id]

    if not recording.get("file_path"):

        raise HTTPException(
            status_code=400,
            detail="Recording has no file"
        )

    input_path = Path(recording["file_path"])

    if not input_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found"
        )

    moments = analyze_audio_energy(
        input_path
    )

    selected = None

    for moment in moments:

        if moment["rank"] == request.moment_rank:

            selected = moment
            break

    if not selected:

        raise HTTPException(
            status_code=404,
            detail="Moment not found"
        )

    clip_id = str(uuid.uuid4())

    username = recording["username"]

    filename = (
        f"{username}_{clip_id}.mp4"
    )

    output_path = CLIPS_DIR / filename

    result = create_vertical_clip(
        input_path,
        output_path,
        selected["start_time"],
        selected["duration"]
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="FFmpeg failed to create AI clip"
        )

    clip = {
        "clip_id": clip_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": filename,
        "file_path": str(output_path),
        "created_at": now(),
        "duration": selected["duration"],
        "type": "ai_vertical",
        "moment_rank": selected["rank"],
        "score": selected["score"]
    }

    clips[clip_id] = clip

    return {
        "status": "AI clip created",
        **clip
    }


# --------------------------------------------------
# CREATE BOTH CLIPS
# --------------------------------------------------

@app.post("/create-two-clips")
def create_two_clips(request: TwoClipRequest):

    if request.recording_id not in recordings:

        raise HTTPException(
            status_code=404,
            detail="Recording not found"
        )

    recording = recordings[request.recording_id]

    if not recording.get("file_path"):

        raise HTTPException(
            status_code=400,
            detail="Recording has no file"
        )

    input_path = Path(recording["file_path"])

    if not input_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Recording file not found"
        )

    username = recording["username"]

    # ----------------------------------------------
    # CLIP 1: FULL / CLEAR VIDEO
    # ----------------------------------------------

    full_clip_id = str(uuid.uuid4())

    full_filename = (
        f"{username}_{full_clip_id}.mp4"
    )

    full_output = CLIPS_DIR / full_filename

    result = run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-ss", str(request.start_time),
            "-i", str(input_path),
            "-t", str(request.duration),
            "-c", "copy",
            str(full_output)
        ]
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="Failed to create full clip"
        )

    full_clip = {
        "clip_id": full_clip_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": full_filename,
        "file_path": str(full_output),
        "created_at": now(),
        "duration": request.duration,
        "type": "full_clear"
    }

    clips[full_clip_id] = full_clip

    # ----------------------------------------------
    # CLIP 2: 9:16 BLURRED BACKGROUND
    # ----------------------------------------------

    vertical_clip_id = str(uuid.uuid4())

    vertical_filename = (
        f"{username}_{vertical_clip_id}.mp4"
    )

    vertical_output = CLIPS_DIR / vertical_filename

    result = create_vertical_clip(
        input_path,
        vertical_output,
        request.start_time,
        request.duration
    )

    if result.returncode != 0:

        raise HTTPException(
            status_code=500,
            detail="Failed to create vertical clip"
        )

    vertical_clip = {
        "clip_id": vertical_clip_id,
        "username": username,
        "recording_id": request.recording_id,
        "filename": vertical_filename,
        "file_path": str(vertical_output),
        "created_at": now(),
        "duration": request.duration,
        "type": "vertical_blurred"
    }

    clips[vertical_clip_id] = vertical_clip

    return {
        "status": "two clips created",
        "full_clip": full_clip,
        "vertical_clip": vertical_clip
    }


# --------------------------------------------------
# CLIPS
# --------------------------------------------------

@app.get("/clips")
def get_clips():

    return list(clips.values())


@app.get("/clip/{clip_id}")
def get_clip(clip_id: str):

    if clip_id not in clips:

        raise HTTPException(
            status_code=404,
            detail="Clip not found"
        )

    clip = clips[clip_id]

    path = Path(clip["file_path"])

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


# --------------------------------------------------
# RUN
# --------------------------------------------------

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
