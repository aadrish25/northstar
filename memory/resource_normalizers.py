from __future__ import annotations

from typing import Any, Dict, Optional


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def normalize_youtube_video(
    video: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "youtube_video",
) -> Dict[str, Any]:
    """
    Convert a YouTube video dict into a unified "resource" record.

    Required resource schema (stable across all recommenders):
      - id: stable unique id (YouTube: videoId)
      - type: resource type (e.g. youtube_video, article, course)
      - title: display title
      - source: origin system (e.g. youtube, platform, web)
      - state: at minimum {"status": "active"}

    Optional fields are allowed and should be additive (url, channel, scores, provenance, etc.).
    """
    print(f"\n\n[normalize_youtube_video] input video dict: {video}\n")
    video_id = (
        video.get("video_id")
        or video.get("id")
        or video.get("videoId")
        or (video.get("id") or {}).get("videoId")
    )
    title = (
        video.get("video_title")
        or video.get("title")
        or (video.get("snippet") or {}).get("title")
    )
    url = video.get("video_url") or video.get("url")
    channel = video.get("channel_name") or video.get("channel") or video.get("creator")

    if not video_id:
        raise ValueError("normalize_youtube_video: missing video id")
    if not title:
        title = ""

    resource: Dict[str, Any] = {
        "id": str(video_id),
        "type": resource_type,
        "title": str(title),
        "source": "youtube",
        "state": {"status": status},
    }

    # Optional (safe) enrichments
    if url:
        resource["url"] = url
    if channel:
        resource["channel"] = channel

    # Pass through useful extras if present (non-breaking for future consumers)
    if isinstance(video.get("score"), (int, float)):
        resource["scores"] = {"relevance": float(video["score"])}
    if isinstance(video.get("level"), str):
        resource.setdefault("tags", []).append(video["level"])

    return resource

def normalize_book(
    book: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "book",
) -> Dict[str, Any]:
    """
    Convert a book dict into a unified "resource" record.
    """
    book_id = (
        book.get("cover_edition_key")
        or book.get("works_key")
        or book.get("id")
        or book.get("key")
    )
    title = book.get("title") or book.get("book_title")
    authors = book.get("author_name") or book.get("book_author")
    if not book_id:
        raise ValueError("normalize_book: missing book id")
    if not title:
        title = ""

    resource: Dict[str, Any] = {
        "id": str(book_id),
        "type": resource_type,
        "title": str(title),
        "source": "open_library",
        "state": {"status": status},
    }

    # Optional (safe) enrichments
    works_key = book.get("works_key") or book.get("key")
    if works_key:
        resource["url"] = "https://openlibrary.org" + "/works/" + _safe_str(works_key).lstrip("/works/")
    if authors:
        resource["authors"] = authors

    return resource


def normalize_kaggle_dataset(
    dataset: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "dataset",
) -> Dict[str, Any]:
    ref = dataset.get("ref") or dataset.get("id")
    title = dataset.get("title") or dataset.get("name") or ""
    url = dataset.get("url")

    if not ref:
        raise ValueError("normalize_kaggle_dataset: missing dataset ref")

    resource: Dict[str, Any] = {
        "id": _safe_str(ref),
        "type": resource_type,
        "title": _safe_str(title),
        "source": "kaggle",
        "state": {"status": status},
    }

    if url:
        resource["url"] = url

    for k in ("votes", "size", "last_updated", "summary"):
        if k in dataset and dataset.get(k) is not None:
            resource[k] = dataset.get(k)

    return resource


def normalize_kaggle_notebook(
    notebook: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "notebook",
) -> Dict[str, Any]:
    ref = notebook.get("ref") or notebook.get("id")
    title = notebook.get("title") or notebook.get("name") or ""
    url = notebook.get("url")

    if not ref:
        raise ValueError("normalize_kaggle_notebook: missing notebook ref")

    resource: Dict[str, Any] = {
        "id": _safe_str(ref),
        "type": resource_type,
        "title": _safe_str(title),
        "source": "kaggle",
        "state": {"status": status},
    }

    if url:
        resource["url"] = url

    for k in ("author", "votes", "language", "summary"):
        if k in notebook and notebook.get(k) is not None:
            resource[k] = notebook.get(k)

    return resource


def normalize_github_repo(
    repo: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "github_repo",
) -> Dict[str, Any]:
    repo_id = repo.get("full_name") or repo.get("id") or repo.get("url") # no such thing as repo_id
    title = repo.get("name") or repo.get("full_name") or ""
    url = repo.get("url")

    # if not repo_id:
    #     raise ValueError("normalize_github_repo: missing repo id")

    resource: Dict[str, Any] = {
        "id": _safe_str(repo_id),
        "type": resource_type,
        "title": _safe_str(title),
        "source": "github",
        "state": {"status": status},
    }

    if url:
        resource["url"] = url

    # if repo.get("description") is not None:
    #     resource["description"] = repo.get("description")
    if repo.get("owner") is not None:
        resource["owner"] = repo.get("owner")
    # if repo.get("stats") is not None:
    #     resource["stats"] = repo.get("stats")
    if repo.get("tech") is not None:
        resource["tech"] = repo.get("tech")

    return resource



# for skill tree normalization
def normalize_skill_tree(
    item: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "skill_tree",
):
    target_role = item.get("role") or item.get("target_role") or item.get("query") or "unknown role"
    skills = item.get("skills") or item.get("skill_builder_items") or item.get("items") or []
    
    resource : Dict[str, Any] = {
        "id": _safe_str(target_role),
        "type": resource_type,
        "title": f"Skill tree for {target_role}",
        "source": "skill_builder",
        "state": {"status": status},
        "skills": skills,
    }
    
    return resource



# for normalizing the roadmap builder
def normalize_roadmap(
    item: Dict[str, Any],
    *,
    status: str = "active",
    resource_type: str = "roadmap",
):
    skill = item.get("skill") or item.get("roadmap_query") or item.get("query") or "unknown skill"
    title = item.get("title") or f"Roadmap for {skill}"
    description = item.get("description") or ""
    resources = item.get("resources") or item.get("roadmap_items") or item.get("items") or []
    
    resource : Dict[str, Any] = {
        "id": _safe_str(skill), 
        "title": _safe_str(title),
        "description": _safe_str(description),
        "resources": resources,
        "type": resource_type,
        "source": "roadmap_sh",
        "state": {"status": status},
    }
    
    return resource
    
def normalize_resource(
    item: Dict[str, Any],
    *,
    kind: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic dispatcher. Extend this as you add new sources/types (articles, courses, etc.).
    """
    inferred_kind = (kind or item.get("type") or item.get("source") or item.get("resource_type")  or "").strip()
    print(f"\n\n[NORMALIZE_RESOURCE] inferred_kind={inferred_kind!r}\n\n")
    if inferred_kind in {"youtube", "youtube_video", "video"}:
        return normalize_youtube_video(item)
    if inferred_kind in {"book", "books"}:
        return normalize_book(item)
    if inferred_kind in {"dataset", "kaggle_dataset"}:
        return normalize_kaggle_dataset(item)
    if inferred_kind in {"notebook", "kaggle_notebook"}:
        return normalize_kaggle_notebook(item)
    if inferred_kind in {"github_repo", "repo", "repository"}:
        return normalize_github_repo(item)
    if inferred_kind in {"skill_tree", "skill_builder"}:
        return normalize_skill_tree(item)
    if inferred_kind in {"roadmap", "roadmap_sh"}:
        return normalize_roadmap(item)
    raise ValueError(f"normalize_resource: unsupported kind={inferred_kind!r}")

