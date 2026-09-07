import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Clipz by Greg")

# Local storage for uploaded recordings.
# This is a starter setup; persistent cloud storage can be added next.
UPLOAD_DIR = Path("recordings")
UPLOAD_DIR.mkdir(exist_ok=True)

monitored_creators = set()
recordings = {}


class CreatorRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
    username: str


@app.get("/")
def home():
    return {
        "status": "Clipz by Greg is running",
        "creators": len(monitored_creators),
        "recordings": len(recordings)
    }


@app.post("/add-creator")
def add_creator(request: CreatorRequest):
    username = request.username.lstrip("@").strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

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


@app.post("/upload-recording")
async def upload_recording(
    username: str = Form(...),
    file: UploadFile = File(...)
):
    username = username.lstrip("@").strip()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    if username not in monitored_creators:
        raise HTTPException(
            status_code=404,
            detail=f"Creator @{username} is not being monitored"
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")

    recording_id = str(uuid.uuid4())
    extension = Path(file.filename).suffix or ".mp4"
    filename = f"{username}_{recording_id}{extension}"
    file_path = UPLOAD_DIR / filename

    with file_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    recordings[recording_id] = {
        "id": recording_id,
        "username": username,
        "filename": filename,
        "path": str(file_path),
        "status": "uploaded"
    }

    return {
        "status": "recording uploaded",
        "recording_id": recording_id,
        "username": username,
        "filename": filename
    }


@app.get("/recordings")
def get_recordings():
    return {
        "recordings": list(recordings.values())
    }


@app.post("/create-clip")
def create_clip(request: ClipRequest):
    username = request.username.lstrip("@").strip()

    matching_recordings = [
        recording
        for recording in recordings.values()
        if recording["username"] == username
    ]

    if not matching_recordings:
        return {
            "status": "no recording found",
            "username": username,
            "message": f"No recording is available for @{username} yet."
        }

    return {
        "status": "clip request received",
        "username": username,
        "recordings_available": len(matching_recordings),
        "message": f"Ready to analyze recordings for @{username}"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
