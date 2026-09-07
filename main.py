import os
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel


app = FastAPI(title="Clipz by Greg")


# -----------------------------
# FOLDERS
# -----------------------------

RECORDINGS_DIR = Path("recordings")
CLIPS_DIR = Path("clips")

RECORDINGS_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)


# -----------------------------
# IN-MEMORY DATA
# -----------------------------

monitored_creators = []
recordings = []
recording_sessions = {}
clips = []
best_moments = {}


# -----------------------------
# MODELS
# -----------------------------

class CreatorRequest(BaseModel):
    username: str


class RecordingRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    username: str


class BestMomentsRequest(BaseModel):
    username: str


class AIClipRequest(BaseModel):
    username: str
    start_time: float
    duration: float = 30


# -----------------------------
# HELPERS
# -----------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def get_latest_recording(username):
    user_recordings = [
        r for r in recordings
        if r["username"].lower() == username.lower()
    ]

    if not user_recordings:
        return None

    return user_recordings[-1]


# -----------------------------
# HOMEPAGE
# -----------------------------

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
                background: #090511;
                color: white;
            }

            nav {
                padding: 22px 8%;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #0d0718;
                border-bottom: 1px solid #241536;
            }

            .logo {
                font-size: 24px;
                font-weight: bold;
            }

            .hero {
                padding: 100px 8%;
                text-align: center;
            }

            .hero h1 {
                font-size: 64px;
                margin-bottom: 15px;
            }

            .hero p {
                color: #aaa;
                font-size: 20px;
            }

            .button {
                display: inline-block;
                margin-top: 30px;
                padding: 15px 25px;
                background: #7c3aed;
                border-radius: 10px;
                color: white;
                text-decoration: none;
            }

            .features {
                display: flex;
                gap: 20px;
                justify-content: center;
                padding: 50px 8%;
                flex-wrap: wrap;
            }

            .card {
                background: #120b1d;
                border: 1px solid #2b193d;
                border-radius: 15px;
                padding: 30px;
                width: 240px;
            }

            .card h2 {
                margin-top: 0;
            }

            .card p {
                color: #aaa;
                line-height: 1.5;
            }
        </style>
    </head>

    <body>

        <nav>
            <div class="logo">Clipz by Greg</div>
            <div>AI Clipping System</div>
        </nav>

        <section class="hero">
            <h1>Turn moments into clips.</h1>

            <p>
                Recordings, AI moment detection, and instant clips
                in one system.
            </p>

            <a class="button" href="/docs">
                Open API
            </a>
        </section>

        <section class="features">

            <div class="card">
                <h2>Creators</h2>
                <p>
                    Keep track of creators you are authorized to monitor
                    and process.
                </p>
            </div>

            <div class="card">
                <h2>Recordings</h2>
                <p>
                    Store recordings and connect them to the creator
                    they belong to.
                </p>
            </div>

            <div class="card">
                <h2>AI Moments</h2>
                <p>
                    Analyze recordings and identify high-energy moments
                    that could make good clips.
                </p>
            </div>

            <div class="card">
                <h2>Clips</h2>
                <p>
                    Turn selected moments into downloadable MP4 clips.
                </p>
            </div>

        </section>

    </body>
    </html>
    """


# -----------------------------
# CREATOR
# -----------------------------

@app.post("/add-creator")
def add_creator(request: CreatorRequest):

    username = request.username.strip().lstrip("@")

    if username not in monitored_creators:
        monitored_creators.append(username)

    return {
        "status": "creator added",
        "username": username,
        "monitoring": True
    }


@app.get("/creators")
def get_creators():

    return {
        "creators": monitored_creators
    }


# -----------------------------
# RECORDING
# -----------------------------

@app.post("/start-recording")
def start_recording(request: RecordingRequest):

    username = request.username.strip().lstrip("@")

    if username not in monitored_creators:
        return {
            "error": "Creator is not being monitored."
        }

    recording_id = str(uuid.uuid4())

    session = {
        "recording_id": recording_id,
        "username": username,
        "started_at": now(),
        "status": "recording",
        "filename": None
    }

    recording_sessions[username] = session

    return session


@app.post("/upload-recording")
async def upload_recording(
    username: str = Form(...),
    file: UploadFile = File(...)
):

    username = username.strip().lstrip("@")

    recording_id = None

    if username in recording_sessions:
        recording_id = recording_sessions[username]["recording_id"]

    filename = f"{username}_{uuid.uuid4()}.mp4"
    file_path = RECORDINGS_DIR / filename

    with open(file_path, "wb") as f:
        f.write(await file.read())

    recording = {
        "recording_id": recording_id or str(uuid.uuid4()),
        "username": username,
        "filename": filename,
        "file_path": str(file_path),
        "uploaded_at": now()
    }

    recordings.append(recording)

    return {
        "status": "recording uploaded",
        "recording_id": recording["recording_id"],
        "username": username,
        "filename": filename,
        "linked_to_session": recording_id is not None
    }


@app.post("/stop-recording")
def stop_recording(request: RecordingRequest):

    username = request.username.strip().lstrip("@")

    session = recording_sessions.get(username)

    if not session:
        return {
            "error": "No active recording."
        }

    session["status"] = "stopped"
    session["stopped_at"] = now()

    return session


@app.get("/recordings")
def get_recordings():

    return {
        "recordings": recordings
    }


# -----------------------------
# AI BEST MOMENTS
# -----------------------------

@app.post("/find-best-moments")
def find_best_moments(request: BestMomentsRequest):

    username = request.username.strip().lstrip("@")

    recording = get_latest_recording(username)

    if not recording:
        return {
            "error": "No recording found for this creator."
        }

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {
            "error": "Recording file does not exist on the server."
        }

    # Get video duration
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_file)
        ],
        capture_output=True,
        text=True
    )

    try:
        duration = float(probe.stdout.strip())
    except:
        return {
            "error": "Could not determine recording duration."
        }

    if duration <= 5:
        return {
            "error": "Recording is too short."
        }

    # ---------------------------------
    # First AI-style scoring pass
    # ---------------------------------
    #
    # We divide the recording into sections.
    # FFmpeg measures audio energy in each section.
    # Louder / more energetic sections receive
    # higher scores.
    #

    segment_length = 10

    segments = []

    current = 0

    while current < duration:

        remaining = duration - current

        length = min(segment_length, remaining)

        if length >= 3:

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-ss",
                    str(current),
                    "-t",
                    str(length),
                    "-i",
                    str(input_file),
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-"
                ],
                capture_output=True,
                text=True
            )

            output = result.stderr

            mean_volume = -60.0

            for line in output.splitlines():

                if "mean_volume" in line:

                    try:
                        mean_volume = float(
                            line.split("mean_volume:")[1]
                            .split("dB")[0]
                            .strip()
                        )
                    except:
                        pass

            segments.append({
                "start_time": round(current, 2),
                "duration": round(length, 2),
                "mean_volume": mean_volume
            })

        current += segment_length

    # Rank segments by energy
    segments.sort(
        key=lambda x: x["mean_volume"],
        reverse=True
    )

    top_segments = segments[:5]

    moments = []

    for index, segment in enumerate(top_segments, start=1):

        start = max(
            0,
            segment["start_time"] - 5
        )

        clip_duration = min(
            30,
            duration - start
        )

        moments.append({
            "rank": index,
            "start_time": round(start, 2),
            "end_time": round(
                start + clip_duration,
                2
            ),
            "duration": round(
                clip_duration,
                2
            ),
            "score": round(
                max(
                    0,
                    min(
                        100,
                        (segment["mean_volume"] + 60) * 2
                    )
                ),
                1
            )
        })

    best_moments[username] = {
        "username": username,
        "recording_id": recording["recording_id"],
        "analyzed_at": now(),
        "moments": moments
    }

    return best_moments[username]


@app.get("/best-moments/{username}")
def get_best_moments(username: str):

    username = username.strip().lstrip("@")

    result = best_moments.get(username)

    if not result:
        return {
            "error": "No AI analysis has been run yet."
        }

    return result


# -----------------------------
# CREATE NORMAL CLIP
# -----------------------------

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    username = request.username.strip().lstrip("@")

    recording = get_latest_recording(username)

    if not recording:
        return {
            "error": "No recording found."
        }

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {
            "error": "Recording file does not exist."
        }

    clip_id = str(uuid.uuid4())

    filename = f"{username}_{clip_id}.mp4"

    output_file = CLIPS_DIR / filename

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

    if result.returncode != 0:

        return {
            "error": "FFmpeg failed.",
            "details": result.stderr[-2000:]
        }

    clip = {
        "clip_id": clip_id,
        "username": username,
        "recording_id": recording["recording_id"],
        "filename": filename,
        "file_path": str(output_file),
        "created_at": now(),
        "duration": 30
    }

    clips.append(clip)

    return {
        "status": "clip created",
        **clip
    }


# -----------------------------
# CREATE AI CLIP
# -----------------------------

@app.post("/create-ai-clip")
def create_ai_clip(request: AIClipRequest):

    username = request.username.strip().lstrip("@")

    recording = get_latest_recording(username)

    if not recording:
        return {
            "error": "No recording found."
        }

    input_file = Path(recording["file_path"])

    if not input_file.exists():
        return {
            "error": "Recording file does not exist."
        }

    start_time = max(0, request.start_time)

    duration = max(
        5,
        min(60, request.duration)
    )

    clip_id = str(uuid.uuid4())

    filename = f"{username}_{clip_id}.mp4"

    output_file = CLIPS_DIR / filename

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start_time),
            "-i",
            str(input_file),
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_file)
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        return {
            "error": "FFmpeg failed.",
            "details": result.stderr[-2000:]
        }

    clip = {
        "clip_id": clip_id,
        "username": username,
        "recording_id": recording["recording_id"],
        "filename": filename,
        "file_path": str(output_file),
        "created_at": now(),
        "start_time": start_time,
        "duration": duration,
        "source": "ai_best_moment"
    }

    clips.append(clip)

    return {
        "status": "AI clip created",
        **clip
    }


# -----------------------------
# CLIPS
# -----------------------------

@app.get("/clips")
def get_clips():

    return {
        "clips": clips
    }


@app.get("/clip/{clip_id}")
def get_clip(clip_id: str):

    for clip in clips:

        if clip["clip_id"] == clip_id:

            file_path = Path(clip["file_path"])

            if file_path.exists():

                return FileResponse(
                    file_path,
                    media_type="video/mp4",
                    filename=clip["filename"]
                )

    return {
        "error": "Clip not found."
    }


# -----------------------------
# STATUS
# -----------------------------

@app.get("/recording-status/{username}")
def recording_status(username: str):

    username = username.strip().lstrip("@")

    return recording_sessions.get(
        username,
        {
            "username": username,
            "status": "not recording"
        }
    )


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "Clipz by Greg"
    }


# -----------------------------
# START SERVER
# -----------------------------

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
