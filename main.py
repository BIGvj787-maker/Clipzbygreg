import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

monitored_creators = set()


class CreatorRequest(BaseModel):
    username: str


class ClipRequest(BaseModel):
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


@app.post("/create-clip")
def create_clip(request: ClipRequest):
    username = request.username.lstrip("@").strip()

    return {
        "status": "clip request received",
        "username": username,
        "message": f"Ready to process a clip for @{username}"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
