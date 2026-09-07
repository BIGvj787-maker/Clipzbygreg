import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Clipz by Greg is running"}

@app.post("/clip")
def create_clip():
    return {
        "status": "clip request received",
        "message": "Clipz by Greg is ready to process a clip"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
