# tools.py

import json
import os
from datetime import datetime
from loguru import logger

from pipecat.frames.frames import EndTaskFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection


async def submit_interview_result(params):
    arguments = params.arguments

    logger.info("✅ Tool called: submit_interview_result")
    logger.info(f"Candidate: {arguments.get('candidate_name')} | Role: {arguments.get('role_applied')}")
    logger.info(f"Score: {arguments.get('overall_score')} | Recommendation: {arguments.get('recommendation')}")

    try:
        os.makedirs("evaluations", exist_ok=True)

        candidate_name = arguments.get("candidate_name", "unknown").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluations/{candidate_name}_{timestamp}.json"

        arguments["evaluated_at"] = datetime.now().isoformat()

        with open(filename, "w") as f:
            json.dump(arguments, f, indent=2)

        logger.info(f"✅ Evaluation saved → {filename}")

        await params.result_callback({"success": True, "file": filename})

        # Say goodbye before ending
        # await params.llm.push_frame(
        #     TTSSpeakFrame("Thank you for completing the interview. We'll be in touch soon. Goodbye!")
        # )

        # Gracefully shut down the pipeline
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)

    except Exception as e:
        logger.exception(f"❌ Failed to save evaluation: {e}")
        await params.result_callback({"success": False, "error": str(e)})