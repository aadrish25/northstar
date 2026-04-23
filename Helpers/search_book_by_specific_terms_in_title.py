import httpx
import asyncio
from Helpers.resolve_query import resolve_query


# helper function to format the book names
async def format_books(book_item):
    return {
        "author_name":book_item.get("author_name"),
        "first_publish_year":book_item.get("first_publish_year"),
        "works_key":book_item.get("key").rsplit('/',1)[-1],
        "subject":book_item.get("subject")[0] if book_item.get("subject") else "NA",
        "title":book_item.get("title"),
    }
    
    
async def search_books_by_specific_terms_in_title(context, limit=10):
    """This tool searches books with specific terms in the book title"""
    url = "https://openlibrary.org/search.json"
    if isinstance(context, dict):
        query = resolve_query(
        context,
        "refined_query",
        "learning_subjects",
        "user_input",
        )
    
        if isinstance(query,list):
            query=" ".join(query)
        print(f"\n[SPECIFIC TERM IN TITLE TOOL] Topic: {query}")
        
        limit = context.get("open_library_title_limit") or limit
    else:
        query = context

    try:
        limit = int(limit)
    except Exception:
        limit = 10
    limit = max(1, min(limit, 50))

    if not query:
        return {
            "book_title_search_query":"None",
            "open_library_title_items": [],
            "items": [],
            "open_library_title_error": "Missing book_title_search_query",
            "type": "books",
            "open_library_title_raw": {
                "books": [],
                "query": query,
            }
        }

    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,first_publish_year,subject,key,isbn"
    }
    
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            data = payload.get("docs") or []
             
        
        # tasks 
        tasks = [
            format_books(book_item=book)
            for book in data
        ]
        
        formatted_books = await asyncio.gather(*tasks)
        
        
        print(f"\n [SPECIFIC TERM IN TITLE TOOL]: {formatted_books}\n")
        
        return {
            "book_title_search_query":query,
            "open_library_title_items": formatted_books,
            "items": formatted_books,
            "open_library_title_error": None,
            "type": "books",
            "open_library_title_raw": {
                "books": formatted_books,
                "query": query,
                "params": params,
                "response": payload,
            }
        }
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        error_text = e.response.text
        print(f"[ERROR IN OPEN LIBRARY TITLE SEARCH] HTTP {status_code}: {error_text}")
        return {
            "book_title_search_query":query,
            "open_library_title_items": [],
            "items": [],
            "open_library_title_error": f"Open Library title search returned HTTP {status_code}",
            "type": "books",
            "open_library_title_raw": {
                "books": [],
                "query": query,
                "params": params,
                "error": error_text,
                "status_code": status_code,
            }
        }
        
    except Exception as e:
        print(f"[ERROR IN OPEN LIBRARY TITLE SEARCH] {e}")
        return {
            "book_title_search_query":query,
            "open_library_title_items": [],
            "items": [],
            "open_library_title_error": f"Open Library title search failed: {str(e)}",
            "type": "books",
            "open_library_title_raw": {
                "books": [],
                "query": query,
                "params": params,
                "error": str(e),
            }
        }
         
         
         
search_books_by_specific_terms_in_title.query_key = "book_title_search_query"
search_books_by_specific_terms_in_title.query_aliases = (
    "refined_query",
    "book_title_search_query",
    "book title search query",
    "user_input",
)
search_books_by_specific_terms_in_title.result_items_key = "open_library_title_items"
search_books_by_specific_terms_in_title.resource_type = "books"
