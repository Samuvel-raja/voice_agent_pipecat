import os
import subprocess
import threading
import json
import urllib.request
import urllib.error
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from loguru import logger

app = FastAPI()

SERVER_PORT = 7870

BOT_HTTP_BASE = "http://localhost:7860"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionConfig(BaseModel):
    pass


_bot_lock = threading.Lock()
_bot_process: Optional[subprocess.Popen] = None


def _is_running(p: Optional[subprocess.Popen]) -> bool:
    return p is not None and p.poll() is None


def _proxy_json(method: str, url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
        logger.error(f"Proxy error {method} {url}: {e.code} {raw}")
        raise HTTPException(status_code=e.code, detail=raw or str(e))
    except Exception as e:
        logger.exception(f"Proxy error {method} {url}: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/webrtc/offer")
async def webrtc_offer(request: Request):
    payload = await request.json()
    return _proxy_json("POST", f"{BOT_HTTP_BASE}/api/offer", payload)


@app.patch("/webrtc/offer")
async def webrtc_ice_candidate(request: Request):
    payload = await request.json()
    return _proxy_json("PATCH", f"{BOT_HTTP_BASE}/api/offer", payload)

@app.post("/connect")
async def connect(config: Optional[SessionConfig] = None):
    try:
        global _bot_process
        with _bot_lock:
            if _is_running(_bot_process):
                return {
                    "status": "ok",
                    "transport": "webrtc",
                    "already_running": True,
                    "pid": _bot_process.pid,
                }

            # Start bot.py as a subprocess using WebRTC transport.
            # Use 'uv run' to ensure it uses the correct environment.
            # We pass --transport webrtc because Daily is not available on Windows.
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            _bot_process = subprocess.Popen(
                ["uv", "run", "bot.py", "--transport", "webrtc"],
                env=os.environ.copy(),
                creationflags=creationflags,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

        return {
            "status": "ok",
            "transport": "webrtc",
            "already_running": False,
            "pid": _bot_process.pid if _bot_process else None,
            "config": {
                "webrtc_config": {} 
            }
        }
    except Exception as e:
        logger.exception(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disconnect")
async def disconnect():
    global _bot_process
    with _bot_lock:
        if not _is_running(_bot_process):
            _bot_process = None
            return {"status": "ok", "stopped": False}

        try:
            _bot_process.terminate()
        except Exception:
            logger.exception("Failed to terminate bot process")
            raise HTTPException(status_code=500, detail="Failed to stop bot process")

        return {"status": "ok", "stopped": True}


@app.get("/status")
async def status():
    with _bot_lock:
        return {
            "running": _is_running(_bot_process),
            "pid": _bot_process.pid if _is_running(_bot_process) else None,
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
