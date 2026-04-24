import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
# from langchain_openrouter import ChatOpenRouter
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from memory.tool_memory import tool_cache
from Agents.Agents.open_library_agent import merge_open_library_books

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

Recommended GitHub Repositories:
{recommended_repos}

Recommended Kaggle Notebooks:
{recommended_kaggle_notebooks}

Recommended Kaggle Datasets:
{recommended_kaggle_datasets}

Recommended Books:
{recommended_books}

Skill Builder Result:
{skill_builder_result}


Roadmap Response:
{roadmap_response}


Skill Gap Analysis:
{skill_gap_analysis}

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
    def _build_skill_gap_summary_text(context: dict) -> str:
        agent_outputs = context.get("agent_outputs") or {}
        skill_gap_output = agent_outputs.get("resume_skill_gap_analyzer_agent") or {}

        return (
            context.get("skill_gap_analyzer_response")
            or skill_gap_output.get("summary")
            or "None"
        )


    @staticmethod
    def _build_roadmap_text(roadmap_items: list) -> str:
        if not isinstance(roadmap_items, list) or not roadmap_items:
            return "None"

        lines = []

        for i, item in enumerate(roadmap_items, start=1):
            if not isinstance(item, dict):
                continue

            title = item.get("title") or "Untitled roadmap item"
            skill = item.get("skill") or "N/A"
            description = item.get("description") or "No description"

            lines.append(f"{i}. {title}")
            lines.append(f"   Skill: {skill}")
            lines.append(f"   Description: {description}")

            resources = item.get("resources") or {}
            resource_count = 0

            if isinstance(resources, dict):
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
                        lines.append(f"   [{rtype}] {label}: {url}")
                        resource_count += 1

                        if resource_count >= 3:
                            break

                    if resource_count >= 3:
                        break

            lines.append("")

        return "\n".join(lines).strip() or "None"

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
        # =============================================================================Prepare compact video text======================================================================
        videos_cache = tool_cache.get_full(user_id=context.get("user_id"), tool_id="run_video_ranker_agent") or {}
        # print(f"\nline:201 videos_cache: {videos_cache}\n")
        videos = videos_cache.get("result")
        # print(f"\nline:203 context: {context.keys()}\n")
        # print(f"\nline:204 agent_outputs: {context.get('agent_outputs', {})}\n")
        # videos = context.get("agent_outputs").get("youtube_recommender_agent") or []
        # print(f"line:206")
        video_text = ""
        if videos:
            for i, v in enumerate(videos.get("items"), start=1):
                video_text += (
                    f"{i}. {v.get('video_title')}\n"
                    f"   Channel: {v.get('channel_name')}\n"
                    f"   Link: {v.get('video_url')}\n\n"
                )
            # print(f"line:162")
            # print(f"\n\n[RESPONSE AGENT] Prepared video text:\n{video_text}\n\n")
        # print(f"line:217")    
        # =========================================================================================================================================================================
        # ================================================================== prepare the github repos ============================================================================= 
        repositories_cache = tool_cache.get_full(user_id=context.get("user_id"), tool_id="github_repo_fetcher") or {}

        # print(f"\nline:222 repositories_cache: {repositories_cache}\n")
        repos = repositories_cache.get("result")
        repo_text = ""
        if repos:
            for i,repo in enumerate(repos.get("items"),start=1):
                repo_text += (
                    f"{i}. {repo.get('name')}\n"
                    f"   Description: {repo.get('description') or 'No description'}\n"
                    f"   Owner: {(repo.get('owner') or {}).get('username', 'Unknown')}\n"
                    f"   Stars: {(repo.get('stats') or {}).get('stars', 'N/A')}\n"
                    f"   Language: {(repo.get('tech') or {}).get('language') or 'N/A'}\n"
                    f"   Link: {repo.get('url')}\n\n"
                )
                
            # print(f"\n\n[RESPONSE AGENT] Prepared repo text:\n{repo_text}\n\n")
        # =====================================================================================================================================================
        # print(f"line:238")
        
        
        # ==================================================================== for kaggle notebooks =============================================================================================
        notebooks_cache = tool_cache.get_full(user_id=context.get("user_id"),tool_id="fetch_kaggle_notebooks")
        # print(f"\nline:243 notebooks_cache: {notebooks_cache}\n")
        notebooks = notebooks_cache.get("result") or [] if notebooks_cache else []
        notebooks_text = ""
        if notebooks:
            for i, notebook in enumerate(notebooks.get("items"), start=1):
                notebooks_text += (
                    f"{i}. {notebook.get('title')}\n"
                    f"   Author: {notebook.get('author') or 'Unknown'}\n"
                    f"   Votes: {notebook.get('votes', 'N/A')}\n"
                    f"   Language: {notebook.get('language') or 'N/A'}\n"
                    f"   Link: {notebook.get('url')}\n\n"
                )
        
            # print(f"\n\n[RESPONSE AGENT] Prepared Kaggle notebook text:\n{notebooks_text}\n\n")
        # =====================================================================================================================================================
        
        # print(f"line:259")
        # =============================================================== for kaggle datasets ==================================================================
        datasets_cache = tool_cache.get_full(user_id=context.get("user_id"),tool_id="fetch_kaggle_datasets")
        # print(f"\nline:262 datasets_cache: {datasets_cache}\n")
        datasets = datasets_cache.get("result") or [] if datasets_cache else []
        dataset_text = ""
        if datasets:
            for i, dataset in enumerate(datasets.get("items"), start=1):
                dataset_text += (
                    f"{i}. {dataset.get('title')}\n"
                    f"   Votes: {dataset.get('votes', 'N/A')}\n"
                    f"   Size: {dataset.get('size') or 'N/A'}\n"
                    f"   Last Updated: {dataset.get('last_updated') or 'N/A'}\n"
                    f"   Link: {dataset.get('url')}\n\n"
                )
                
            # print(f"\n\n[RESPONSE AGENT] Prepared Kaggle dataset text:\n{dataset_text}\n\n")
        # ============================================================================================================================
        # print(f"line:277")
        # ==================================================== for open library books ===========================================================================
        title_cache = tool_cache.get_full(
        user_id=context.get("user_id"),
        tool_id="search_books_by_specific_terms_in_title"
        ) or {}
        
        # print(f"\nline:284 title_cache: {title_cache}\n")
        
        subject_cache = tool_cache.get_full(
            user_id=context.get("user_id"),
            tool_id="get_books_for_a_specific_subject"
        ) or {}
        
        # print(f"\nline:291 subject_cache: {subject_cache}\n")
        
        
        title_result = title_cache.get("result") or {} if title_cache else {}
        subject_result = subject_cache.get("result") or {} if subject_cache else {}
        
        title_books = title_result.get("open_library_title_items") or []
        subject_books = subject_result.get("open_library_subject_items") or []
        
        merged_books = merge_open_library_books(title_books, subject_books)
        # print(f"\nline:301 merged_books: {merged_books}\n")
        books_text = ""
        if merged_books:
            for i, book in enumerate(merged_books, start=1):
                title = book.get("title") or book.get("book_title") or "Unknown title"
                author = book.get("author_name")
                if isinstance(author, list):
                    author = ", ".join(author[:2]) if author else None
                if not author:
                    author_names = book.get("author_names")
                    if isinstance(author_names, list):
                        author = ", ".join(author_names[:2]) if author_names else None

                subject = book.get("subject")
                if isinstance(subject, list):
                    subject = ", ".join(subject[:2]) if subject else None
                if not subject:
                    covered = book.get("subject_covered")
                    if isinstance(covered, list):
                        subject = ", ".join(covered[:2]) if covered else None

                year = book.get("first_publish_year") or "N/A"
                work_key = book.get("works_key") or "N/A"
                source_type = book.get("source_type") or "N/A"

                books_text += (
                    f"{i}. {title}\n"
                    f"   Author: {author or 'Unknown'}\n"
                    f"   Subject: {subject or 'N/A'}\n"
                    f"   First Published: {year}\n"
                    f"   Work Key: {work_key}\n"
                    f"   Source: {source_type}\n\n"
                )
                
                
            # print(f"\n\n[RESPONSE AGENT] Prepared Open Library books text:\n{books_text}\n\n")
        # ===================================================================================================================================
        # print(f"line:338")
        # ==================================================================== Skill Builder items ============================================
        skill_builder_cache = tool_cache.get_full(user_id=context.get("user_id"), tool_id="fetch_skill_tree") or {}
        # print(f"\nline:341 skill_builder_cache: {skill_builder_cache}\n")
        skills = skill_builder_cache.get("result").get("items")[0] or [] if skill_builder_cache else []
        skill_builder_text = ""
        if skills:
            for i,skill in enumerate(skills.get("skills"),start=1):
                skill_builder_text += (
                    f"{i}. Skill: {skill.get('skill')}\n"
                    f"     Demand:{skill.get('demand', 1)}\n"
                )
            # print(f"\n\n[RESPONSE AGENT] Prepared skill builder text:\n{skill_builder_text}\n\n")
        # ===================================================================================================================================
        # ==================================================================== Roadmap agent ============================================
        # print(f"line:353")
        roadmap_cache = tool_cache.get_full(
            user_id=context.get("user_id"),
            tool_id="fetch_roadmap"
        ) or {}
        # # print(f"\nline:358 roadmap_cache: {roadmap_cache}\n")

        roadmap_result = roadmap_cache.get("result") or {} if roadmap_cache else {}
        roadmap_items = roadmap_result.get("roadmap_items") or []
        roadmap_text = ""
        if roadmap_items:
            roadmap_text = self._build_roadmap_text(roadmap_items)
            # # print(f"\n\n[RESPONSE AGENT] Prepared roadmap text:\n{roadmap_text}\n\n")
        # print(f"line:365")
        # ==========================================================================================================================================
        
        
        # ========================================================================================= Resume Skill Gap Analyzer =======================================
        
        skill_gap_analysis_text = self._build_skill_gap_summary_text(context=context)
        # if skill_gap_analysis_text:
            # print(f"\n[RESPONSE AGENT] Prepared skill gap analysis text:\n{skill_gap_analysis_text}\n")
        
        response = await self.chain.ainvoke({
            "user_input": context.get("user_input"),
            "chat_history": context.get("chat_history"),
            "goals": context.get("goals"),
            "filters": context.get("filters"),
            "recommended_videos": video_text or "None",
            "recommended_repos": repo_text or "None",
            "recommended_kaggle_notebooks": notebooks_text or "None",
            "recommended_kaggle_datasets": dataset_text or "None",
            "recommended_books": books_text or "None",
            "skill_builder_result": skill_builder_text or "None",
            "roadmap_response": roadmap_text or "None",
            "skill_gap_analysis": skill_gap_analysis_text or "None",
            "agent_outputs": context.get("agent_outputs") or "None",
            "resources": context.get("resources") or "None",
            "state": context.get("state") or "suggesting",
        })

        return response.content
