from pprint import pprint

from dotenv import load_dotenv
from langchain_classic.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from Helpers.roadmap_sh_builder import fetch_roadmap

load_dotenv()
import os

prompt = PromptTemplate(
    template="""
You are a career roadmap builder agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- filters: {filters}
- roadmap_items: {roadmap_items}

Rules:
- Only use roadmap titles, descriptions, skills, and resources from roadmap_items. Never invent roadmap steps, links, topics, or summaries.
- Each item in roadmap_items represents part of a learning or career roadmap, including a title, description, and categorized resources.
- Prefer the roadmap items that best match the user's stated goal, experience level, and intent.
- Organize the answer like a practical roadmap, starting with fundamentals and moving toward more advanced areas when that progression is supported by roadmap_items.
- Use the provided resources naturally to support the roadmap, and include direct resource URLs for recommended items.
- Every resource mention must include its clickable URL when available in roadmap_items.
- If roadmap_items is empty, say so and ask the user to refine the target role or roadmap topic.

Response format:
- Recommend a clear roadmap for the target role or topic.
- Start with a short explanation of why this roadmap fits the user's goal.
- Then present the roadmap in a sensible order, highlighting the most important areas to focus on first and what to learn next.
- Include a short "Recommended resources" section with 3-8 items and each item must include title + URL from roadmap_items.
- If the user's request is still broad, end with a short clarifying question.
- If the request is specific enough, give a clean final roadmap-style answer.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "filters", "roadmap_items"],
)

output_parser = StrOutputParser()

# llm = ChatGroq(
#     api_key=os.getenv("GROQ_API_KEY"),
#     model_name="llama-3.3-70b-versatile"
# )

llm = ChatOllama(model="deepseek-v3.1:671b-cloud")

chain = prompt | llm


class RoadmapBuilderAgent:
    def __init__(self,goals=None, filters=None):
        self.tools = [fetch_roadmap]
        self.chain = chain
        
        
    async def run(self, context:dict):
        items = context.get("roadmap_items", [])
        roadmap_error = context.get("roadmap_error", None)
        
        if roadmap_error:
            roadmap_status = "error"
            parsed_response = f"I couldn't build the roadmap right now because: {roadmap_error}"
        else:
            response = await self.chain.ainvoke({
                "chat_history": context.get("chat_history", ""),
                "user_input": context.get("user_input", ""),
                "goals": context.get("goals", ""),
                "filters": context.get("filters", ""),
                "roadmap_items": items
            })
            
            parsed_response = output_parser.parse(response.content)
            
            if items:
                roadmap_status = "ok"
            else:
                roadmap_status = "empty"
                
                
        pprint(f"\n\n[ROADMAP BUILDER AGENT] Response: {parsed_response}\n\n")
        return {
            "roadmap_response": parsed_response,
            "roadmap_status": roadmap_status,
            "roadmap_error": roadmap_error,
            "recommended_roadmaps": items,
            "agent_outputs": {
                "roadmap_builder_agent": {
                    "status": roadmap_status,
                    "error": roadmap_error,
                    "summary": parsed_response,
                    "items": items,
                    "type": "roadmap",
                }
            }
        }
