from langchain_openai import OpenAI
import os
import json
from prompts import AI_INTERVIEWER_PROMPT, AI_INTERVIEWR_WITH_QUESTIONS
from dotenv import load_dotenv
import logging

load_dotenv(override=True)

class Common:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = OpenAI(api_key=api_key)
    
    async def generate_prompt(self, job_details):
        job_data = AI_INTERVIEWER_PROMPT.format(**job_details)
        response = await self.llm.ainvoke(job_data)
        print("REs", response)
        return response

    async def generate_prompt_with_questions(self, candidate_name: str, questions: list[str]):
        prompt = AI_INTERVIEWR_WITH_QUESTIONS.format(
            candidate_name=candidate_name,
            questions=json.dumps(questions, ensure_ascii=False),
        )
        response = await self.llm.ainvoke(prompt)
        print("REs", response)
        return response
