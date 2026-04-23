import asyncio
import httpx
from Helpers.resolve_query import resolve_query
from dotenv import load_dotenv
import os
load_dotenv()

headers = {
    "Authorization": f"token {os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")}"
}


# formatting function for github api response
async def format_repo(item: dict) -> dict:
    """
    Takes a single GitHub repo item and returns a clean, minimal summary.
    """

    return {
        "name": item.get("name"),
        "full_name": item.get("full_name"),
        "description": item.get("description")[50:150] if item.get("description") else None,  # truncate long descriptions
        "url": item.get("html_url"),

        "owner": {
            "username": item.get("owner", {}).get("login"),
            "profile": item.get("owner", {}).get("html_url"),
        },

        "stats": {
            "stars": item.get("stargazers_count"),
            "forks": item.get("forks_count"),
            "open_issues": item.get("open_issues_count"),
        },

        "tech": {
            "language": item.get("language"),
            "topics": item.get("topics", []),
        }
    }
    
    



async def github_repo_fetcher(context: dict):
    """
    Searches GitHub repositories by a keyword and returns a formatted list.
    """

    url = "https://api.github.com/search/repositories"
    
    q = resolve_query(
        context,
        "refined_query",
        "learning_subjects",
        "user_input",
    )
    
    if isinstance(q,list):
        q=" ".join(q)
    
    print(f"\n[GITHUB REPO FETCHER] Got github_query: {q}\n")

    params = {
        "q": q,
        "per_page": 5,
        "sort": "stars",
        "order": "desc"
    }

    try:
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        repo_list = data.get("items", [])

        # parallel formatting
        tasks = [
            format_repo(item)
            for item in repo_list
        ]

        formatted_repos = await asyncio.gather(*tasks)

        print(f"\n[GITHUB REPO FETCHER] Got formatted repos: {formatted_repos}\n")
        
        return {
            "github_query":q,
            "github_items":formatted_repos,
            "items": formatted_repos,
            "github_error": None,
            "type":"github_repo",
            "github_raw":{
                "repos":formatted_repos,
            }
        }

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text

        print(f"[ERROR IN GITHUB_FETCHER] HTTP {status_code}: {error_text}")

        return {
            "github_query":q,
            "github_items": [],
            "items": [],
            "github_error": f"GitHub API returned HTTP {status_code}",
            "type": "github_repo",
            "github_raw": {
                "repos": [],
                "error": error_text,
                "status_code": status_code,
            }
        }

    except Exception as e:
        print(f"[ERROR IN GITHUB_FETCHER] {e}")

        return {
            "github_query":q,
            "github_items": [],
            "items": [],
            "github_error": f"GitHub fetch failed: {str(e)}",
            "type": "github_repo",
            "github_raw": {
                "repos": [],
                "error": str(e),
            }
        }

        

# for decoupling
github_repo_fetcher.query_key = "github_query"
github_repo_fetcher.query_aliases = ("github_query", "github query", "user_input")
github_repo_fetcher.result_items_key = "github_items"
github_repo_fetcher.resource_type = "github_repo"
