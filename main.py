import os
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

monitored_creators = set()
recordings = {}
recording_sessions = {}


class CreatorRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    username: str


class RecordingRequest(BaseModel):
    username: str


@app.get("/")
def home():
    return {"status": "Clipz by Greg is running"}


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
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "recording"
    }

    return {
        "status": "recording started",
        "username": username,
        "recording_id": recording_id,
        "started_at": recording_sessions[username]["started_at"]
    }


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
    session["stopped_at"] = datetime.now(timezone.utc).isoformat()

    recording_id = session["recording_id"]

    recordings[recording_id] = session
    del recording_sessions[username]

    return {
        "status": "recording stopped",
        "username": username,
        "recording_id": recording_id,
        "started_at": session["started_at"],
        "stopped_at": session["stopped_at"]
    }


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


@app.get("/recordings")
def get_recordings():
    return {
        "recordings": list(recordings.values())
    }


@app.post("/create-clip")
def create_clip(request: ClipRequest):
    username = request.username.lstrip("@").strip()

    creator_recordings = [
        r for r in recordings.values()
        if r["username"] == username
    ]

    return {
        "status": "clip request received",
        "username": username,
        "recordings_available": len(creator_recordings),
        "message": f"Ready to analyze recordings for @{username}"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
