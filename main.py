import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ClipRequest(BaseModel):
    username: str


@app.get("/")
def home():
    return {"status": "Clipz by Greg is running"}


@app.post("/create-clip")
def create_clip(request: ClipRequest):
    return {
        "status": "clip request received",
        "username": request.username,
        "message": f"Ready to process a clip for @{request.username}"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
