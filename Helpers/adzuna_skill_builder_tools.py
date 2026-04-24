import ast
import asyncio
import os
from collections import Counter

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from Helpers.resolve_query import resolve_query

load_dotenv()

gpt_oss_120 = ChatGroq(model="openai/gpt-oss-120b")

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "ad67b046")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "df44396e7bc188707a95bb1bdabc970b")
BASE = "https://api.adzuna.com/v1/api/jobs/in"


def format_job_role(job_item: dict) -> dict:
    return {
        "title": job_item.get("title", "N/A"),
        "company": job_item.get("company", {}).get("display_name", "N/A"),
        "location": job_item.get("location", {}).get("display_name", "N/A"),
        "category": job_item.get("category", {}).get("label", "N/A"),
        "salary_min": job_item.get("salary_min", "Not disclosed"),
        "salary_max": job_item.get("salary_max", "Not disclosed"),
        "posted_on": job_item.get("created", "N/A")[:10],
        "description": job_item.get("description", "N/A"),
    }


async def extract_skills_from_jd(description: str) -> list[str]:
    if not description or description == "N/A":
        return []

    prompt = f"""Extract only technical skills from this job description.
Return a Python list of strings only. No explanation, no markdown, no extra text.

Example output: ["Python", "TensorFlow", "MLOps", "Docker"]

Job Description: {description}"""

    response = await gpt_oss_120.ainvoke([HumanMessage(content=prompt)])

    try:
        parsed = ast.literal_eval(response.content.strip())
        return [skill for skill in parsed if isinstance(skill, str)]
    except Exception:
        return []


async def search_jobs_for_role(role: str, page: int = 1, results_per_page: int = 10) -> list[dict]:
    """Search Adzuna jobs in India for a specific role and return formatted results."""

    url = f"{BASE}/search/{page}"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": role,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json().get("results", [])

    return [format_job_role(job_item) for job_item in data]


def format_skill_tree(role: str, ranked_skills: list[tuple[str, int]], job_count: int) -> dict:
    skills = [{"skill": skill, "demand": demand} for skill, demand in ranked_skills]
    top_skills = [item["skill"] for item in skills[:5]]

    return {
        "role": role,
        "job_count": job_count,
        "skills": skills,
        "summary": f"Top in-demand skills for {role} based on {job_count} job descriptions",
        "relevance_hint": (
            f"Prioritize {', '.join(top_skills)} for {role}"
            if top_skills
            else f"No skill signals found yet for {role}"
        ),
    }


async def build_skill_tree_for_role(role: str, max_skills: int = 20) -> dict:
    jobs = await search_jobs_for_role(role=role)
    descriptions = [
        job.get("description")
        for job in jobs
        if job.get("description") and job.get("description") != "N/A"
    ]

    if not descriptions:
        return format_skill_tree(role=role, ranked_skills=[], job_count=len(jobs))

    skill_extraction_tasks = [
        extract_skills_from_jd(description=description)
        for description in descriptions
    ]
    all_skills = await asyncio.gather(*skill_extraction_tasks)

    flattened_skills = [skill for skills in all_skills for skill in skills]
    skill_counts = Counter(flattened_skills)
    ranked_skills = skill_counts.most_common(max_skills)

    return format_skill_tree(role=role, ranked_skills=ranked_skills, job_count=len(jobs))


async def fetch_skill_tree(context: dict, max_results: int = 20):
    """
    Fetch skill-demand signals for one or more target roles and return them
    in the same context-driven shape used by the other fetcher helpers.
    """

    roles = resolve_query(
        context,
        "job_roles",
        "skill_builder_query",
        "refined_query",
        "user_input",
    )

    if isinstance(roles, str):
        roles = [roles]
    elif not roles:
        roles = []

    # print(f"\n[SKILL BUILDER FETCHER] Roles: {roles}\n")

    try:
        tasks = [
            build_skill_tree_for_role(role=role, max_skills=max_results)
            for role in roles
            if isinstance(role, str) and role.strip()
        ]
        results = await asyncio.gather(*tasks) if tasks else []

        # print(f"\n[SKILL BUILDER FETCHER] Results: {results}\n")

        return {
            "skill_builder_query": roles,
            "skill_builder_items": results,
            "items": results,
            "skill_builder_error": None,
            "type": "skill_tree",
            "skill_builder_raw": {
                "roles": roles,
                "results": results,
            },
        }

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text

        return {
            "skill_builder_query": roles,
            "skill_builder_items": [],
            "items":[],
            "skill_builder_error": f"Adzuna API returned HTTP {status_code}",
            "type": "skill_tree",
            "skill_builder_raw": {
                "roles": roles,
                "results": [],
                "error": error_text,
                "status_code": status_code,
            },
        }

    except Exception as e:
        return {
            "skill_builder_query": roles,
            "skill_builder_items": [],
            "items":[],
            "skill_builder_error": f"Skill builder fetch failed: {str(e)}",
            "type": "skill_tree",
            "skill_builder_raw": {
                "roles": roles,
                "results": [],
                "error": str(e),
            },
        }


async def get_skill_tree(context: dict):
    """Backward-compatible wrapper for the original helper name."""

    return await fetch_skill_tree(context)


fetch_skill_tree.query_key = "skill_builder_query"
fetch_skill_tree.query_aliases = (
    "job_roles",
    "skill_builder_query",
    "refined_query",
    "user_input",
)
fetch_skill_tree.result_items_key = "skill_builder_items"
fetch_skill_tree.resource_type = "skill_tree"
