import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from pprint import pprint
from memory.tool_memory import tool_cache

load_dotenv()


# -----------------------
# Prompt
# -----------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a smart assistant responsible for generating the final response to the user.

Your job:
- Read the available downstream agent summaries and use them to answer the user
- If information is insufficient → ask a short clarifying question
- If recommendations, explanations, or roadmaps exist → present them clearly
- If resume skill gap analysis exists → present the strongest matches, key gaps, and the best next step clearly
- Do NOT hallucinate resources, items, links, books, videos, repos, notebooks, datasets, roles, or skills
- Prefer the most relevant information based on the user's goal and filters
- If multiple agent summaries are available, combine them into one natural response without sounding repetitive
- If roadmap resources or links are available, include direct resource URLs in the final answer
- For roadmap answers, end with a short "Resources" list containing concrete URLs from provided data
- If skill gap analysis is available together with roadmap or skill-builder outputs, combine them naturally: first explain alignment/gaps, then suggest what to learn next
- If skill gap analysis is unavailable or failed, do not invent it; rely on the other available agent outputs instead
- If no useful results are available, say so clearly and guide the user toward a better next query

Be conversational, concise, and well-structured.
"""),
    ("human", """USER INPUT:
{user_input}

CHAT HISTORY:
{chat_history}

GOALS:
{goals}

FILTERS:
{filters}

RECOMMENDED VIDEOS:
{recommended_videos}

Github Agent Summary:
{github_response}

Kaggle Notebooks Agent Response:
{kaggle_notebooks_response}

Kaggle Datasets Agent Response:
{kaggle_datasets_response}

Open Library Agent Summary:
{open_library_response}

Skill Builder Agent Summary:
{skill_builder_response}


Roadmap Builder Agent Summary:
{roadmap_response}

Roadmap Resource URLs:
{roadmap_resources}


Skill Gap Analysis:
{skill_gap_analysis_summary}

