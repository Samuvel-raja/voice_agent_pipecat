import os
import subprocess
import threading
import json
import uuid
import urllib.request
import urllib.error
import socket
import time
import queue
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from loguru import logger
from starlette.responses import StreamingResponse

from models import InterviewSessionConfig

app = FastAPI()

SERVER_PORT = 7870

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Session registry — one entry per active bot process
# ---------------------------------------------------------------------------

class _BotSession:
    def __init__(self, session_id: str, process: subprocess.Popen, bot_port: int, config_port: int, mode: str):
        self.session_id = session_id
        self.process = process
        self.bot_port = bot_port
        self.config_port = config_port
        self.mode = mode

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def http_base(self) -> str:
        return f"http://127.0.0.1:{self.bot_port}"

    def config_base(self) -> str:
        return f"http://127.0.0.1:{self.config_port}"


_sessions: dict[str, _BotSession] = {}
_sessions_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Port utilities
# ---------------------------------------------------------------------------

def _find_free_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}–{end}")


def _find_two_free_ports() -> tuple[int, int]:
    """Return (bot_port, config_port) — guaranteed distinct and free."""
    bot_port = _find_free_port(7900, 7960)
    config_port = _find_free_port(7961, 7999)
    return bot_port, config_port


def _wait_for_tcp(host: str, port: int, timeout_secs: float = 30.0) -> bool:
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# HTTP proxy helper
# ---------------------------------------------------------------------------

