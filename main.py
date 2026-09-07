import os
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel


app = FastAPI(title="Clipz by Greg")


# ============================================================
# FOLDERS
# ============================================================

RECORDINGS_DIR = Path("recordings")
CLIPS_DIR = Path("clips")

RECORDINGS_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(exist_ok=True)


# ============================================================
# DATA
# ============================================================

monitored_creators = []
recordings = []
recording_sessions = {}
clips = []
best_moments = {}


# ============================================================
# MODELS
# ============================================================

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


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc).isoformat()


def clean_username(username):
    return username.strip().lstrip("@").lower()


def get_latest_recording(username):

    username = clean_username(username)

    user_recordings = [
        r for r in recordings
        if clean_username(r["username"]) == username
    ]

    if not user_recordings:
        return None

    return user_recordings[-1]


# ============================================================
# HOMEPAGE
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home():

    return """
    <!DOCTYPE html>
    <html>

    <head>

        <title>Clipz by Greg</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>

            * {
                box-sizing: border-box;
            }

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

            .status {
                color: #a78bfa;
                font-size: 14px;
            }

            .hero {
                padding: 100px 8%;
                text-align: center;
            }

            .badge {
                display: inline-block;
                padding: 8px 14px;
                border: 1px solid #3b1f5c;
                border-radius: 999px;
                color: #c4b5fd;
                background: #120b1d;
                margin-bottom: 25px;
            }

            .hero h1 {
                font-size: 64px;
                margin: 0 0 20px;
            }

            .hero p {
                color: #aaa;
                font-size: 20px;
                max-width: 650px;
                margin: auto;
                line-height: 1.6;
            }

            .button {
                display: inline-block;
                margin-top: 30px;
                padding: 15px 25px;
                background: #7c3aed;
                border-radius: 10px;
                color: white;
                text-decoration: none;
                font-weight: bold;
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
                width: 250px;
            }

            .card h2 {
                margin-top: 0;
            }

            .card p {
                color: #aaa;
                line-height: 1.5;
            }

            footer {
                text-align: center;
                padding: 50px;
                color: #666;
            }

        </style>

    </head>

    <body>

        <nav>

            <div class="logo">
                Clipz by Greg
            </div>

            <div class="status">
                ● SYSTEM ONLINE
            </div>

        </nav>


        <section class="hero">

            <div class="badge">
                CLIPZ BY GREG
            </div>

            <h1>
                Turn moments into clips.
            </h1>

            <p>
                Recordings, AI moment detection and
                vertical social-ready clips in one system.
            </p>

            <a class="button" href="/docs">
                Open API
            </a>

        </section>


        <section class="features">

            <div class="card">

                <h2>
                    Creators
                </h2>

                <p>
                    Manage creators you are authorized
                    to process.
                </p>

            </div>


            <div class="card">

                <h2>
                    Recordings
                </h2>

                <p>
                    Upload and connect recordings
                    to their creator.
                </p>

            </div>


            <div class="card">

                <h2>
                    AI Moments
                </h2>

                <p>
                    Find high-energy moments and
                    rank potential clips.
                </p>

            </div>


            <div class="card">

                <h2>
                    Vertical Clips
                </h2>

                <p>
                    Create a 9:16 social-ready video
                    with a blurred background.
                </p>

            </div>

        </section>


        <footer>

            Clipz by Greg

        </footer>

    </body>

    </html>
    """


# ============================================================
# CREATOR MANAGEMENT
# ============================================================

@app.post("/add-creator")
def add_creator(request: CreatorRequest):

    username = clean_username(request.username)

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


# ============================================================
# RECORDING
# ============================================================

@app.post("/start-recording")
def start_recording(request: RecordingRequest):

    username = clean_username(request.username)

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

    username = clean_username(username)

    recording_id = None

    if username in recording_sessions:

        recording_id = recording_sessions[
            username
        ]["recording_id"]

    filename = f"{username}_{uuid.uuid4()}.mp4"

    file_path = RECORDINGS_DIR / filename

    with open(file_path, "wb") as f:

        f.write(await file.read())

    recording = {

        "recording_id":
            recording_id or str(uuid.uuid4()),

        "username":
            username,

        "filename":
            filename,

        "file_path":
            str(file_path),

        "uploaded_at":
            now()
    }

    recordings.append(recording)

    return {

        "status":
            "recording uploaded",

        "recording_id":
            recording["recording_id"],

        "username":
            username,

        "filename":
            filename,

        "linked_to_session":
            recording_id is not None
    }


@app.post("/stop-recording")
def stop_recording(request: RecordingRequest):

    username = clean_username(request.username)

    session = recording_sessions.get(username)

    if not session:

        return {
            "error":
                "No active recording."
        }

    session["status"] = "stopped"

    session["stopped_at"] = now()

    return session


@app.get("/recordings")
def get_recordings():

    return {
        "recordings":
            recordings
    }


# ============================================================
# AI BEST MOMENT DETECTION
# ============================================================

