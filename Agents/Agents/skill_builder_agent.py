from pprint import pprint

from dotenv import load_dotenv
from langchain_classic.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from Helpers.adzuna_skill_builder_tools import fetch_skill_tree

load_dotenv()
import os


prompt = PromptTemplate(
    template="""
You are a career skill builder agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- filters: {filters}
- skill_builder_items: {skill_builder_items}

Rules:
- Only use roles and skills from skill_builder_items. Never invent roles, skills, demand scores, job counts, or summaries.
- Each item in skill_builder_items contains a target role and a list of ranked skills based on job-market demand.
- Prefer the role or roles that best match the user's stated goal, experience level, and intent.
- Present skills in priority order, using the provided demand signals to justify the order naturally.
- If skill_builder_items is empty, say so and ask the user to refine the target role.

Response format:
- Recommend 1-3 target roles if relevant.
- For each role: explain why it fits, list the most important skills to focus on first, and mention a few next-step skills after that.
- When useful, mention demand count or job_count as supporting context.
- If the user's request is still broad, end with a short clarifying question.
- If the request is specific enough, give a clean final roadmap-style answer.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "filters", "skill_builder_items"],
)

output_parser = StrOutputParser()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

chain = prompt | llm


class SkillBuilderAgent:
    def __init__(self, goals=None, filters=None):
        self.tools = [fetch_skill_tree]
        self.chain = chain

    async def run(self, context: dict):
        items = context.get("skill_builder_items") or []
        skill_builder_error = context.get("skill_builder_error")

        if skill_builder_error:
            skill_builder_status = "error"
            parsed_response = f"I couldn't build the skill roadmap right now because: {skill_builder_error}"
        else:
            response = await self.chain.ainvoke({
                "user_input": context.get("user_input"),
                "chat_history": context.get("chat_history"),
                "goals": context.get("goals"),
                "filters": context.get("filters"),
                "skill_builder_items": items,
            })
            parsed_response = output_parser.parse(response.content)
            if items:
                skill_builder_status = "ok"
            else:
                skill_builder_status = "empty"

        pprint(f"\n\n[SKILL BUILDER AGENT] Response: {parsed_response}\n\n")
        return {
            "skill_builder_response": parsed_response,
            "skill_builder_status": skill_builder_status,
            "skill_builder_error": skill_builder_error,
            "recommended_skill_trees": items,
            "agent_outputs": {
                "skill_builder_agent": {
                    "status": skill_builder_status,
                    "error": skill_builder_error,
                    "summary": parsed_response,
                    "items": items,
                    "type": "skill_tree",
                }
            }
        }
