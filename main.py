import os
import time
import asyncio
import subprocess
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from moviepy.editor import VideoFileClip
import streamlink

app = FastAPI()

# In-memory tracking lists
monitored_creators = set()
currently_recording = set()

# Official TikTok Configuration
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "7682396267984619541")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "YOUR_USER_ACCESS_TOKEN")

# --- DATA MODELS ---
class CreatorRequest(BaseModel):
    username: str

class LiveClipRequest(BaseModel):
    username: str
    stream_url: str        
    duration_sec: int = 60 
    caption: str = "Live stream highlight!"

# --- TIKTOK API UPLOADER ENGINE ---
def upload_to_tiktok(video_file_path: str, caption: str):
    """Publishes the finalized video file using TikTok's Content Posting API."""
    if TIKTOK_ACCESS_TOKEN == "YOUR_USER_ACCESS_TOKEN":
        print("[TikTok Upload] Skipped: Real access token not configured.")
        return False

    init_url = "https://tiktokapis.com"
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    file_size = os.path.getsize(video_file_path)
    init_data = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": file_size,
            "total_chunk_count": 1
        },
        "post_info": {
            "title": caption,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False
        }
    }
    
    try:
        # Step A: Initialize upload session
        response = requests.post(init_url, headers=headers, json=init_data)
        res_data = response.json()
        
        if response.status_code != 200 or res_data.get("error", {}).get("code") != "ok":
            print(f"[TikTok Upload] Init Failed: {res_data}")
            return False
            
        # Step B: Securely stream video bytes directly to TikTok target URL
        upload_url = res_data["data"]["upload_url"]
        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
        }
        
        with open(video_file_path, "rb") as video_file:
            upload_res = requests.put(upload_url, headers=upload_headers, data=video_file)
            
        # Fixed list validation - checks for valid API response codes
        if upload_res.status_code in:
            print("[TikTok Upload] Success! Clip posted safely.")
            return True
        else:
            print(f"[TikTok Upload] Byte upload failed: {upload_res.text}")
            return False
            
    except Exception as e:
        print(f"[TikTok Upload] Request Exception: {str(e)}")
        return False

# --- LIVE CAPTURE & PROCESSING PIPELINE ---
def record_and_clip_live(stream_url: str, duration_sec: int, username: str, caption: str):
    """Asynchronously records an active stream, transforms to 9:16, and uploads."""
    timestamp = int(time.time())
    raw_recorded_file = f"{username}_live_{timestamp}.mp4"
    final_tiktok_clip = f"{username}_tiktok_{timestamp}.mp4"
    
    print(f"[Pipeline] Verifying live status for {stream_url}...")
    
    try:
        # Step 1: Hook stream using Streamlink
        session = streamlink.Streamlink()
        streams = session.streams(stream_url)
        
        if not streams:
            print(f"[Pipeline] Error: Stream offline or link broken: {stream_url}")
            return
        
        best_stream = streams['best']
        stream_m3u8_url = best_stream.url
        
        # Step 2: Stream copy raw segments using FFmpeg (Low CPU load)
        print(f"[Pipeline] Capturing {duration_sec}s of live stream video...")
        ffmpeg_cmd = [
            'ffmpeg', '-y', 
            '-i', stream_m3u8_url,       
            '-t', str(duration_sec),     
            '-c', 'copy',                
            raw_recorded_file
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Step 3: Vertical 9:16 center-cropping transformation
        if os.path.exists(raw_recorded_file):
            print(f"[Pipeline] Formatting captured source to 9:16...")
            video = VideoFileClip(raw_recorded_file)
            new_width = int(video.h * (9 / 16))
            video_vertical = video.crop(x_center=video.w / 2, width=new_width, height=video.h)
            
            video_vertical.write_videofile(
                final_tiktok_clip, 
                codec="libx264", 
                audio_codec="aac",
                fps=30,
                logger=None 
            )
            
            # Close file logs to clean memory locks
            video.close()
            video_vertical.close()
            os.remove(raw_recorded_file)
            print(f"[Pipeline] Vertical conversion compiled: {final_tiktok_clip}")
            
            # Step 4: Post straight to your TikTok app flow
            upload_to_tiktok(video_file_path=final_tiktok_clip, caption=caption)
            
            if os.path.exists(final_tiktok_clip):
                os.remove(final_tiktok_clip)
        else:
            print("[Pipeline] Error: Raw capture was never written by FFmpeg.")

    except Exception as e:
        print(f"[Pipeline] Processing execution failed: {str(e)}")
    finally:
        currently_recording.discard(username)

# --- 24/7 AUTOMATED LIVE STREAM MONITOR ---
async def continuous_stream_monitor():
    """Loops indefinitely, checking if tracked creators are live on Twitch."""
    await asyncio.sleep(5)
    print("[Monitor] Automated 24/7 Live Stream Check Engine started.")
    
    while True:
        for username in list(monitored_creators):
            if username in currently_recording:
                continue 
                
            stream_url = f"https://twitch.tv{username}"
            
            try:
                session = streamlink.Streamlink()
                streams = session.streams(stream_url)
                
                if streams:
                    print(f"[Monitor] ALERT! @{username} just went live! Initializing automatic clip bot...")
                    currently_recording.add(username)
                    
                    asyncio.to_thread(
                        record_and_clip_live,
                        stream_url=stream_url,
                        duration_sec=60, 
                        username=username,
                        caption=f"Insane live stream moment from @{username}! #twitch #clips #gaming"
                    )
            except Exception as e:
                print(f"[Monitor] Error scanning stream status for @{username}: {str(e)}")
                
        # Scan your creator lists every 2 minutes
        await asyncio.sleep(120)

# --- FASTAPI LIFECYCLE MANAGEMENT ---
@app.on_event("startup")
async def startup_event():
    # Automatically boots up the background check loop thread
    asyncio.create_task(continuous_stream_monitor())

# --- YOUR ORIGINAL SYSTEM ENDPOINTS ---
@app.get("/")
def home():
    return {"status": "Clipz by Greg is running"}

@app.post("/add-creator")
def add_creator(request: CreatorRequest):
    username = request.username.lstrip("@").strip().lower()
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
def create_clip(request: LiveClipRequest, background_tasks: BackgroundTasks):
    username = request.username.lstrip("@").strip().lower()
    
    if username in currently_recording:
        return {"status": "busy", "message": f"Already processing a clip for @{username} right now."}
        
    currently_recording.add(username)
    
    # Offloads recording pipeline completely out of main thread window
    background_tasks.add_task(
        record_and_clip_live, 
        stream_url=request.stream_url, 
        duration_sec=request.duration_sec, 
        username=username,
        caption=f"{request.caption} @{username} #clips"
    )

    return {
        "status": "recording_initiated",
        "username": username,
        "message": f"Ready to process a clip for @{username}"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
