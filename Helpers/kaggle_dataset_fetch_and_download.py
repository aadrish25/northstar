from dotenv import load_dotenv
import os
import asyncio
import httpx
from kaggle.api.kaggle_api_extended import KaggleApi
from Helpers.resolve_query import resolve_query

load_dotenv()


# global-level
api = KaggleApi()

    
def score_dataset(dataset):
    return getattr(dataset,"total_votes",0)


def format_dataset(d, topic: str):
    return {
        "title": d.title,
            "ref": d.ref,  # important for downloader
            "votes": getattr(d, "total_votes", 0),
            "size": getattr(d, "size", None),
            "last_updated": getattr(d, "lastUpdated", None),
            "url": f"https://www.kaggle.com/datasets/{d.ref}",

            # agent-friendly fields
            "summary": f"{d.title} with {getattr(d, 'total_votes', 0)} votes",
            "relevance_hint": f"Useful dataset for learning {topic}"
    }

    
    
async def fetch_kaggle_datasets(context:dict, max_results: int = 5):
    """
    Fetch and return a ranked list of Kaggle datasets for a given topic.

    Args:
        topic (str): Search topic (e.g., 'housing', 'nlp', 'image classification')
        max_results (int): Number of datasets to return

    Returns:
        List[Dict]: Structured dataset metadata
    """

    topic = resolve_query(
        context,
        "refined_query",
        "learning_subjects",
        "user_input",
    )
    
    if isinstance(topic,list):
        topic=" ".join(topic)
        
    print(f"\n[KAGGLE DATASET FETCHER] Topic: {topic}")

    try:
        api.authenticate()
        datasets = api.dataset_list(search=topic)
    except Exception as e:
        return {
            "kaggle_datasets_query":topic,
            "kaggle_dataset_items": [],
            "items": [],
            "kaggle_datasets_error": f"Kaggle datasets fetch failed: {str(e)}",
            "type": "dataset",
            "kaggle_datasets_error": f"Kaggle datasets fetch failed: {str(e)}",
            "kaggle_datasets_raw": {
                "datasets": [],
                "query": topic,
                "error": str(e),
            },
        }


    ranked = sorted(datasets, key=score_dataset, reverse=True)
    selected = ranked[:max_results]
    results = [format_dataset(d, topic) for d in selected]
    
    print(f"\n[KAGGLE DATASET FETCHER] Results: {results}")

    return  {
            "kaggle_datasets_query":topic,
            "kaggle_dataset_items":results,
            "items": results,
            "kaggle_datasets_error": None,
            "type":"dataset",
            "kaggle_datasets_raw":{
                "datasets":results,
                "query": topic,
            }
        }
    
    
    
fetch_kaggle_datasets.query_key = "kaggle_datasets_query"
fetch_kaggle_datasets.query_aliases = (
    "refined_query",
    "kaggle_datasets_query",
    "kaggle datasets query",
    "user_input",
)
fetch_kaggle_datasets.result_items_key = "kaggle_dataset_items"
fetch_kaggle_datasets.resource_type = "dataset"

    

async def download_kaggle_dataset(context:dict, base_dir: str = "kaggle_datasets"):
    """
    Download a Kaggle dataset using its reference.

    Args:
        ref (str): Dataset reference (e.g., 'zynicide/wine-reviews')
        base_dir (str): Base directory to store datasets

    Returns:
        Dict: Download status and file info
    """

    # api = KaggleApi()
    api.authenticate()

    ref = context.get("ref")
    # create isolated folder per dataset
    safe_ref = ref.replace("/", "_")
    dataset_dir = os.path.join(base_dir, safe_ref)
    os.makedirs(dataset_dir, exist_ok=True)

    try:
        api.dataset_download_files(ref, path=dataset_dir, unzip=True)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ref": ref
        }

    files = os.listdir(dataset_dir)

    return {
        "success": True,
        "ref": ref,
        "path": dataset_dir,
        "files": files,
        "message": "Dataset downloaded and extracted successfully"
    }
