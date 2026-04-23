import os
import json
from langchain_groq import ChatGroq


from langchain_core.prompts import ChatPromptTemplate


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
    ("system", """You are a feedback control agent for a recommendation system.

Your job:
1. Determine user satisfaction
2. Decide action
3. Improve query if needed

RULES:
- action: reuse | refine | save
- save ONLY if user clearly confirms (e.g. "finalize", "save", "perfect", "go ahead")
- refined_query MUST be non-empty if action=refine
- Return STRICT JSON only (no extra text)

Return EXACTLY this shape:
{{
  "action": "reuse|refine|save",
  "feedback": "positive|negative|neutral",
  "refined_query": "..."
}}
"""),
    ("human", """USER INPUT:
{user_input}

PREVIOUS QUERY:
{previous_query}

GOALS:
{goals}

FILTERS:
{filters}

Chat history:
{chat_history}
""")
])


llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
    )


chain = prompt | llm


# -----------------------
# Agent
# -----------------------
class FeedbackLoopAgent:
    def __init__(self):
        self.chain = chain

    async def run(self, context: dict):
        # safer item preview
        # items_preview = []
        # for item in context.get("items", [])[:5]:
        #     if isinstance(item, dict):
        #         items_preview.append({
        #             "title": item.get("video_title") or item.get("title"),
        #             "source": item.get("channel_name") or item.get("source"),
        #         })
        #     else:
        #         items_preview.append(str(item))

        response = await self.chain.ainvoke({
            "user_input": context.get("user_input"),
            "previous_query": context.get("previous_query") or context.get("query"),
            "goals": context.get("goals"),
            "filters": context.get("filters"),
            "chat_history": context.get("chat_history"),
        })

        try:
            parsed = extract_json(response.content)
        except Exception:
            # fallback safety
            parsed = {
                "action": "reuse",
                "feedback": "neutral",
                "refined_query": ""
            }

        # defaults
        parsed.setdefault("action", "reuse")
        parsed.setdefault("feedback", "neutral")
        parsed.setdefault("refined_query", "")

        # 🔥 safety: enforce refine correctness
        if parsed["action"] == "refine" and not parsed["refined_query"]:
            parsed["action"] = "reuse"

        return parsed