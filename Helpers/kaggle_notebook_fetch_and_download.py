from dotenv import load_dotenv
import os
import asyncio
import httpx
from kaggle.api.kaggle_api_extended import KaggleApi
from Helpers.resolve_query import resolve_query

load_dotenv()


# global-level
api = KaggleApi()
    
    
def score_kernel(kernel):
    return getattr(kernel,"total_votes",0)


def format_kernel(kernel, topic: str):
    return {
        "title": kernel.title,
        "ref": kernel.ref,
        "author": kernel.author,
        "votes": kernel.total_votes,
        "language": getattr(kernel, "language", None),
        "url": f"https://www.kaggle.com/{kernel.ref}",
        "summary": f"{kernel.title} by {kernel.author} with {kernel.total_votes} votes",
        "relevance_hint": f"Good for learning {topic} based on popularity",
    }

    
    
async def fetch_kaggle_notebooks(context:dict,max_results:int=5):
    """
    Fetch and return a clean, structured list of Kaggle notebooks (kernels)
    for a given topic. No downloading.

    Args:
        topic (str): Search topic (e.g., 'regression', 'nlp', 'pandas')
        max_results (int): Number of notebooks to return

    Returns:
        List[Dict]: Ranked notebook metadata for agent reasoning
    """

    topic = resolve_query(
        context,
        "refined_query",
        "learning_subjects",
        "user_input",
    )
    
    if isinstance(topic,list):
        topic=" ".join(topic)
        
    print(f"\n[KAGGLE NOTEBOOKS FETCHER] Topic: {topic}")

    try:
        api.authenticate()
        kernels = api.kernels_list(search=topic)
    except Exception as e:
        return {
            "kaggle_notebooks_query":topic,
            "kaggle_notebooks_items": [],
            "items": [],
            "kaggle_notebooks_error": f"Kaggle notebooks fetch failed: {str(e)}",
            "type": "notebook",
            "kaggle_notebooks_error": f"Kaggle notebooks fetch failed: {str(e)}",
            "kaggle_notebooks_raw": {
                "notebooks": [],
                "query": topic,
                "error": str(e),
            },
        }


    ranked = sorted(kernels, key=score_kernel, reverse=True)
    selected = ranked[:max_results]
    results = [format_kernel(kernel, topic) for kernel in selected]
    
    print(f"\n[KAGGLE NOTEBOOKS FETCHER] Results: {results}")

    return  {
            "kaggle_notebooks_query":topic,
            "kaggle_notebooks_items":results,
            "items": results,
            "kaggle_notebooks_error": None,
            "type":"notebook",
            "kaggle_notebooks_raw":{
                "notebooks":results,
                "query": topic,
            }
        }
    
    
    
fetch_kaggle_notebooks.query_key = "kaggle_notebooks_query"
fetch_kaggle_notebooks.query_aliases = (
    "refined_query",
    "kaggle_notebooks_query",
    "kaggle notebooks query",
    "user_input",
)
fetch_kaggle_notebooks.result_items_key = "kaggle_notebooks_items"
fetch_kaggle_notebooks.resource_type = "notebook"

    

async def download_kaggle_notebook(context:dict,save_dir: str = "kaggle_notebooks"):
    """
    Download a Kaggle notebook (kernel) using its reference.

    Args:
        ref (str): Notebook reference (e.g., 'username/notebook-name')
        save_dir (str): Directory to save the notebook

    Returns:
        Dict: Download status and file info
    """

    # api = KaggleApi()
    api.authenticate()

    os.makedirs(save_dir, exist_ok=True)
    
    ref = context.get("notebook_ref")

    try:
        api.kernels_pull(ref, path=save_dir)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ref": ref
        }

    # Try to locate downloaded file
    files = os.listdir(save_dir)
    notebook_files = [f for f in files if f.endswith(".ipynb")]

    return {
        "success": True,
        "ref": ref,
        "save_dir": save_dir,
        "files": notebook_files,
        "message": f"Notebook {ref} downloaded successfully"
    }
