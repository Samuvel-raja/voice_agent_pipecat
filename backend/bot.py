#
# Copyright (c) 2024-2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat Quickstart Example.

The example runs a simple voice AI bot that you can connect to using your
browser and speak with it. You can also deploy this bot to Pipecat Cloud.

Required AI services:
- Deepgram (Speech-to-Text)
- OpenAI (LLM)
- Cartesia (Text-to-Speech)

Run the bot using::

    uv run bot.py
"""

import os
import json
import threading
from typing import Any

from dotenv import load_dotenv
from loguru import logger


_session_config_lock = threading.Lock()
_session_config: dict[str, Any] = {}


def _set_session_config(candidate_name: str, questions: list[str]) -> None:
    with _session_config_lock:
        _session_config["candidate_name"] = candidate_name
        _session_config["questions"] = questions


def _get_session_config() -> tuple[str, list[str]]:
    with _session_config_lock:
        candidate_name = _session_config.get("candidate_name")
        questions = _session_config.get("questions")

    if isinstance(candidate_name, str) and isinstance(questions, list):
        return candidate_name, [str(q) for q in questions]

    candidate_name_env = os.getenv("CANDIDATE_NAME", "Candidate")
    questions_raw = os.getenv("INTERVIEW_QUESTIONS", "[]")
    try:
        questions_env = json.loads(questions_raw)
        if not isinstance(questions_env, list):
            questions_env = []
    except Exception:
        questions_env = []

    return candidate_name_env, [str(q) for q in questions_env]


def _start_config_server() -> None:
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
        import uvicorn

        app = FastAPI()

        class SessionConfigPayload(BaseModel):
            candidate_name: str
            questions: list[str]

        @app.get("/health")
        async def health():
            return {"ok": True}

        @app.post("/session-config")
        async def set_session_config(payload: SessionConfigPayload):
            _set_session_config(payload.candidate_name, payload.questions)
            return {"ok": True}

        uvicorn.run(app, host="127.0.0.1", port=7861, log_level="warning")
    except Exception as e:
        logger.exception(f"Failed to start config server: {e}")


_config_server_thread = threading.Thread(target=_start_config_server, daemon=True)
_config_server_thread.start()

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds, first run only)\n")

logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")

from pipecat.frames.frames import LLMRunFrame

logger.info("Loading pipeline components...")
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
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.azure.llm import AzureLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
# from pipecat.transports.daily.transport import DailyParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.observers.loggers.llm_log_observer import LLMLogObserver
from tools import submit_interview_result
from prompts import SYSTEM_PROMPT
from pipecat.services.deepgram.tts import DeepgramTTSService
from common import Common

common = Common()




logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)


submit_interview_result_function = FunctionSchema(
    name="submit_interview_result",
    description="Submit the final structured interview result for this candidate.",
    properties={
        "candidate_name": {"type": "string"},
        "role_applied": {"type": "string"},
        "interview_duration_minutes": {"type": "number"},
        "questions_asked": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "candidate_answer_summary": {"type": "string"},
                    "score": {"type": "number"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "warmup",
                            "technical",
                            "behavioral",
                            "problem_solving",
                            "culture_fit",
                        ],
                    },
                },
                "required": [
                    "question",
                    "candidate_answer_summary",
                    "score",
                    "category",
                ],
            },
        },
        "scores": {"type": "object"},
        "overall_score": {"type": "number"},
        "recommendation": {
            "type": "string",
            "enum": ["strong_hire", "hire", "maybe", "no_hire"],
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "areas_of_concern": {"type": "array", "items": {"type": "string"}},
        "hiring_manager_summary": {"type": "string"},
        "next_steps": {"type": "string"},
    },
    required=[
        "candidate_name",
        "role_applied",
        "interview_duration_minutes",
        "questions_asked",
        "scores",
        "overall_score",
        "recommendation",
        "strengths",
        "areas_of_concern",
        "hiring_manager_summary",
        "next_steps",
    ],
)



async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # tts = CartesiaTTSService(
    #     api_key=os.getenv("CARTESIA_API_KEY"),
    #     settings=CartesiaTTSService.Settings(
    #         voice="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    #     ),
    # )

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        settings=DeepgramTTSService.Settings(
            voice="aura-2-andromeda-en",
        ),
    )

    candidate_name, questions = _get_session_config()
    if questions:
        AI_CONTEXT = await common.generate_prompt_with_questions(candidate_name, questions)
    else:
        AI_CONTEXT = await common.generate_prompt({
                "job_title": "Senior Backend Engineer",
                "company": "Finmo",
                "industry": "Fintech / Payments Infrastructure",
                "seniority": "Senior (5–8 years)",
                "duration": "45 minutes",
                "focus_areas": [
                    "Distributed systems",
                    "API design",
                    "Payment processing pipelines",
                    "Observability"
                ],
                "tech_skills": [
                    "Python",
                    "Go",
                    "Kafka",
                    "PostgreSQL",
                    "Redis",
                    "REST/gRPC APIs",
                    "Docker/Kubernetes"
                ],
                "jd_summary": "Finmo is building real-time cross-border payment rails for Southeast Asia. The role owns the design and reliability of core transaction processing microservices, collaborates with product and compliance teams, and leads incident response for production issues.",
                "candidate_name": "Priya Nair",
                "followup_timeline": "within 3–5 business days",
                "custom_guardrails": [
                    "Do not ask about availability or notice period.",
                    "Do not discuss the company's Series B funding or investor details."
                ],
                "resume_flags": [
                    "18-month gap between 2021–2022 listed as 'freelance consulting' with no clients named.",
                    "Promoted twice in 18 months at previous employer — worth probing what drove the fast progression."
                ]
                }
            )

    FINAL_SYSTEM_PROMPT = SYSTEM_PROMPT.format(AI_CONTEXT=AI_CONTEXT)

    # llm = OpenAILLMService(
    #     api_key=os.getenv("OPENAI_API_KEY"),
    #     settings=OpenAILLMService.Settings(
    #         system_instruction=FINAL_SYSTEM_PROMPT,
    #     ),
    # )
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY_GPT_5")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_GPT_5")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_5")
    deployed_version = os.getenv("AZURE_OPENAI_API_VERSION_GPT_5")

    llm = AzureLLMService(
        api_key=azure_api_key,
        endpoint=endpoint,
        settings=AzureLLMService.Settings(
            model=deployment,
            system_instruction=FINAL_SYSTEM_PROMPT,
        ),
    )

    tools = ToolsSchema(standard_tools=[submit_interview_result_function])


    context = LLMContext(
        tools=tools,
    ) 

    llm.register_function(
        "submit_interview_result",
        submit_interview_result,
        cancel_on_interruption=False,  # usually you want this to finish even if user speaks
        timeout_secs=60,
    )
    
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            stt,
            user_aggregator,  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            assistant_aggregator,  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            observers=[LLMLogObserver()],
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        context.add_message(
            {"role": "user", "content": "Say hello and briefly introduce yourself."}
        )
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    transport_params = {
        # "daily": lambda: DailyParams(
        #     audio_in_enabled=True,
        #     audio_out_enabled=True,
        # ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
