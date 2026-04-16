import json
import os
import urllib.request
import urllib.error
from datetime import datetime

from loguru import logger
from pipecat.frames.frames import EndTaskFrame
from pipecat.processors.frame_processor import FrameDirection

from utils.storage import save_result

_EVALUATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evaluations")
_HIRE_BACKEND_BASE_URL = os.environ.get("HIRE_BACKEND_BASE_URL", "http://127.0.0.1:8000")


def _post_to_hire_backend(endpoint: str, payload: dict) -> None:
    """POST JSON to hire-backend (non-blocking, ignores errors)."""
    url = f"{_HIRE_BACKEND_BASE_URL}{endpoint}"
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            logger.info(f"Posted to hire-backend {endpoint}: {body}")
    except urllib.error.HTTPError as e:
        logger.error(f"Hire-backend POST {endpoint} failed: {e.code} {e.read().decode('utf-8')}")
    except Exception:
        logger.exception(f"Hire-backend POST {endpoint} failed")


async def submit_interview_result(params) -> None:
    """LLM tool handler — saves evaluation to disk + DB, then shuts down the pipeline."""
    args = params.arguments
    candidate = args.get("candidate_name", "unknown")
    role = args.get("role_applied", "unknown")
    score = args.get("overall_score")
    recommendation = args.get("recommendation")
    interview_mode = args.get("interview_mode")

    logger.info(
        f"submit_interview_result | candidate={candidate} role={role} "
        f"score={score} recommendation={recommendation}"
    )

    try:
        os.makedirs(_EVALUATIONS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(_EVALUATIONS_DIR, f"{candidate.replace(' ', '_')}_{timestamp}.json")
        args["evaluated_at"] = datetime.now().isoformat()

        with open(filename, "w") as f:
            json.dump(args, f, indent=2)
        logger.info(f"Evaluation saved → {filename}")

        try:
            db_path = save_result(args, interview_mode=interview_mode)
            logger.info(f"Evaluation stored in DB → {db_path}")
        except Exception:
            logger.exception("Failed to save evaluation to DB")

        try:
            user_id = os.environ.get("INTERVIEW_USER_ID")
            user_email = os.environ.get("INTERVIEW_USER_EMAIL")
            application_id = os.environ.get("INTERVIEW_APPLICATION_ID")
            hire_backend_payload = {
                "user_id": user_id,
                "user_email": user_email,
                "application_id": application_id,
                "interview_mode": interview_mode,
                "payload": args,
            }
            _post_to_hire_backend("/interview-results", hire_backend_payload)
        except Exception:
            logger.exception("Failed to post evaluation to hire-backend")

        await params.result_callback({"success": True, "file": filename})

    except Exception:
        logger.exception("Failed to save evaluation")
        await params.result_callback({"success": False})

    finally:
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
