import json
import os
import sys
import threading
from typing import Any
import urllib.request
import urllib.error

from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Session config
# ---------------------------------------------------------------------------

_session_config_lock = threading.Lock()
_session_config: dict[str, Any] = {}


def _load_env_session_config() -> None:
    raw = os.getenv("SESSION_CONFIG_JSON")
    if not raw:
        return
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("mode") and payload.get("candidate"):
            _set_full_session_config(payload)
    except Exception:
        pass


def _set_session_config(candidate_name: str, questions: list[str]) -> None:
    with _session_config_lock:
        _session_config["candidate_name"] = candidate_name
        _session_config["questions"] = questions


def _set_full_session_config(payload: dict[str, Any]) -> None:
    with _session_config_lock:
        _session_config.clear()
        _session_config.update(payload)


def _get_session_config() -> tuple[str, list[str]]:
    with _session_config_lock:
        name = _session_config.get("candidate_name")
        questions = _session_config.get("questions")
    if isinstance(name, str) and isinstance(questions, list):
        return name, [str(q) for q in questions]
    return os.getenv("CANDIDATE_NAME", "Candidate"), []


# ---------------------------------------------------------------------------
# Config server
# ---------------------------------------------------------------------------

def _start_config_server() -> None:
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel

        config_app = FastAPI()

        class SessionConfigPayload(BaseModel):
            candidate_name: str | None = None
            questions: list[str] | None = None
            mode: str | None = None
            candidate: dict[str, Any] | None = None
            company: dict[str, Any] | None = None
            metadata: dict[str, Any] | None = None

        class UserMessagePayload(BaseModel):
            text: str

        @config_app.get("/health")
        async def health():
            return {"ok": True}

        @config_app.post("/user-message")
        async def user_message(payload: UserMessagePayload):
            text = (payload.text or "").strip()
            if not text:
                raise HTTPException(status_code=400, detail="text is required")

            with _active_task_lock:
                task = _active_task
                context = _active_context
            if task is None or context is None:
                raise HTTPException(status_code=409, detail="bot pipeline not ready")

            context.add_message({"role": "user", "content": text})
            await task.queue_frames([LLMRunFrame()])
            return {"ok": True}

        @config_app.post("/session-config")
        async def set_session_config(payload: SessionConfigPayload):
            raw = payload.model_dump(exclude_none=True)
            if raw.get("mode") and raw.get("candidate"):
                _set_full_session_config(raw)
            else:
                _set_session_config(payload.candidate_name or "Candidate", payload.questions or [])
            return {"ok": True}

        config_port = int(os.getenv("BOT_CONFIG_PORT", "7861"))
        uvicorn.run(config_app, host="127.0.0.1", port=config_port, log_level="warning")
    except Exception:
        logger.exception("Failed to start config server")


threading.Thread(target=_start_config_server, daemon=True).start()

# ---------------------------------------------------------------------------
# Pipeline imports
# ---------------------------------------------------------------------------

logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer
logger.info("Silero VAD model loaded")

logger.info("Loading pipeline components...")
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import LLMRunFrame
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.azure.llm import AzureLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.base_transport import BaseTransport, TransportParams

from models import InterviewSessionConfig
from prompts import (
    SESSION_START_MESSAGE,
    SUBMIT_INTERVIEW_RESULT_SCHEMA,
    PUBLISH_TEACHING_SNIPPET_SCHEMA,
    TTS_VOICE,
    build_ai_context,
    build_system_prompt,
)
from utils import ContextGenerator, submit_interview_result

logger.info("All components loaded")

_load_env_session_config()
_context_generator = ContextGenerator()

_active_task_lock = threading.Lock()
_active_task: PipelineTask | None = None
_active_context: LLMContext | None = None


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def _submit_tool_handler(params):
    """Inject interview_mode from session config if the LLM omitted it."""
    args = params.arguments
    if isinstance(args, dict) and not args.get("interview_mode"):
        with _session_config_lock:
            mode = _session_config.get("mode")
        if mode:
            args["interview_mode"] = mode
    return await submit_interview_result(params)


def _post_json(url: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


async def _publish_teaching_snippet_handler(params):
    args = params.arguments if isinstance(params.arguments, dict) else {}

    session_id = os.getenv("BOT_SESSION_ID")
    server_base = os.getenv("BOT_SERVER_BASE")
    if not session_id or not server_base:
        await params.result_callback({"ok": False})
        return

    payload = {
        "title": args.get("title"),
        "language": args.get("language"),
        "code": args.get("code"),
        "explanation": args.get("explanation"),
        "step": args.get("step"),
        "kind": args.get("kind"),
    }

    try:
        _post_json(f"{server_base}/teaching/publish?session_id={session_id}", payload)
        await params.result_callback({"ok": True})
    except Exception:
        await params.result_callback({"ok": False})


# ---------------------------------------------------------------------------
# Bot pipeline
# ---------------------------------------------------------------------------

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Building bot pipeline")

    with _session_config_lock:
        raw_cfg = dict(_session_config)

    ai_context: str | None = None
    if raw_cfg.get("mode") and raw_cfg.get("candidate"):
        try:
            cfg = InterviewSessionConfig.model_validate(raw_cfg)
            ai_context = build_ai_context(cfg)
        except Exception:
            logger.exception("Failed to build AI_CONTEXT from session config")

    if not ai_context:
        candidate_name, questions = _get_session_config()
        if questions:
            ai_context = await _context_generator.from_questions(candidate_name, questions)
        else:
            ai_context = await _context_generator.from_job_details({})

    system_prompt = build_system_prompt(raw_cfg.get("mode"), ai_context)

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        settings=DeepgramTTSService.Settings(voice=TTS_VOICE),
    )

    llm = AzureLLMService(
        api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT_5"),
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_GPT_5"),
        settings=AzureLLMService.Settings(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_5"),
            system_instruction=system_prompt,
        ),
    )

    context = LLMContext(
        tools=ToolsSchema(
            standard_tools=[
                SUBMIT_INTERVIEW_RESULT_SCHEMA,
                PUBLISH_TEACHING_SNIPPET_SCHEMA,
            ]
        )
    )

    llm.register_function(
        "submit_interview_result",
        _submit_tool_handler,
        cancel_on_interruption=False,
        timeout_secs=60,
    )

    llm.register_function(
        "publish_teaching_snippet",
        _publish_teaching_snippet_handler,
        cancel_on_interruption=False,
        timeout_secs=10,
    )

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            observers=[LLMLogObserver()],
        ),
    )

    with _active_task_lock:
        global _active_task, _active_context
        _active_task = task
        _active_context = context

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        context.add_message({"role": "user", "content": SESSION_START_MESSAGE})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    await PipelineRunner(handle_sigint=runner_args.handle_sigint).run(task)


async def bot(runner_args: RunnerArguments):
    transport = await create_transport(runner_args, {
        "webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    })
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    bot_port = os.getenv("BOT_PORT")
    if bot_port and "--port" not in sys.argv:
        sys.argv += ["--port", bot_port]

    main()
