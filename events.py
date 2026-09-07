import hashlib, hmac, json, httpx
from config import settings

async def emit_event(event, creator, recording_id, extra=None):
    if not settings.make_webhook_url: return
    payload={"event":event,"creator":creator,"recording_id":recording_id,**(extra or {})}
    body=json.dumps(payload,separators=(",",":"))
    sig=hmac.new(settings.make_webhook_secret.encode(),body.encode(),"sha256").hexdigest()
    headers={"Content-Type":"application/json","X-Webhook-Signature":sig,"Idempotency-Key":hashlib.sha256(body.encode()).hexdigest()}
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.post(settings.make_webhook_url,content=body,headers=headers)
        r.raise_for_status()