@app.post("/find-best-moments")
def find_best_moments(
    request: BestMomentsRequest
):

    username = clean_username(request.username)

    recording = get_latest_recording(username)

    if not recording:

        return {
            "error":
                "No recording found for this creator."
        }

    input_file = Path(
        recording["file_path"]
    )

    if not input_file.exists():

        return {
            "error":
                "Recording file does not exist on the server."
        }


    # --------------------------------------------------------
    # GET VIDEO DURATION
    # --------------------------------------------------------

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

        duration = float(
            probe.stdout.strip()
        )

    except:

        return {
            "error":
                "Could not determine recording duration."
        }


    if duration <= 5:

        return {
            "error":
                "Recording is too short."
        }


    # --------------------------------------------------------
    # ANALYZE AUDIO ENERGY
    # --------------------------------------------------------

    segment_length = 10

    segments = []

    current = 0

    while current < duration:

        remaining = duration - current

        length = min(
            segment_length,
            remaining
        )

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
                            line.split(
                                "mean_volume:"
                            )[1]
                            .split("dB")[0]
                            .strip()
                        )

                    except:

                        pass


            segments.append({

                "start_time":
                    round(current, 2),

                "duration":
                    round(length, 2),

                "mean_volume":
                    mean_volume
            })


        current += segment_length


    # --------------------------------------------------------
    # RANK MOMENTS
    # --------------------------------------------------------

    segments.sort(

        key=lambda x:
            x["mean_volume"],

        reverse=True
    )


    top_segments = segments[:5]

    moments = []


    for index, segment in enumerate(
        top_segments,
        start=1
    ):

        start = max(
            0,
            segment["start_time"] - 5
        )

        clip_duration = min(
            30,
            duration - start
        )


        moments.append({

            "rank":
                index,

            "start_time":
                round(start, 2),

            "end_time":
                round(
                    start + clip_duration,
                    2
                ),

            "duration":
                round(
                    clip_duration,
                    2
                ),

            "score":
                round(

                    max(
                        0,
                        min(
                            100,
                            (
                                segment[
                                    "mean_volume"
                                ] + 60
                            ) * 2
                        )
                    ),

                    1
                )
        })


    result = {

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "analyzed_at":
            now(),

        "moments":
            moments
    }


    best_moments[username] = result

    return result


@app.get("/best-moments/{username}")
def get_best_moments(username: str):

    username = clean_username(username)

    result = best_moments.get(username)

    if not result:

        return {
            "error":
                "No AI analysis has been run yet."
        }

    return result


# ============================================================
# NORMAL 30-SECOND CLIP
# ============================================================

@app.post("/create-clip")
def create_clip(request: ClipRequest):

    username = clean_username(request.username)

    recording = get_latest_recording(username)

    if not recording:

        return {
            "error":
                "No recording found."
        }

    input_file = Path(
        recording["file_path"]
    )

    if not input_file.exists():

        return {
            "error":
                "Recording file does not exist."
        }


    clip_id = str(uuid.uuid4())

    filename = (
        f"{username}_{clip_id}.mp4"
    )

    output_file = (
        CLIPS_DIR / filename
    )


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
            "-movflags",
            "+faststart",
            str(output_file)
        ],

        capture_output=True,
        text=True
    )


    if result.returncode != 0:

        return {

            "error":
                "FFmpeg failed.",

            "details":
                result.stderr[-2000:]
        }


    clip = {

        "clip_id":
            clip_id,

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "filename":
            filename,

        "file_path":
            str(output_file),

        "created_at":
            now(),

        "duration":
            30,

        "format":
            "original"
    }


    clips.append(clip)

    return {

        "status":
            "clip created",

        **clip
    }


# ============================================================
# AI VERTICAL CLIP
# ============================================================

@app.post("/create-ai-clip")
def create_ai_clip(
    request: AIClipRequest
):

    username = clean_username(request.username)

    recording = get_latest_recording(username)

    if not recording:

        return {
            "error":
                "No recording found."
        }


    input_file = Path(
        recording["file_path"]
    )

    if not input_file.exists():

        return {
            "error":
                "Recording file does not exist."
        }


    start_time = max(
        0,
        request.start_time
    )

    duration = max(
        5,
        min(
            60,
            request.duration
        )
    )


    clip_id = str(uuid.uuid4())

    filename = (
        f"{username}_{clip_id}_vertical.mp4"
    )

    output_file = (
        CLIPS_DIR / filename
    )


    # --------------------------------------------------------
    # 9:16 VERTICAL LAYOUT
    #
    # BACKGROUND:
    #   Enlarged version of the video
    #   Cropped to 1080x1920
    #   Blurred
    #
    # FOREGROUND:
    #   Full video
    #   Kept inside the 9:16 frame
    #   Centered
    # --------------------------------------------------------

    filter_complex = (

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=20:10"
        "[bg];"

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease"
        "[fg];"

        "[bg][fg]"
        "overlay="
        "(W-w)/2:"
        "(H-h)/2,"
        "setsar=1"
    )


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

            "-filter_complex",
            filter_complex,

            "-map",
            "0:v:0",

            "-map",
            "0:a?",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-movflags",
            "+faststart",

            str(output_file)
        ],

        capture_output=True,
        text=True
    )


    if result.returncode != 0:

        return {

            "error":
                "Vertical video creation failed.",

            "details":
                result.stderr[-3000:]
        }


    clip = {

        "clip_id":
            clip_id,

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "filename":
            filename,

        "file_path":
            str(output_file),

        "created_at":
            now(),

        "start_time":
            start_time,

        "duration":
            duration,

        "source":
            "ai_best_moment",

        "format":
            "vertical_9_16",

        "layout":
            "blurred_background_with_full_video"
    }


    clips.append(clip)


    return {

        "status":
            "AI vertical clip created",

        **clip
    }


