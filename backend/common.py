# from langchain_openai import OpenAI
from langchain_openai import AzureChatOpenAI
import os
import json
from prompts import AI_INTERVIEWER_PROMPT, AI_INTERVIEWR_WITH_QUESTIONS
from dotenv import load_dotenv
import logging

load_dotenv(override=True)

class Common:
    def __init__(self):
        # api_key = os.getenv("OPENAI_API_KEY")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY_GPT_5")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_GPT_5")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT_5")
        deployed_version = os.getenv("AZURE_OPENAI_API_VERSION_GPT_5")
        
        print("azure_api_key", azure_api_key)
        print("endpoint", endpoint)
        print("deployment", deployment)
        print("deployed_version", deployed_version)
        self.llm = AzureChatOpenAI(
            api_key=azure_api_key,
            azure_endpoint=endpoint,
            deployment_name=deployment,
            api_version=deployed_version,
        )
    
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
