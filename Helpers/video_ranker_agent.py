import json
import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter
from Helpers.youtube_rank_and_fetch import fetch_youtube_videos
load_dotenv()
from memory.chat_memory import chat_memory
from langchain_groq import ChatGroq

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
    ("system", """You are a strict evaluator.

Evaluate each provided video for the user's goal and preferences.

Return STRICT JSON only (no extra text) using EXACTLY this shape:
{{
  "videos": [
    {{
      "id": "string",
      "score": 0.0,
      "level": "beginner|intermediate|advanced",
      "keep": true,
      "reason": "max 10 words"
    }}
  ]
}}

Rules:
- Do NOT skip any video
- id MUST match the input video_id
"""),
    ("human", """USER GOAL:
{goal}

USER PREFERENCES:
{preferences}

VIDEOS:
{videos}
""")
])

llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
    )

chain = prompt | llm

async def run_video_ranker_agent(context:dict):
    videos = await fetch_youtube_videos(context)
    video_list = videos.get("videos") or []
    videos_text = videos.get("videos_text") or ""
    next_page_token = videos.get("next_page_token")
    response = await chain.ainvoke({
        "goal": context.get("goal"),
        "preferences": context.get("preferences"),
        "videos": videos_text or json.dumps(video_list, indent=2),
    })
    parsed_response = extract_json(response.content)

    evaluations = parsed_response.get("videos") or []
    by_id = {v.get("video_id"): v for v in video_list if isinstance(v, dict)}

    ranked_videos = []
    for ev in evaluations:
        if not isinstance(ev, dict):
            continue
        vid = ev.get("id")
        base = by_id.get(vid, {"video_id": vid})
        merged = {**base, **ev}
        ranked_videos.append(merged)

    recommended_videos = [v for v in ranked_videos if v.get("keep") is True]

    return {
    "items": recommended_videos,   # ✅ unified
    "youtube_items":recommended_videos,
    "type": "video",
    "raw": {
        "videos": video_list,
        "ranked_videos": ranked_videos,
        "next_page_token": next_page_token,
    }
}
