"""
Generates AI_CONTEXT strings via Azure LLM when no structured session config is available.
Used as a fallback in bot.py when only candidate_name + questions are provided.
"""

import json
import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from loguru import logger

from prompts import AI_INTERVIEWER_PROMPT, AI_INTERVIEWER_WITH_QUESTIONS

load_dotenv(override=True)

_FALLBACK_CONTEXT = (
    "You are ARIA, an AI interviewer. Ask concise, job-relevant questions one at a time "
    "and evaluate the candidate professionally."
)


class ContextGenerator:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY_GPT_5"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_GPT_5"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_5"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_GPT_5"),
        )

    async def from_job_details(self, job_details: dict) -> str:
        """Generate AI_CONTEXT from job/company metadata."""
        try:
            response = await self.llm.ainvoke(AI_INTERVIEWER_PROMPT.format(**job_details))
            return getattr(response, "content", str(response))
        except Exception:
            logger.exception("Failed to generate context from job details — using fallback")
            return _FALLBACK_CONTEXT

    async def from_questions(self, candidate_name: str, questions: list[str]) -> str:
        """Generate AI_CONTEXT from an explicit question list."""
        try:
            prompt = AI_INTERVIEWER_WITH_QUESTIONS.format(
                candidate_name=candidate_name,
                questions=json.dumps(questions, ensure_ascii=False),
            )
            response = await self.llm.ainvoke(prompt)
            return getattr(response, "content", str(response))
        except Exception:
            logger.exception("Failed to generate context from questions — using fallback")
            return _FALLBACK_CONTEXT