# ============================================================
# CREATE BOTH VERSIONS
# ============================================================

@app.post("/create-two-clips")
def create_two_clips(
    request: AIClipRequest
):

    username = clean_username(request.username)

    recording = get_latest_recording(username)

    if not recording:

        return {
            "error":
                "No recording found."
        }


    input_file = Path(
        recording["file_path"]
    )

    if not input_file.exists():

        return {
            "error":
                "Recording file does not exist."
        }


    start_time = max(
        0,
        request.start_time
    )

    duration = max(
        5,
        min(
            60,
            request.duration
        )
    )


    # ========================================================
    # CLIP 1 — FULL / ORIGINAL
    # ========================================================

    full_id = str(uuid.uuid4())

    full_filename = (
        f"{username}_{full_id}_full.mp4"
    )

    full_output = (
        CLIPS_DIR / full_filename
    )


    full_result = subprocess.run(

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

            "-movflags",
            "+faststart",

            str(full_output)
        ],

        capture_output=True,
        text=True
    )


    if full_result.returncode != 0:

        return {

            "error":
                "Full clip creation failed.",

            "details":
                full_result.stderr[-2000:]
        }


    full_clip = {

        "clip_id":
            full_id,

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "filename":
            full_filename,

        "file_path":
            str(full_output),

        "created_at":
            now(),

        "start_time":
            start_time,

        "duration":
            duration,

        "type":
            "full_video",

        "format":
            "original"
    }


    clips.append(full_clip)


    # ========================================================
    # CLIP 2 — BLURRED BACKGROUND
    # ========================================================

    vertical_id = str(uuid.uuid4())

    vertical_filename = (
        f"{username}_{vertical_id}_vertical.mp4"
    )

    vertical_output = (
        CLIPS_DIR / vertical_filename
    )


    filter_complex = (

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "boxblur=20:10"
        "[bg];"

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease"
        "[fg];"

        "[bg][fg]"
        "overlay="
        "(W-w)/2:"
        "(H-h)/2,"
        "setsar=1"
    )


    vertical_result = subprocess.run(

        [
            "ffmpeg",
            "-y",

            "-ss",
            str(start_time),

            "-i",
            str(input_file),

            "-t",
            str(duration),

            "-filter_complex",
            filter_complex,

            "-map",
            "0:v:0",

            "-map",
            "0:a?",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-movflags",
            "+faststart",

            str(vertical_output)
        ],

        capture_output=True,
        text=True
    )


    if vertical_result.returncode != 0:

        return {

            "error":
                "Vertical clip creation failed.",

            "details":
                vertical_result.stderr[-3000:]
        }


    vertical_clip = {

        "clip_id":
            vertical_id,

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "filename":
            vertical_filename,

        "file_path":
            str(vertical_output),

        "created_at":
            now(),

        "start_time":
            start_time,

        "duration":
            duration,

        "type":
            "blurred_background",

        "format":
            "vertical_9_16",

        "layout":
            "blurred_background_with_full_video"
    }


    clips.append(vertical_clip)


    # ========================================================
    # RETURN BOTH
    # ========================================================

    return {

        "status":
            "two clips created",

        "username":
            username,

        "recording_id":
            recording["recording_id"],

        "clips": [

            full_clip,

            vertical_clip

        ]
    }


# ============================================================
# CLIPS
# ============================================================

@app.get("/clips")
def get_clips():

    return {
        "clips":
            clips
    }


@app.get("/clip/{clip_id}")
def get_clip(clip_id: str):

    for clip in clips:

        if clip["clip_id"] == clip_id:

            file_path = Path(
                clip["file_path"]
            )

            if file_path.exists():

                return FileResponse(

                    file_path,

                    media_type="video/mp4",

                    filename=
                        clip["filename"]
                )


    return {
        "error":
            "Clip not found."
    }


# ============================================================
# RECORDING STATUS
# ============================================================

@app.get("/recording-status/{username}")
def recording_status(username: str):

    username = clean_username(username)

    return recording_sessions.get(

        username,

        {
            "username":
                username,

            "status":
                "not recording"
        }
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {

        "status":
            "ok",

        "service":
            "Clipz by Greg"
    }


# ============================================================
# SERVER
# ============================================================

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
