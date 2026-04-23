import httpx
import json
import re
import asyncio
from pathlib import Path
from urllib.parse import quote
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from pprint import pprint
from Helpers.resolve_query import resolve_query

load_dotenv()

ROADMAP_SLUGS = {}
CACHE_FILE = Path("roadmap_slugs_cache.json")
GITHUB_API = "https://api.github.com/repos/kamranahmedse/developer-roadmap/contents/src/data/roadmaps"
slug_checker_llm = ChatGroq(model="openai/gpt-oss-120b")




# ========================================== HELPER FUNCTIONS ==========================================

# slug generator - generates slugs based on the roadmap names and caches them in memory and on disk
async def generate_slugs() -> dict:
    global ROADMAP_SLUGS
    
    # return from memory if already loaded
    if ROADMAP_SLUGS:
        return ROADMAP_SLUGS
    
    # return from disk cache if exists
    if CACHE_FILE.exists():
        ROADMAP_SLUGS = json.loads(CACHE_FILE.read_text())
        print(f"[cache] loaded {len(ROADMAP_SLUGS)} slugs from disk")
        return ROADMAP_SLUGS
    
    # fetch fresh from GitHub
    print("[fetch] fetching slugs from GitHub...")
    async with httpx.AsyncClient() as client:
        response = await client.get(GITHUB_API)
        data = response.json()
    
    ROADMAP_SLUGS = {
        item["name"]: item["url"]
        for item in data
        if item["type"] == "dir"
    }
    
    # save to disk
    CACHE_FILE.write_text(json.dumps(ROADMAP_SLUGS, indent=2))
    print(f"[cache] saved {len(ROADMAP_SLUGS)} slugs to disk")
    
    return ROADMAP_SLUGS


# fomat skill - extracts title, description, and categorized resources from the raw markdown content of a skill roadmap
def format_skill(skill: dict) -> dict:
    content = skill["content"]
    
    # extract title
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else skill["skill"]
    
    # extract description
    desc_match = re.search(r'^#\s+.+\n+([\s\S]+?)(?=Visit the following|$)', content)
    description = desc_match.group(1).strip() if desc_match else ""
    
    # extract and categorize resources
    resource_pattern = r'-\s+\[@?(\w+)@(.+?)\]\((.+?)\)'  # fixed: handles [@type@Label]
    resources = {"official": [], "article": [], "video": [], "opensource": [], "feed": [], "other": []}
    
    for match in re.finditer(resource_pattern, content):
        rtype, label, url = match.group(1), match.group(2).strip(), match.group(3).strip()
        entry = {"label": label, "url": url}
        if rtype in resources:
            resources[rtype].append(entry)
        else:
            resources["other"].append(entry)
    
    # also catch plain markdown links not using @type@ format
    plain_pattern = r'-\s+\[(?!@)(.+?)\]\((.+?)\)'
    for match in re.finditer(plain_pattern, content):
        label, url = match.group(1).strip(), match.group(2).strip()
        resources["other"].append({"label": label, "url": url})
    
    resources = {k: v for k, v in resources.items() if v}
    
    return {
        "skill": skill["skill"],
        "title": title,
        "description": description[:100],
        "resources": resources
    }
    
    
    
# slug generator - uses an LLM to determine the most relevant roadmap slug for a given skill/job role based on the available slugs in the roadmap repository
async def slug_generator(skill:str):
    prompt = f"""Given the following list of roadmap slugs, determine which one is most relevant for someone looking to build a career in {skill}. 
    Return only the slug name, no explanation.

    Slugs: {list(ROADMAP_SLUGS.keys())}"""

    response = await slug_checker_llm.ainvoke([HumanMessage(content=prompt)])
    
    pprint(f"Selected slug: {response.content.strip()}")
    
    return response.content.strip()

# ========================================================================================================




async def fetch_roadmap(context:dict) -> dict:
    resolved_skill = resolve_query(
        context,
        "roadmap_query",
        "refined_query",
        "job_roles",
        "user_input",
    )

    if isinstance(resolved_skill, list):
        resolved_skill = " ".join(str(item) for item in resolved_skill if item)

    pprint(f"\n\n[FETCH ROADMAP] Resolved skill/job role: {resolved_skill}\n\n")

    if not resolved_skill:
        return {
            "roadmap_query": None,
            "roadmap_items": [],
            "items": [],
            "roadmap_error": "Missing roadmap_query",
            "type": "roadmap",
            "roadmap_raw": {
                "roadmaps": [],
                "query": resolved_skill,
            }
        }

    try:
        await generate_slugs()

        slug = await slug_generator(resolved_skill)
        api_url = f"https://api.github.com/repos/kamranahmedse/developer-roadmap/contents/src/data/roadmaps/{slug}/content"

        pprint(f"\n\n[FETCH ROADMAP] Generated slug: {slug}\n\n")

        async with httpx.AsyncClient() as client:
            resp = await client.get(api_url)
            resp.raise_for_status()
            files = resp.json()

            seen = {}
            for f in files:
                if not f["name"].endswith(".md"):
                    continue
                skill_name = f["name"].split("@")[0]
                if skill_name not in seen or f["size"] > seen[skill_name]["size"]:
                    seen[skill_name] = f

            async def fetch_one(f):
                content = await client.get(f["download_url"])
                content.raise_for_status()
                return {
                    "skill": f["name"].split("@")[0],
                    "content": content.text,
                    "download_url": f["download_url"]
                }

            skills = await asyncio.gather(*[fetch_one(f) for f in seen.values()])

        formatted = [format_skill(s) for s in skills]
        
        print(f"\n\n[FETCH ROADMAP] Response: {formatted}\n\n")

        return {
            "roadmap_query": resolved_skill,
            "roadmap_items": formatted,
            "items": formatted,
            "roadmap_error": None,
            "type": "roadmap",
            "roadmap_raw": {
                "roadmaps": formatted,
                "query": resolved_skill,
                "slug": slug,
            }
        }

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text

        return {
            "roadmap_query": resolved_skill,
            "roadmap_items": [],
            "items": [],
            "roadmap_error": f"Roadmap fetch returned HTTP {status_code}",
            "type": "roadmap",
            "roadmap_raw": {
                "roadmaps": [],
                "query": resolved_skill,
                "error": error_text,
                "status_code": status_code,
            }
        }

    except Exception as e:
        return {
            "roadmap_query": resolved_skill,
            "roadmap_items": [],
            "items": [],
            "roadmap_error": f"Roadmap fetch failed: {str(e)}",
            "type": "roadmap",
            "roadmap_raw": {
                "roadmaps": [],
                "query": resolved_skill,
                "error": str(e),
            }
        }


fetch_roadmap.query_key = "roadmap_query"
fetch_roadmap.query_aliases = (
    "roadmap_query",
    "refined_query",
    "job_roles",
    "user_input",
)
fetch_roadmap.result_items_key = "roadmap_items"
fetch_roadmap.resource_type = "roadmap"
