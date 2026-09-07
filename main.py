import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Clipz by Greg is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
