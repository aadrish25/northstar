import os
import json
from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter
from langchain_ollama import ChatOllama
from memory.chat_memory import chat_memory

load_dotenv()

os.environ["OPENROUTER_API_KEY"] = os.getenv("NS_API_KEY_OR")

# ✅ Prompt (LCEL style)
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a routing agent. Analyze the user query and route it to the correct downstream agent.

Available agents and their responsibilities:

1. learning_planner_agent
   - User wants to learn a topic or technology
   - User asks for study resources (videos, books, courses, repos)
   - User wants a study plan or learning schedule
   - User asks "how do I learn X" or "resources for X"

2. career_planner_agent
   - User wants career guidance or direction
   - User asks about job roles, job market, or salaries
   - User wants a skill tree or roadmap for a specific job role
   - User asks "how to become a X" or "what skills do I need for X job"
   - User wants to know which jobs match their current skills
   - User wants resume skill gap analysis for a target role
   - User wants to compare their resume/profile against a job role or job description
   - User asks what skills are missing from their resume for a target career path

Return STRICT JSON only, no explanation:
{{
    "agent": "<agent_name>"
}}
"""),
    ("human", """USER INPUT:
{user_input}

CHAT HISTORY:
{chat_history}
""")
])

# ✅ LLM

# llm = ChatGroq(
#     api_key = os.getenv("GROQ_API_KEY"),
#     model_name="llama-3.3-70b-versatile"
#     )

llm = ChatOllama(model="deepseek-v3.1:671b-cloud")

# ✅ Runnable chain (NEW way)
chain = prompt | llm


# ✅ Safe JSON parser
def extract_json(text: str):
    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
        raise ValueError(f"Invalid JSON response: {text}")


# ✅ Parent Agent
class ParentAgent:
    def __init__(self):
        self.chain = chain
        self.tools = []

    async def run(self, context: dict):
        response = await self.chain.ainvoke({
            "user_input": context.get("user_input", ""),
            "chat_history": context.get("chat_history", "")
        })

        # 👇 NEW: response is AIMessage, not dict
        content = response.content

        parsed_response = extract_json(content)

        if "agent" not in parsed_response:
            raise ValueError(f"Missing 'agent' in response: {parsed_response}")

        return parsed_response