STATE:
{state}
""")
])


# -----------------------
# LLM
# -----------------------
# llm = ChatGroq(
#     api_key = os.getenv("GROQ_API_KEY"),
#     model_name="llama-3.3-70b-versatile"
#     )

llm = ChatOllama(model="deepseek-v3.1:671b-cloud")

chain = prompt | llm


# -----------------------
# Agent
# -----------------------
class ResponseAgent:
    def __init__(self):
        self.chain = chain

    @staticmethod
    def _build_roadmap_resources_text(context: dict) -> str:
        roadmaps = context.get("recommended_roadmaps") or context.get("roadmap_items") or []
        if not isinstance(roadmaps, list) or not roadmaps:
            return "None"

        lines = []
        roadmap_count = 0

        for item in roadmaps:
            if roadmap_count >= 3:
                break

            resources = item.get("resources") or {}
            if not isinstance(resources, dict) or not resources:
                continue

            title = item.get("title") or item.get("skill") or "Roadmap"
            collected = []

            for rtype, entries in resources.items():
                if not isinstance(entries, list):
                    continue

                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    url = entry.get("url")
                    if not url:
                        continue
                    label = entry.get("label") or "Resource"
                    collected.append((rtype, label, url))
                    if len(collected) >= 5:
                        break

                if len(collected) >= 5:
                    break

            if not collected:
                continue

            roadmap_count += 1
            lines.append(f"{roadmap_count}. {title}")
            for rtype, label, url in collected:
                lines.append(f"   [{rtype}] {label}: {url}")

        return "\n".join(lines) if lines else "None"

    async def run(self, context: dict):
        # Prepare compact video text
        videos_cache = tool_cache.get_full(user_id=context.get("user_id"), tool_id="run_video_ranker_agent") or {}
        print(f"\nline:151 videos_cache: {videos_cache}\n")
        videos = videos_cache.get("result")
        print(f"\nline:152 context: {context.keys()}\n")
        print(f"\nline:153 agent_outputs: {context.get('agent_outputs', {})}\n")
        # videos = context.get("agent_outputs").get("youtube_recommender_agent") or []
        print(f"line:154")
        video_text = ""
        for i, v in enumerate(videos.get("items"), start=1):
            video_text += (
                f"{i}. {v.get('video_title')}\n"
                f"   Channel: {v.get('channel_name')}\n"
                f"   Link: {v.get('video_url')}\n\n"
            )
        # print(f"line:162")
        # pprint(f"\n\n[RESPONSE AGENT] Prepared video text:\n{video_text}\n\n")
        # print(f"line:164")    
        # # prepare the github repos 
        # repos = context.get("recommended_repos") or []
        # repo_text = ""
        # if repos:
        #     for i,repo in enumerate(repos[:10],start=1):
        #         repo_text += (
        #             f"{i}. {repo.get('name')}\n"
        #             f"   Description: {repo.get('description') or 'No description'}\n"
        #             f"   Owner: {(repo.get('owner') or {}).get('username', 'Unknown')}\n"
        #             f"   Stars: {(repo.get('stats') or {}).get('stars', 'N/A')}\n"
        #             f"   Language: {(repo.get('tech') or {}).get('language') or 'N/A'}\n"
        #             f"   Link: {repo.get('url')}\n\n"
        #         )
            
        # print(f"line:179")
        # # for kaggle notebooks
        # notebooks = context.get("recommended_kaggle_notebooks") or []
        # kaggle_text = ""
        # if notebooks:
        #     for i, notebook in enumerate(notebooks[:5], start=1):
        #         kaggle_text += (
        #             f"{i}. {notebook.get('title')}\n"
        #             f"   Author: {notebook.get('author') or 'Unknown'}\n"
        #             f"   Votes: {notebook.get('votes', 'N/A')}\n"
        #             f"   Language: {notebook.get('language') or 'N/A'}\n"
        #             f"   Link: {notebook.get('url')}\n\n"
        #         )
        
        # print(f"line:193")
        # # for kaggle datasets
        # datasets = context.get("recommended_kaggle_datasets") or []
        # dataset_text = ""
        # if datasets:
        #     for i, dataset in enumerate(datasets[:5], start=1):
        #         dataset_text += (
        #             f"{i}. {dataset.get('title')}\n"
        #             f"   Votes: {dataset.get('votes', 'N/A')}\n"
        #             f"   Size: {dataset.get('size') or 'N/A'}\n"
        #             f"   Last Updated: {dataset.get('last_updated') or 'N/A'}\n"
        #             f"   Link: {dataset.get('url')}\n\n"
        #         )
        # print(f"line:206")
        # # for open library books
        # books = context.get("recommended_books") or []
        # books_text = ""
        # if books:
        #     for i, book in enumerate(books[:5], start=1):
        #         title = book.get("title") or book.get("book_title") or "Unknown title"
        #         author = book.get("author_name")
        #         if isinstance(author, list):
        #             author = ", ".join(author[:2]) if author else None
        #         if not author:
        #             author_names = book.get("author_names")
        #             if isinstance(author_names, list):
        #                 author = ", ".join(author_names[:2]) if author_names else None

        #         subject = book.get("subject")
        #         if isinstance(subject, list):
        #             subject = ", ".join(subject[:2]) if subject else None
        #         if not subject:
        #             covered = book.get("subject_covered")
        #             if isinstance(covered, list):
        #                 subject = ", ".join(covered[:2]) if covered else None

        #         year = book.get("first_publish_year") or "N/A"
        #         work_key = book.get("works_key") or "N/A"
        #         source_type = book.get("source_type") or "N/A"

        #         books_text += (
        #             f"{i}. {title}\n"
        #             f"   Author: {author or 'Unknown'}\n"
        #             f"   Subject: {subject or 'N/A'}\n"
        #             f"   First Published: {year}\n"
        #             f"   Work Key: {work_key}\n"
        #             f"   Source: {source_type}\n\n"
        #         )
        # print(f"line:241")
        # roadmap_resources_text = self._build_roadmap_resources_text(context)
        # print(f"line:243")
        response = await self.chain.ainvoke({
            "user_input": context.get("user_input"),
            "chat_history": context.get("chat_history"),
            "goals": context.get("goals"),
            "filters": context.get("filters"),
            "recommended_videos": video_text or "None",
            "recommended_repos": "None",
            "recommended_kaggle_notebooks": "None",
            "recommended_kaggle_datasets": "None",
            "kaggle_datasets_response":context.get("kaggle_datasets_response") or None,
            "kaggle_notebooks_response":context.get("kaggle_notebooks_response") or None,
            "recommended_books": "None",
            "github_response": context.get("github_response") or "None",
            "open_library_response": context.get("open_library_response") or "None",
            "open_library_status": context.get("open_library_status") or "None",
            "open_library_error": context.get("open_library_error") or "None",
            "skill_builder_response":context.get("skill_builder_response") or None,
            "roadmap_response":context.get("roadmap_response") or None,
            "roadmap_resources": "None",
            "skill_gap_analysis_summary": context.get("skill_gap_analyzer_response") or "None",
            "agent_outputs": context.get("agent_outputs") or "None",
            "resources": context.get("resources") or "None",
            "state": context.get("state") or "suggesting",
        })

        return response.content
