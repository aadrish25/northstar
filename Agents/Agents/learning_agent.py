import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter

load_dotenv()


def extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
        raise ValueError(f"Invalid JSON response: {text}")


prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a learning intent planner.

Your job:
1. Understand user intent
2. Extract learning goals
3. Generate a strong YouTube search query
4. Extract filters
5. Choose correct agents

AGENTS:
- youtube_agent → for tutorials, courses, learning videos
- github_agent → for code/resources
- stackoverflow_agent → for debugging/help
- reddit_agent → for opinions/discussions

FILTER RULES:
- level → infer from user (default beginner)
- topic → infer domain
- duration: short | medium | long
- language → default english
- sort_by → default relevance

IMPORTANT:
- Do NOT decide confirmation or saving
- Return STRICT JSON only (no extra text)

Return EXACTLY this shape:
{{
  "agents": ["youtube_agent",
    "github_agent",
    "kaggle_notebooks_agent",
    "kaggle_datasets_agent",
    "open_library_agent"],
  "goals": ["..."],
  "filters": {{
    "level": "beginner|intermediate|advanced",
    "topic": "technology|science|math|programming|other",
    "duration": "short|medium|long",
    "language": "english|other",
    "sort_by": "relevance|date|views"
  }},
  "youtube_query": "..."
  "learning_subjects":["list of subjects eg math, Programing, Machine Learning, etc]
}}
"""),
    ("human", """USER INPUT:
{user_input}

CHAT HISTORY:
{chat_history}
""")
])


llm  = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)


chain = prompt | llm


# -----------------------
# Agent
# -----------------------
class LearningAgent:
    def __init__(self):
        self.chain = chain
        self.tools = []

    async def run(self, context: dict):
        response = await self.chain.ainvoke({
            "user_input": context.get("user_input"),
            "chat_history": context.get("chat_history"),
        })

        parsed = extract_json(response.content)

        # safety defaults
        parsed.setdefault("agents", ["youtube_agent"])
        parsed.setdefault("goals", [])
        parsed.setdefault("filters", {})
        parsed.setdefault("youtube_query", context.get("user_input"))

        # normalize filters
        filters = parsed.get("filters", {})
        parsed["filters"] = {
            "level": filters.get("level", "beginner"),
            "topic": filters.get("topic", "other"),
            "duration": filters.get("duration", "medium"),
            "language": filters.get("language", "english"),
            "sort_by": filters.get("sort_by", "relevance"),
        }

        return parsed