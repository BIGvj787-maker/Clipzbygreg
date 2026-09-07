from fastapi import FastAPI, Header, HTTPException, Request
import hashlib,hmac
from config import settings
from pipeline.events import emit_event

app=FastAPI(title="TikTok LIVE AI Bot Webhooks")
seen=set()

@app.post("/webhooks/make")
async def make_webhook(request: Request, x_webhook_signature: str|None=Header(default=None), x_idempotency_key: str|None=Header(default=None)):
    raw=await request.body()
    expected=hmac.new(settings.make_webhook_secret.encode(),raw,"sha256").hexdigest()
    if not settings.make_webhook_secret or not x_webhook_signature or not hmac.compare_digest(expected,x_webhook_signature):
        raise HTTPException(401,"invalid webhook signature")
    key=x_idempotency_key or hashlib.sha256(raw).hexdigest()
    if key in seen: return {"ok":True,"duplicate":True}
    seen.add(key)
    return {"ok":True}
