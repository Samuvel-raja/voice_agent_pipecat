import os
import subprocess
import threading
import json
import urllib.request
import urllib.error
import time
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
BOT_CONFIG_HTTP_BASE = "http://127.0.0.1:7861"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionConfig(BaseModel):
    pass


class QuestionsSessionConfig(BaseModel):
    candidate_name: str
    questions: list[str]


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


def _wait_for_http_ok(url: str, timeout_secs: float = 10.0) -> bool:
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if 200 <= resp.status < 300:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def _push_session_config(candidate_name: str, questions: list[str]) -> None:
    if not _wait_for_http_ok(f"{BOT_CONFIG_HTTP_BASE}/health", timeout_secs=30.0):
        raise HTTPException(status_code=502, detail="Bot config server not ready on port 7861")

    _proxy_json(
        "POST",
        f"{BOT_CONFIG_HTTP_BASE}/session-config",
        {"candidate_name": candidate_name, "questions": questions},
    )


def _start_bot(env_overrides: Optional[dict] = None) -> subprocess.Popen:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.Popen(
        ["uv", "run", "bot.py", "--transport", "webrtc"],
        env=env,
        creationflags=creationflags,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

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

            _bot_process = _start_bot({"PROMPT_MODE": "job"})

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


@app.post("/connect/questions")
async def connect_questions(config: QuestionsSessionConfig):
    try:
        global _bot_process
        with _bot_lock:
            already_running = _is_running(_bot_process)
            if not already_running:
                _bot_process = _start_bot({"PROMPT_MODE": "job"})

        _push_session_config(config.candidate_name, config.questions)

        return {
            "status": "ok",
            "transport": "webrtc",
            "already_running": already_running,
            "pid": _bot_process.pid if _bot_process else None,
            "config": {"webrtc_config": {}},
        }
    except Exception as e:
        logger.exception(f"Error starting bot (questions mode): {e}")
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
