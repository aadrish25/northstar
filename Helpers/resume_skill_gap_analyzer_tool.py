from Helpers.extract_resume_text import extract_resume_info_from_pdf
from Helpers.resolve_query import resolve_query
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
import asyncio
import httpx


# define llm
llm = ChatOllama(model="deepseek-v3.1:671b-cloud")


# ============================== RESUME SKILL GAP ANALYSIS SYSTEM PROMPT ==============================
SKILL_GAP_ANALYSIS_PROMPT = ChatPromptTemplate.from_template("""
You are a career advisor specializing in the Indian tech job market for freshers.
Given a candidate's skill profile and a list of job descriptions for a target role, perform a detailed skill gap analysis.
Respond ONLY as valid JSON, no markdown, no backticks, no preamble.

Use exactly this schema:
{{
  "target_role": "role being analyzed",
  "overall_match_score": <integer 0-100>,
  "matched_skills": [
    {{
      "skill": "skill name",
      "frequency": <integer, how many of the 10 JDs mention this skill>
    }}
  ],
  "missing_skills": [
    {{
      "skill": "skill name",
      "priority": "HIGH / MEDIUM / LOW",
      "frequency": <integer>,
      "reason": "one sentence on why this skill matters for the role"
    }}
  ],
  "missing_languages": [
    {{
      "language": "language name",
      "priority": "HIGH / MEDIUM / LOW",
      "frequency": <integer>,
      "reason": "one sentence on why this language matters for the role"
    }}
  ],
  "project_relevance": {{
    "relevant_projects": ["project names that are relevant to this role"],
    "gap": "one sentence on what kind of projects the candidate should build to be more competitive"
  }},
  "certification_recommendations": [
    {{
      "name": "certification name",
      "provider": "issuing body",
      "reason": "one sentence on why this cert adds value for this role"
    }}
  ],
  "experience_gap": "one sentence assessment of candidate experience vs what JDs expect",
  "summary": "3-4 sentence overall assessment: strengths, critical gaps, and the single most impactful next step"
}}

Rules:
- Return ONLY the JSON. No explanation, no markdown, no extra text.
- priority is HIGH if frequency >= 7, MEDIUM if 4-6, LOW if <= 3.
- matched_skills: only skills the candidate HAS that appear in the JDs.
- missing_skills: only skills the candidate LACKS that appear in the JDs.
- Do not invent skills not mentioned in the JDs.
- overall_match_score: based on ratio of matched vs required skills, weighted by frequency.

# Candidate Profile\n:
{candidate_profile}

# Job Descriptions\n:
{job_descriptions}
""")
# =======================================================================================================



ADZUNA_APP_ID = "ad67b046"
ADZUNA_APP_KEY = "df44396e7bc188707a95bb1bdabc970b"
BASE = "https://api.adzuna.com/v1/api/jobs/in"  # 'in' = India

# ============================== Helpers for Resume Skill Gap Analyzer Tool =============================
async def format_job_descriptions(job_item: dict, index: int) -> str:
    def clean_text(value, default: str = "N/A") -> str:
        if value is None:
            return default
        value = str(value).strip()
        return " ".join(value.split()) if value else default

    title = clean_text(job_item.get("title"))
    company = clean_text((job_item.get("company") or {}).get("display_name"))
    location = clean_text((job_item.get("location") or {}).get("display_name"))

    salary_min = job_item.get("salary_min")
    salary_max = job_item.get("salary_max")
    if salary_min is not None and salary_max is not None:
        salary = f"{salary_min:,.0f} - {salary_max:,.0f}"
    else:
        salary = "N/A"

    description = clean_text(job_item.get("description"))

    return (
        f"[JOB {index}]\n"
        f"Title: {title}\n"
        f"Company: {company}\n"
        f"Location: {location}\n"
        f"Salary: {salary}\n"
        f"Description:\n{description}"
    )
    
    
    
async def get_job_jds(role: str, page: int = 1) -> str:
    """Searches jobs in India for a specific role and returns prompt-ready job descriptions."""
    url = f"{BASE}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": role,
        "results_per_page": 10,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("results", [])

        if not data:
            return f"No job descriptions found for role: {role}."

        tasks = [
            format_job_descriptions(job_item=job, index=idx)
            for idx, job in enumerate(data, start=1)
        ]
        formatted_jobs = await asyncio.gather(*tasks)

        prompt_ready_jds = (
            f"Role: {role}\n"
            f"Total jobs: {len(formatted_jobs)}\n\n"
            "Use the following job descriptions as context:\n\n"
            + "\n\n".join(formatted_jobs)
        )

        return prompt_ready_jds

    except Exception as e:
        print(f"[ADZUNA JOB API ERROR]{e}")
        return ""
# ====================================================================================================



# main connector function 
async def align_resume_with_job_descriptions(context:dict) -> dict:
    try:
        # fetch the resume info in structured format using the resume extraction tool
        candidate_profile = await extract_resume_info_from_pdf(pdf_path="sample_resume/sample_resume.pdf")
        
        # fetch the job descriptions for the target role using the Adzuna API and format them in a prompt-ready way
        target_role = resolve_query(
            context,
            "job_roles",
            "skill_gap_analysis_query",
            "refined_query",
            "user_input",
        )
        job_descriptions = await get_job_jds(role=target_role)
        
        if not job_descriptions:
            return {
                "skill_gap_analysis_query": target_role,
                "skill_gap_analysis": None,
                "skill_gap_analysis_items": [],
                "items": [],
                "skill_gap_analysis_error": "Failed to fetch job descriptions for the target role.",
                "type": "skill_gap_analysis",
                "skill_gap_analysis_raw": {
                    "analysis": None,
                    "target_role": target_role,
                    "job_descriptions": job_descriptions,
                },
            }
                                            
        
        skill_gap_analysis_chain = SKILL_GAP_ANALYSIS_PROMPT | llm | JsonOutputParser()
        
        skill_gap_analysis = await skill_gap_analysis_chain.ainvoke({
            "candidate_profile": candidate_profile,
            "job_descriptions": job_descriptions
        })
    
        return  {
                "skill_gap_analysis_query": target_role,
                "skill_gap_analysis": skill_gap_analysis,
                "skill_gap_analysis_items": [skill_gap_analysis],
                "items": [skill_gap_analysis],
                "skill_gap_analysis_error": None,
                "type": "skill_gap_analysis",
                "skill_gap_analysis_raw": {
                    "analysis": skill_gap_analysis,
                    "target_role": target_role,
                    "job_descriptions": job_descriptions,
                    "candidate_profile": candidate_profile,
                },
            }
    except Exception as e:
        return {
            "skill_gap_analysis_query": resolve_query(
                context,
                "job_roles",
                "refined_query",
                "user_input",
            ),
            "skill_gap_analysis": None,
            "skill_gap_analysis_items": [],
            "items": [],
            "skill_gap_analysis_error": f"Skill gap analysis failed: {str(e)}",
            "type": "skill_gap_analysis",
            "skill_gap_analysis_raw": {
                "analysis": None,
                "error": str(e),
            },
        }


align_resume_with_job_descriptions.query_key = "skill_gap_analysis_query"
align_resume_with_job_descriptions.query_aliases = (
    "job_roles",
    "skill_gap_analysis_query",
    "refined_query",
    "user_input",
)
align_resume_with_job_descriptions.result_items_key = "skill_gap_analysis_items"
align_resume_with_job_descriptions.resource_type = "skill_gap_analysis"
