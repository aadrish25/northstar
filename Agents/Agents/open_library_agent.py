from pprint import pprint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.output_parsers import ResponseSchema,StructuredOutputParser
from langchain_classic.chains import LLMChain
import json
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from Helpers.search_book_by_specific_terms_in_title import search_books_by_specific_terms_in_title
from Helpers.get_books_for_a_specific_subject import get_books_for_a_specific_subject

load_dotenv()

from memory.chat_memory import chat_memory
import os

output_parser = StrOutputParser()

prompt = PromptTemplate(
    template="""
You are an Open Library book recommender agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- filters: {filters}
- title_match_books: {title_match_books}
- subject_books: {subject_books}

Rules:
- Only use books from `title_match_books` and `subject_books`. Never invent titles, authors, subjects, work keys, years, or links.
- `title_match_books` contains books whose titles match a specific search term.
- `subject_books` contains books fetched from a particular subject area, usually better for broader topic-based discovery.
- Prefer `title_match_books` when the user asks for a specific named book, exact title phrase, or a narrowly targeted book topic.
- Prefer `subject_books` when the user is exploring a domain, learning a subject, or wants broader academic recommendations.
- If both inputs have useful books, combine them thoughtfully and explain why the strongest picks fit the user's goal.
- If both `title_match_books` and `subject_books` are empty, say so and ask the user to refine their request.

Response format:
- Recommend 2-5 relevant books.
- For each: title, why it fits the user's goal, 1-2 useful details (author, subject, first publish year), and the Open Library work key if available.
- If helpful, mention whether the recommendation came from the title search or the subject search.
- If the user's request is still broad, end with a short clarifying question.
- If the request is specific enough, give a clean final list.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "filters", "title_match_books", "subject_books"],
)


llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
    )

chain = LLMChain(
    llm=llm,
    prompt=prompt
)


def merge_open_library_books(title_books, subject_books):
    merged = []
    seen = set()

    for source_name, books in (
        ("title_search", title_books or []),
        ("subject_search", subject_books or []),
    ):
        for book in books:
            if not isinstance(book, dict):
                continue

            work_key = book.get("works_key")
            title = book.get("title") or book.get("book_title")
            dedupe_key = work_key or title

            if not dedupe_key or dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            merged.append({
                **book,
                "source_type": source_name,
            })

    return merged


class OpenLibraryAgent:
    def __init__(self,goals=None,filters=None):
        self.tools = [search_books_by_specific_terms_in_title,get_books_for_a_specific_subject]
        self.chain = chain
        
    async def run(self,context:dict):
        title_match_books = context.get("open_library_title_items") or []
        subject_books = context.get("open_library_subject_items") or []
        open_library_books = merge_open_library_books(title_match_books, subject_books)

        title_error = context.get("open_library_title_error")
        subject_error = context.get("open_library_subject_error")
        error_parts = [err for err in (title_error, subject_error) if err]
        open_library_error = " | ".join(error_parts) if error_parts else None

        if open_library_error and not open_library_books:
            open_library_status = "error"
            openlibrary_summary = f"I couldn't fetch Open Library recommendations right now because: {open_library_error}"
        else:
            response = await self.chain.ainvoke({
                "user_input":context.get("user_input"),
                "chat_history":context.get("chat_history"),
                "title_match_books": title_match_books,
                "subject_books": subject_books,
                "goals":context.get("goals"),
                "filters": context.get("filters"),
            })

            openlibrary_summary = output_parser.parse(response['text'])

            if open_library_books:
                open_library_status = "ok"
            else:
                open_library_status = "empty"

        pprint(f"[OPEN LIBRARY AGENT] Response: {openlibrary_summary}\n")
        return {
            "open_library_status": open_library_status,
            "open_library_error": open_library_error,
            "open_library_response": openlibrary_summary,
            "recommended_books": open_library_books,
            "agent_outputs": {
                "open_library_agent": {
                    "status": open_library_status,
                    "error": open_library_error,
                    "summary": openlibrary_summary,
                    "items": open_library_books,
                    "type": "books",
                }
            }
        }
