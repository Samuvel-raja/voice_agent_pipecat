from langchain_openai import OpenAI
import os
from prompts import AI_INTERVIEWER_PROMPT
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
