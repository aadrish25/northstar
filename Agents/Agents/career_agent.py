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
    ("system", """You are a career intent planner.

Your job:
1. Understand user intent
2. Extract career goals
3. Identify relevant job roles
4. Extract filters
5. Choose correct agents

AGENTS:
- skill_builder_agent → for prioritized skills needed for a target job role
- skill_gap_analyzer_agent → for comparing a user's resume/profile against a target job role and identifying matched skills, missing skills, languages, project gaps, or certification gaps
- roadmap_builder_agent → for a structured learning roadmap, step-by-step progression, or curated roadmap resources for a target role

FILTER RULES:
- level → infer from user (default fresher)

IMPORTANT:
- This is not a job search platform
- Do NOT decide confirmation or saving
- Use skill_builder_agent when the user wants required skills, core competencies, or prioritized capabilities for a target role
- Use skill_gap_analyzer_agent when the user wants resume skill gap analysis, resume-vs-job-description comparison, match analysis for a target role, missing skills from their resume, or wants to know how aligned their profile is with a target role
- Use roadmap_builder_agent when the user wants a roadmap, learning path, step-by-step progression, or guided sequence for becoming a specific role
- If the user clearly asks both what skills are needed for a role and how their current resume compares against that role, return both skill_builder_agent and skill_gap_analyzer_agent
- If the user asks for both a skill gap analysis and a roadmap to close the gaps, return both skill_gap_analyzer_agent and roadmap_builder_agent
- If the user clearly wants both the required skills and the roadmap for the same role, return both agents
- Even if the user mentions jobs or career growth, focus on identifying the target role and whether they need required skills, a resume gap analysis, or a roadmap for that role
- Return STRICT JSON only (no extra text)
- Only return agents from this allowed set: ["skill_builder_agent", "skill_gap_analyzer_agent", "roadmap_builder_agent"]

Return EXACTLY this shape:
{{
  "agents": ["skill_builder_agent"],
  "goals": ["..."],
  "filters": {{
    "level": "fresher|experienced"
  }},
  "job_roles": ["Software Developer", "Machine Learning Engineer", "Data Analyst", "Product Manager"]
}}

Valid examples for "agents":
- ["skill_builder_agent"]
- ["skill_gap_analyzer_agent"]
- ["roadmap_builder_agent"]
- ["skill_builder_agent", "skill_gap_analyzer_agent"]
- ["skill_gap_analyzer_agent", "roadmap_builder_agent"]
- ["skill_builder_agent", "roadmap_builder_agent"]
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


# write the agent class now
class CareerAgent:
    def __init__(self):
        self.chain = chain
        self.tools = []
        
    
    async def run(self,context:dict):
        response = await self.chain.ainvoke({
            "user_input":context.get("user_input"),
            "chat_history":context.get("chat_history"),
        })
        
        parsed = extract_json(response.content)
        
        # safety defaults
        parsed.setdefault("agents", ["skill_builder_agent"])
        parsed.setdefault("goals", [])
        parsed.setdefault("filters", {})
        parsed.setdefault("job_roles", [])
        
        # normalize filters
        filters = parsed.get("filters",{})
        parsed["filters"] = {
            "level":filters.get("level","fresher")
        }
        
        return parsed
