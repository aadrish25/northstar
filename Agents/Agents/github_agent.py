from pprint import pprint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.output_parsers import ResponseSchema,StructuredOutputParser
from langchain_classic.chains import LLMChain
import json
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from Helpers.github_repo_fetcher import github_repo_fetcher

load_dotenv()

import os
from memory.chat_memory import chat_memory

GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
headers = {
    "Authorization":f"token {GITHUB_ACCESS_TOKEN}"
}

response_schemas = [
    ResponseSchema(name="repos",description="""
                   List of github repos, each repo must contain
                   - description
                   - full_name
                   - name
                   - owner
                   - stats
                   - url
            """)
]

parser = StructuredOutputParser.from_response_schemas(response_schemas=response_schemas)
format_instructions = parser.get_format_instructions()

output_parser = StrOutputParser()

prompt = PromptTemplate(
    template="""
You are a GitHub repository recommender agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- collected_repos: {collected_repos}

Rules:
- Only use repos from collected_repos. Never invent repos, stats, or URLs.
- If collected_repos is empty, say so and ask the user to refine their request.

Response format:
- Recommend 2–5 relevant repos.
- For each: name, what it's useful for, 1–2 stats (stars, forks, language, issues), link.
- If the user's need is still broad, end with a short clarifying question.
- If specific enough, give a clean final list.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "collected_repos"],
)


# llm = ChatGroq(
#     api_key = os.getenv("GROQ_API_KEY"),
#     model_name="llama-3.3-70b-versatile"
#     )

llm = ChatOllama(model="deepseek-v3.1:671b-cloud")

chain = LLMChain(
    llm=llm,
    prompt=prompt
)


class GithubAgent:
    def __init__(self,goals=None,filters=None):
        self.tools = [github_repo_fetcher]
        self.chain = chain
        
    async def run(self,context:dict):
        response = await self.chain.ainvoke({
            "user_input":context.get("user_input"),
            "chat_history":context.get("chat_history"),
            "collected_repos":context.get("collected_repos") or context.get("github_items"),
            "goals":context.get("goals"),
        })
        
        github_summary = output_parser.parse(response['text'])
        
        items = context.get("github_items") or context.get("collected_repos") or []
        github_error = context.get("github_error")

        if github_error:
            github_status = "error"
        elif items:
            github_status = "ok"
        else:
            github_status = "empty"

        pprint(f"[GITHUB AGENT] Response: {github_summary}\n")
        return {
            "github_status": github_status,
            "github_error": github_error,
            "github_response": github_summary,
            "recommended_repos": items,
            "agent_outputs": {
                "github_agent": {
                    "status": github_status,
                    "error": github_error,
                    "summary": github_summary,
                    "items": items,
                    "type": "github_repo",
                }
            }
        }

