import httpx
import asyncio
from urllib.parse import quote
from Helpers.resolve_query import resolve_query

# helper fn to filter academic books only
ACADEMIC_SUBJECTS = {
    "textbook", "textbooks", "study guides", "study and teaching",
    "problems and exercises", "examinations", "handbooks, manuals",
    "lecture notes", "academic", "education", "curriculum",
    "learning", "teaching", "research", "science", "mathematics",
    "engineering", "medicine", "history", "philosophy", "economics",
    "computer science", "physics", "chemistry", "biology"
}

NON_ACADEMIC_SUBJECTS = {
    "fiction", "science fiction", "thriller", "novel", "romance",
    "mystery", "horror", "fantasy", "suspense fiction", "novela",
    "short stories", "poetry", "drama"
}

def is_academic(book: dict) -> bool:
    subjects = {s.lower() for s in book.get("subject", [])}
    
    # hard exclude if clearly fiction
    if subjects & NON_ACADEMIC_SUBJECTS:
        return False
    
    # include if matches academic signals
    if subjects & ACADEMIC_SUBJECTS:
        return True
    
    return False

async def format_academic_books(book_item):
    if not book_item:
        return
    
    author_list = book_item.get("authors") or []
    author_names = [a.get("name") for a in author_list if isinstance(a, dict)]
    subjects = (book_item.get("subject") or [])[:10]
    book_title = book_item.get("title")
    book_key = (book_item.get("key") or "").rsplit('/',1)[-1]
    cover_edition_key = book_item.get("cover_edition_key")
    
    return {
        "author_names":author_names,
        "subject_covered":subjects,
        "book_title":book_title,
        "works_key":book_key,
        "cover_edition_key":cover_edition_key
    }
    
    
async def get_books_for_a_specific_subject(context,limit:int=10):
    """Get the books for a specific subject"""
    if isinstance(context, dict):
        subject = resolve_query(
        context,
        "refined_query",
        "learning_subjects",
        "user_input",
        )
    
        if isinstance(subject,list):
            subject=" ".join(subject)
        # print(f"\n[SPECIFIC SUBJECT BOOK SEARCH TOOL] Topic: {subject}")
        
        limit = context.get("open_library_subject_limit") or limit
    else:
        subject = context

    try:
        limit = int(limit)
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    if not subject:
        return {
            "academic_books_search_query":"None",
            "open_library_subject_items": [],
            "items": [],
            "open_library_subject_error": "Missing academic_books_search_query",
            "type": "books",
            "open_library_subject_raw": {
                "books": [],
                "subject": subject,
            }
        }
    
    normalized_subject = quote(subject.lower().replace(" ", "_"))
    url = f"https://openlibrary.org/subjects/{normalized_subject}.json"
    params = {"limit": limit}
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("works") or []
             
        # filter only academic books
        academic_books = [
            book
            for book in data
            if is_academic(book=book)
        ]
        
        # formatting task
        task = [
            format_academic_books(book_item=book)
            for book in academic_books
        ]
        
        formatted_academic_books = await asyncio.gather(*task)
        
        # print(f"\n [SPECIFIC SUBJECT BOOK SEARCH TOOL]: {formatted_academic_books}\n")
        
        return {
            "academic_books_search_query":subject,
            "open_library_subject_items": formatted_academic_books,
            "items": formatted_academic_books,
            "open_library_subject_error": None,
            "type": "books",
            "open_library_subject_raw": {
                "books": formatted_academic_books,
                "subject": subject,
                "normalized_subject": normalized_subject,
                "params": params,
                "response": payload,
            }
        }
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text
        # print(f"[ERROR IN OPEN LIBRARY SUBJECT SEARCH] HTTP {status_code}: {error_text}")
        return {
            "academic_books_search_query":subject,
            "open_library_subject_items": [],
            "items": [],
            "open_library_subject_error": f"Open Library subject search returned HTTP {status_code}",
            "type": "books",
            "open_library_subject_raw": {
                "books": [],
                "subject": subject,
                "normalized_subject": normalized_subject,
                "params": params,
                "error": error_text,
                "status_code": status_code,
            }
        }
        
    except Exception as e:
        # print(f"[ERROR IN OPEN LIBRARY SUBJECT SEARCH] {e}")
        return {
            "academic_books_search_query":subject,
            "open_library_subject_items": [],
            "items": [],
            "open_library_subject_error": f"Open Library subject search failed: {str(e)}",
            "type": "books",
            "open_library_subject_raw": {
                "books": [],
                "subject": subject,
                "normalized_subject": normalized_subject,
                "params": params,
                "error": str(e),
            }
        }
         
         
get_books_for_a_specific_subject.query_key = "academic_books_search_query"
get_books_for_a_specific_subject.query_aliases = (
    "refined_query",
    "academic_books_search_query",
    "academic books search query",
    "user_input",
)
get_books_for_a_specific_subject.result_items_key = "open_library_subject_items"
get_books_for_a_specific_subject.resource_type = "books"
