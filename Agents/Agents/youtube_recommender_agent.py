import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter

load_dotenv()

from memory.chat_memory import chat_memory
from Helpers.video_ranker_agent import run_video_ranker_agent as video_ranker_tool

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube video recommender agent.

You are given some candidate videos and your job is to chat with the user to finalize recommendations.

If the user seems unsatisfied, ask a focused follow-up question (level, duration, subtopic, practical vs theory).
If the user is satisfied, tell them you can save/finalize (but don't claim you saved).
"""),
    ("human", """USER INPUT:
{user_input}

CHAT HISTORY:
{chat_history}

COLLECTED VIDEOS:
{collected_videos}

FILTERS:
{filters}
""")
])
llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
    )

chain = prompt | llm

class YoutubeRecommenderAgent:
    def __init__(self, goals=None, filters=None):
        self.tools = [video_ranker_tool]
        self.chain = chain
    
    async def run(self, context:dict):
        # response = await self.chain.ainvoke({
        #     "user_input": context.get("user_input"),
        #     "chat_history": context.get("chat_history"),
        #     "collected_videos": context.get("youtube_items"),
        #     "filters": context.get("filters")
        # })
        
        # print(f"\n\n[YOUTUBE RECOMMENDER AGENT]")
        
        
        return {
            "agent_outputs": {
                "youtube_recommender_agent": {
                    "status": "ok",
                    "error": None,
                    "summary": f"Here are some youtube videos I found for your query videos :\n\n {context.get('youtube_items', [])}",
                    "items": context.get("youtube_items", []),
                    "type": "video",
                }
            }
    }
 