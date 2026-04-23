from dotenv import load_dotenv
import os
import asyncio
import httpx
from Helpers.resolve_query import resolve_query

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY")
YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

def apply_youtube_filters(params: dict, filters: dict):
    if not filters:
        return params

    # Duration mapping
    duration_map = {
        "short": "short",     # < 4 min
        "medium": "medium",   # 4–20 min
        "long": "long"        # > 20 min
    }

    # Sort mapping
    sort_map = {
        "relevance": "relevance",
        "date": "date",
        "views": "viewCount"
    }

    # Apply duration
    if filters.get("duration") in duration_map:
        params["videoDuration"] = duration_map[filters["duration"]]

    # Apply sorting
    if filters.get("sort_by") in sort_map:
        params["order"] = sort_map[filters["sort_by"]]

    # Language (optional)
    if filters.get("language") == "english":
        params["relevanceLanguage"] = "en"

    return params

async def video_response_format(video:dict):
    # print(f"video_item: {video}")
    video_id = video.get("id").get("videoId")
    return {
        "video_id":video_id,
        "type":"video",
        "channel_name":video.get("snippet").get("channelTitle"),
        "video_description":video.get("snippet").get("description"),
        "video_title":video.get("snippet").get("title"),
        "video_url":YOUTUBE_VIDEO_URL.format(video_id=video_id),
    }

# youtube video fetcher tool

async def fetch_youtube_videos(context:dict):
    """Searches the youtube api by a certain keyword, and returns a list of recommended videos"""
    
    url = "https://www.googleapis.com/youtube/v3/search"
    print("context in fetch_youtube_videos",context)

    max_results = context.get("youtube_max_results") or 5
    try:
        max_results = int(max_results)
    except Exception:
        max_results = 5
    max_results = max(1, min(max_results, 50))
    
    query = resolve_query(
        context,
        "refined_query",
        "youtube_query",
        "youtube query",
        "user_input",
    )

    params = {
    "part": "snippet",
    "q": query,
    "type": "video",
    "maxResults": max_results,
    "key": YOUTUBE_API_KEY,
    }

    params = apply_youtube_filters(params, context.get("filters"))

    page_token = context.get("youtube_page_token")
    if page_token:
        params["pageToken"] = page_token

    if not YOUTUBE_API_KEY:
        return {
            "videos": [],
            "items": [],
            "videos_text": "",
            "next_page_token": None,
            "youtube_error": "Missing YOUTUBE_DATA_API_KEY",
            "type": "video",
            "youtube_raw": {
                "videos": [],
                "query": query,
                "params": params,
            }
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
             
        video_list = data.get("items") or []
        next_page_token = data.get("nextPageToken")
        
        tasks = [
            video_response_format(video=video_item)
            for video_item in video_list
        ]
        
        formatted_video_list = await asyncio.gather(*tasks)
        
        lines = []
        for i, v in enumerate(formatted_video_list, start=1):
            lines.append(
                f"{i}. Video Id : {v.get('video_id')}\n"
                f"   Video title: {v.get('video_title')}\n"
                f"   Channel: {v.get('channel_name')}\n"
                f"   URL: {v.get('video_url')}\n"
                f"   About: {(v.get('video_description') or '')[:100]}..."
            )

        return {
            # Structured list for downstream ranker + saving
            "videos": formatted_video_list,
            "items": formatted_video_list,
            # Pretty display string (optional for LLM prompts / debugging)
            "videos_text": "\n\n".join(lines),
            "next_page_token": next_page_token,
            "youtube_error": None,
            "type": "video",
            "youtube_raw": {
                "videos": formatted_video_list,
                "query": query,
                "params": params,
                "response": data,
                "next_page_token": next_page_token,
            }
        }

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text
        print(f"[ERROR IN YOUTUBE_FETCHER] HTTP {status_code}: {error_text}")

        return {
            "videos": [],
            "items": [],
            "videos_text": "",
            "next_page_token": None,
            "youtube_error": f"YouTube API returned HTTP {status_code}",
            "type": "video",
            "youtube_raw": {
                "videos": [],
                "query": query,
                "params": params,
                "error": error_text,
                "status_code": status_code,
            }
        }

    except Exception as e:
        print(f"[ERROR IN YOUTUBE_FETCHER] {e}")
        return {
            "videos": [],
            "videos_text": "",
            "items": [],
            "next_page_token": None,
            "youtube_error": f"YouTube fetch failed: {str(e)}",
            "type": "video",
            "youtube_raw": {
                "videos": [],
                "query": query,
                "params": params,
                "error": str(e),
            }
        }
