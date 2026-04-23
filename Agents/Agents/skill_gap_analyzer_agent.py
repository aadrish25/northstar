from pprint import pprint
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from Helpers.resume_skill_gap_analyzer_tool import align_resume_with_job_descriptions

load_dotenv()

import os
from memory.chat_memory import chat_memory


# define llm 
llm = ChatOllama(model="deepseek-v3.1:671b-cloud")


# resume skill gap analysis system prompt
prompt = ChatPromptTemplate(
    template="""
You are a resume skill gap analysis agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- skill_gap_analysis: {skill_gap_analysis}

Rules:
- Only use information present in skill_gap_analysis. Never invent skills, certifications, scores, projects, or requirements.
- If skill_gap_analysis is missing, empty, or failed, say that clearly and ask the user to refine the target role or try again.
- Prioritize the most important gaps first, especially high-priority missing skills and languages.
- Keep the response practical, specific, and easy to act on.

Response format:
- Start with a short overall match summary.
- Then list:
  1. strongest matched skills
  2. most important missing skills
  3. missing programming languages, if any
  4. recommended project focus
  5. recommended certifications, if any
  6. the single best next step
- If the user asks for advice, explain the next step in a concise, career-oriented way.
- If the analysis already looks strong, say where the resume is competitive and what would improve it further.

Tone: conversational, clear, supportive, and concise.
"""
)



# chain
skill_gap_analysis_chain = prompt | llm | StrOutputParser()


class ResumeSkillGapAnalyzerAgent:
    def __init__(self,goals=None, filters=None):
        self.tools = [align_resume_with_job_descriptions]
        self.chain = skill_gap_analysis_chain
        
        
    async def run(self, context:dict):
        items = context.get("skill_gap_analysis_items", [])
        analysis_error = context.get("skill_gap_analysis_error", None)
        
        if analysis_error:
            analysis_error = "error"
            parsed_response = f"I couldn't perform the skill gap analysis right now because: {analysis_error}"
            
        else:
            parsed_response = await self.chain.ainvoke({
                "chat_history": context.get("chat_history", ""),
                "user_input": context.get("user_input", ""),
                "goals": context.get("goals", ""),
                "filters": context.get("filters", ""),
                "skill_gap_analysis": items,
            })
            
            if items:
                skill_gap_analyzer_status = "ok"
            else:
                skill_gap_analyzer_status = "empty"
                
        print(f"\n[RESUME SKILL GAP ANALYZER AGENT] Response: {parsed_response}\n")
        
        return {
            "skill_gap_analyzer_response": parsed_response,
            "skill_gap_analyzer_status": skill_gap_analyzer_status,
            "skill_gap_analysis_error": analysis_error,
            "agent_outputs": {
                "skill_gap_analyzer_agent": {
                    "status": skill_gap_analyzer_status,
                    "error": analysis_error,
                    "summary": parsed_response,
                    "items": items,
                    "type": "skill_gap_analysis",
                }
            }
        }
                
                