def _proxy_json(method: str, url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=method,
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


# ---------------------------------------------------------------------------
# Bot lifecycle
# ---------------------------------------------------------------------------

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


def _launch_session(session_payload: dict, mode: str) -> _BotSession:
    """Start a new bot process on fresh ports and register a session."""
    session_id = str(uuid.uuid4())
    bot_port, config_port = _find_two_free_ports()
    logger.info(f"[{session_id}] Starting bot — bot_port={bot_port} config_port={config_port} mode={mode}")

    process = _start_bot({
        "PROMPT_MODE": "job",
        "SESSION_CONFIG_JSON": json.dumps(session_payload, ensure_ascii=False),
        "BOT_PORT": str(bot_port),
        "BOT_CONFIG_PORT": str(config_port),
        "BOT_SESSION_ID": session_id,
        "BOT_SERVER_BASE": f"http://127.0.0.1:{SERVER_PORT}",
        "INTERVIEW_USER_ID": session_payload.get("candidate", {}).get("id"),
        "INTERVIEW_USER_EMAIL": session_payload.get("candidate", {}).get("email"),
        "INTERVIEW_APPLICATION_ID": session_payload.get("application_id"),
    })

    session = _BotSession(session_id, process, bot_port, config_port, mode)
    with _sessions_lock:
        _sessions[session_id] = session

    return session


def _stop_session(session_id: str) -> bool:
    with _sessions_lock:
        session = _sessions.pop(session_id, None)
    if session is None:
        return False
    try:
        if session.is_running():
            session.process.terminate()
            try:
                session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()
                session.process.wait(timeout=3)
    except Exception:
        logger.exception(f"[{session_id}] Failed to terminate bot process")
    logger.info(f"[{session_id}] Session stopped")
    return True


# ---------------------------------------------------------------------------
# Teaching events — per-session SSE stream
# ---------------------------------------------------------------------------

_teaching_subscribers: dict[str, list[queue.Queue]] = {}
_teaching_lock = threading.Lock()


def _publish_teaching_event(session_id: str, payload: dict) -> None:
    with _teaching_lock:
        subs = list(_teaching_subscribers.get(session_id, []))
    for q in subs:
        try:
            q.put_nowait(payload)
        except Exception:
            pass


class TeachingPublishPayload(BaseModel):
    title: str | None = None
    language: str | None = None
    code: str
    explanation: str | None = None
    step: float | None = None
    kind: str | None = None


@app.post("/teaching/publish")
async def teaching_publish(payload: TeachingPublishPayload, session_id: str = Query(...)):
    _get_session(session_id)
    event = payload.model_dump(exclude_none=True)
    event["type"] = "teaching_snippet"
    event["ts"] = time.time()
    _publish_teaching_event(session_id, event)
    return {"ok": True}


@app.get("/teaching/stream")
async def teaching_stream(session_id: str = Query(...)):
    _get_session(session_id)

    q: queue.Queue = queue.Queue(maxsize=200)
    with _teaching_lock:
        _teaching_subscribers.setdefault(session_id, []).append(q)

    def _iter_sse():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event = q.get(timeout=15)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            with _teaching_lock:
                subs = _teaching_subscribers.get(session_id, [])
                try:
                    subs.remove(q)
                except ValueError:
                    pass
                if not subs:
                    _teaching_subscribers.pop(session_id, None)

    return StreamingResponse(_iter_sse(), media_type="text/event-stream")


def _get_session(session_id: str) -> _BotSession:
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if not session.is_running():
        with _sessions_lock:
            _sessions.pop(session_id, None)
        raise HTTPException(status_code=410, detail=f"Session '{session_id}' has ended")
    return session


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QuestionsSessionConfig(BaseModel):
    candidate_name: str | None = None
    questions: list[str] | None = None
    mode: str | None = None
    candidate: dict | None = None
    company: dict | None = None
    metadata: dict | None = None


class SessionMessagePayload(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# WebRTC proxy routes — require session_id query param
# ---------------------------------------------------------------------------

@app.post("/webrtc/offer")
async def webrtc_offer(request: Request, session_id: str = Query(...)):
    session = _get_session(session_id)
    payload = await request.json()
    return _proxy_json("POST", f"{session.http_base()}/api/offer", payload)


@app.post("/api/offer")
async def api_offer(request: Request, session_id: str = Query(...)):
    session = _get_session(session_id)
    payload = await request.json()
    return _proxy_json("POST", f"{session.http_base()}/api/offer", payload)


@app.patch("/webrtc/offer")
async def webrtc_ice_candidate(request: Request, session_id: str = Query(...)):
    session = _get_session(session_id)
    payload = await request.json()
    return _proxy_json("PATCH", f"{session.http_base()}/api/offer", payload)


@app.patch("/api/offer")
async def api_ice_candidate(request: Request, session_id: str = Query(...)):
    session = _get_session(session_id)
    payload = await request.json()
    return _proxy_json("PATCH", f"{session.http_base()}/api/offer", payload)


# ---------------------------------------------------------------------------
# Session management routes
# ---------------------------------------------------------------------------

@app.post("/connect/session")
async def connect_session(config: InterviewSessionConfig):
    try:
        session_payload = config.model_dump()
        session = _launch_session(session_payload, str(config.mode))

        if not _wait_for_tcp("127.0.0.1", session.bot_port, timeout_secs=30.0):
            _stop_session(session.session_id)
            raise HTTPException(status_code=502, detail="Bot server did not start in time")

        return {
            "status": "ok",
            "session_id": session.session_id,
            "mode": config.mode,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error starting bot (session mode): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disconnect")
async def disconnect(session_id: str = Query(...)):
    stopped = _stop_session(session_id)
    return {"status": "ok", "stopped": stopped}


@app.post("/session/message")
async def session_message(payload: SessionMessagePayload, session_id: str = Query(...)):
    session = _get_session(session_id)
    body = {"text": payload.text}
    return _proxy_json("POST", f"{session.config_base()}/user-message", body)


@app.get("/status")
async def status(session_id: str = Query(None)):
    if session_id:
        with _sessions_lock:
            session = _sessions.get(session_id)
        if not session:
            return {"session_id": session_id, "running": False}
        return {"session_id": session_id, "running": session.is_running(), "mode": session.mode}

    with _sessions_lock:
        return {
            "active_sessions": [
                {"session_id": s.session_id, "mode": s.mode, "running": s.is_running()}
                for s in _sessions.values()
            ]
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)
