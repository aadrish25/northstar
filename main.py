import asyncio
import json
import os
from quart import Quart, websocket,jsonify,request
from typing import Dict
from pprint import pprint
from quart_cors import cors
import requests
from werkzeug.utils import secure_filename
# --- Your existing imports ---

from Agents.Agents.parent_agent import ParentAgent
from Agents.Agents.youtube_recommender_agent import YoutubeRecommenderAgent
from Agents.Agents.github_agent import GithubAgent
from Agents.Agents.kaggle_datasets_agent import KaggleDatasetsAgent
from Agents.Agents.kaggle_notebooks_agent import KaggleNotebooksAgent
from Agents.Agents.learning_agent import LearningAgent
from Agents.Agents.feedback_loop_agent import FeedbackLoopAgent
from Agents.Agents.response_agent import ResponseAgent
from Agents.Agents.open_library_agent import OpenLibraryAgent
from Agents.Agents.career_agent import CareerAgent
from Agents.Agents.skill_builder_agent import SkillBuilderAgent
from Agents.Agents.roadmap_builder_agent import RoadmapBuilderAgent
from Agents.Agents.skill_gap_analyzer_agent import ResumeSkillGapAnalyzerAgent



from memory.tool_memory import tool_cache
from memory.chat_memory import chat_memory
from memory.memory_handler import user_recommended_memory
from tool_executor import execute_tool_with_feedback

import warnings

warnings.filterwarnings("ignore")

# --- Initialize app ---

app = Quart(__name__)
app = Quart(__name__)
app = cors(app, allow_origin="*")

learning_agent = LearningAgent()
youtube_agent = YoutubeRecommenderAgent()
parent_agent = ParentAgent()
feedback_agent = FeedbackLoopAgent()
response_agent = ResponseAgent()
github_agent = GithubAgent()
kaggle_notebooks_agent = KaggleNotebooksAgent()
kaggle_datasets_agent = KaggleDatasetsAgent()
open_library_agent = OpenLibraryAgent()
career_agent = CareerAgent()
skill_builder_agent = SkillBuilderAgent()
roadmap_builder_agent = RoadmapBuilderAgent()
resume_skill_gap_analyzer_agent = ResumeSkillGapAnalyzerAgent()

name_chain_mapping = {
    "youtube_agent": youtube_agent,
    "github_agent":github_agent,
    "kaggle_notebooks_agent": kaggle_notebooks_agent,
    "kaggle_datasets_agent":kaggle_datasets_agent,
    "open_library_agent":open_library_agent,
    "learning_planner_agent":learning_agent,
    "career_planner_agent":career_agent,
    "skill_builder_agent":skill_builder_agent,
    "roadmap_builder_agent":roadmap_builder_agent,
    "skill_gap_analyzer_agent":resume_skill_gap_analyzer_agent,
}


def _collect_preview_items_from_cached_result(result: dict, limit: int = 5):
    if not isinstance(result, dict):
        return []

    candidates = (
        result.get("items")
        or result.get("videos")
        or result.get("github_items")
        or result.get("kaggle_dataset_items")
        or result.get("kaggle_notebooks_items")
        or result.get("open_library_title_items")
        or result.get("open_library_subject_items")
        or result.get("skill_builder_items")
        or []
    )

    if not isinstance(candidates, list):
        return []

    return candidates[:limit]


async def _should_enter_feedback_mode(user_id: str, context: Dict) -> bool:
    keys = tool_cache.list_keys(user_id)
    if not keys:
        return False

    # Use cached tool outputs as the "items" for feedback classification.
    preview_items = []
    previous_query = None

    for k in keys:
        cached_full = tool_cache.get_full(user_id, k) or {}
        meta = cached_full.get("meta") or {}
        result = cached_full.get("result")

        if previous_query is None:
            previous_query = meta.get("query")

        preview_items.extend(_collect_preview_items_from_cached_result(result, limit=3))
        if len(preview_items) >= 5:
            preview_items = preview_items[:5]
            break

    tmp = {
        **context,
        "items": preview_items,
        "previous_query": previous_query,
    }

    decision = await feedback_agent.run(tmp)

    print(f"\n\n[ORCHESTRATOR] Response from feedback agent: {decision}\n")
    
    # Treat as feedback if the model is reacting to cached results:
    # - explicit save/reuse\n+    # - refine where refined_query differs from the raw user input
    action = decision.get("action")
    refined_query = decision.get("refined_query") or ""
    user_input = (context.get("user_input") or "").strip()
    context["feedback_decision"] = decision

    if action in {"save"}:
        return True
    # if action == "refine" and refined_query and refined_query.strip() != user_input:
    #     return True

    return False


async def run_agent(user_id: str, agent, context: Dict):
    # run tools
    if getattr(agent, "tools", None):
        print(f"\n [RUN AGENT] Tools: {agent.tools}\n")
        tasks = [
            execute_tool_with_feedback(
                user_id,
                tool,
                context,
                tool_cache,
                user_recommended_memory,
                feedback_agent
            )
            for tool in agent.tools
        ]

        await asyncio.gather(*tasks)

    # run agent logic
    response = await agent.run(context)
    
    print(f"\n [RUN AGENT] Agent response: {response}\n")
    if isinstance(response, dict):
        if "agent_outputs" in response:
            print("line:160")
            context.setdefault("agent_outputs",{})
            context["agent_outputs"].update(response["agent_outputs"])
            
            response = {
                k:v for k,v in response.items()
                if k != "agent_outputs"
            }
            print(f"\n [RUN AGENT] line 168: {context['agent_outputs']}\n")
            
        context.update(response)
    print(f"\n [RUN AGENT] line 171: {context['agent_outputs']}\n")
    return response


async def orchestrator(user_id: str, context: Dict):
    user_input = context.get("user_input", "")
    context["user_id"] = user_id

    # memory
    chat_memory.add_user(user_id, user_input)
    context["chat_history"] = chat_memory.get_all(user_id)

    # -----------------------
    # Feedback-only mode (avoid new tool fetches on "looks nice", etc.)
    # -----------------------
    if await _should_enter_feedback_mode(user_id, context):
        # Build a tool registry from existing agents
        print(f"\n\n[ORCHESTRATOR] Entering feedback mode based on feedback agent decision.\n")
        tools = []
        for agent in (
            youtube_agent,
            github_agent,
            kaggle_notebooks_agent,
            kaggle_datasets_agent,
            open_library_agent,
            skill_builder_agent,
            roadmap_builder_agent,
        ):
            tools.extend(getattr(agent, "tools", []) or [])

        print(f"\n\n[ORCHESTRATOR] Tools available for feedback mode: {tools}\n")
        tool_by_name = {getattr(t, "__name__", str(t)): t for t in tools}

        cached_tool_names = set(tool_cache.list_keys(user_id))
        runnable_tools = [tool_by_name[n] for n in cached_tool_names if n in tool_by_name]
        
        print(f"\n\n[ORCHESTRATOR] Runnable tools based on cache: {runnable_tools}\n")

        if runnable_tools:
            await asyncio.gather(*[
                execute_tool_with_feedback(
                    user_id,
                    tool,
                    context,
                    tool_cache,
                    user_recommended_memory,
                    feedback_agent,
                )
                for tool in runnable_tools
            ])

        final_output = await response_agent.run(context)
        context["response"] = final_output
        chat_memory.add_agent(user_id, final_output)
        return context

    # -----------------------
    # Parent → 1st Subagent
    # -----------------------
    parent_res = await parent_agent.run(context)
    pprint(f"[ORCHESTRATOR] Parent response: {parent_res}")
    if isinstance(parent_res, dict):
        context.update(parent_res)
        
    # extract the selected agent from parent response
    selected_agent = parent_res.get("agent")
    
    print(f"\n\n[ORCHESTRATOR] Selected agent: {selected_agent}\n")
    
    # select the agent instance
    selected_agent_instance = name_chain_mapping.get(selected_agent,None)
    
    
    if selected_agent_instance is None:
        context["response"] = "Ambiguous query, please clarify your purpose."
        return

    agent_response = await selected_agent_instance.run(context)
    if isinstance(agent_response, dict):
        context.update(agent_response)
        
    pprint(f"[ORCHESTRATOR] Agent response: {agent_response}")
    
    # ✅ Normalize agents to a list
    if isinstance(context.get("agents"), str):
        context["agents"] = [
            a.strip() for a in context["agents"].split(",") if a.strip()
        ]

    # unify query
    # context["query"] = context.get("youtube_query") or context.get("github_query")

    # -----------------------
    # Run Agents
    # -----------------------
    agents = [
        name_chain_mapping[a]
        for a in context.get("agents", ["youtube_agent"])
        if a in name_chain_mapping
    ]
    
    pprint(f"\n [ORCHESTRATOR] Agents selected: {agents}\n")

    await asyncio.gather(*[
        run_agent(user_id, agent, context)
        for agent in agents
    ])

    # -----------------------
    # Final Response
    # -----------------------
    final_output = await response_agent.run(context)

    context["response"] = final_output

    chat_memory.add_agent(user_id, final_output)
    
    action = context.get("feedback_decision", {}).get("action") 
    if action == "save":
        tool_cache.clear(user_id)

    return context


# -----------------------

# WebSocket Route

# -----------------------

@app.websocket("/ws/<user_id>")
async def ws(user_id):
    print(f"Client connected: {user_id}")
    try:

        while True:
            # Receive message from client

            data = await websocket.receive()

            # Assume plain text input (can switch to JSON if needed)
            context = {

                "user_input": data

            }
            # Run orchestrator
            try:
                print(f"context: {context}")
                result = await orchestrator(user_id, context)
                print(f"result: {result}")
                await websocket.send(json.dumps({"message":result["response"]}))
            except Exception as e:
                print(f"Error: {e}")
                await websocket.send(json.dumps({"message":"Error: "+str(e)}))


    except Exception as e:
        print(f"Connection closed for {user_id}: {e}")



@app.route("/")
async def index():
    return "Hello, World!"

@app.route("/get_resource_by_type/<user_id>/<type>", methods=["POST"])
async def get_resource_by_type(user_id, type):
    result = user_recommended_memory.get_by_type(user_id, type)
    print("result", result)
    return jsonify({"response": result})

@app.route("/update_resource_status/<user_id>/<resource_id>", methods=["POST"])
async def update_resource_status(user_id, resource_id):
    status = requests.json.get("status")
    ok = user_recommended_memory.update_status(user_id, resource_id, status)
    return jsonify({"success": ok})

@app.route("/delete_resource/<user_id>/<resource_id>", methods=["DELETE"])
async def delete_resource(user_id, resource_id):
    ok = user_recommended_memory.delete(user_id, resource_id)
    return jsonify({"success": ok})


UPLOAD_FOLDER = "resume"
ALLOWED_EXTENSIONS = {"pdf"}

# Create folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/upload_resume/<user_id>", methods=["POST"])
async def upload_resume(user_id):
    try:
        files = await request.files
        file = files.get("file")   # Frontend should send field name "file"

        if not file:
            return jsonify({
                "success": False,
                "message": "No file uploaded"
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": "Only PDF files allowed"
            }), 400

        # Safe filename
        safe_user_id = secure_filename(user_id)

        # Final path: resume/user123_resume.pdf
        file_path = os.path.join(
            UPLOAD_FOLDER,
            f"{safe_user_id}_resume.pdf"
        )

        # Delete old resume if exists
        if os.path.exists(file_path):
            os.remove(file_path)

        # Save new resume
        await file.save(file_path)

        return jsonify({
            "success": True,
            "message": "Resume uploaded successfully",
            "file_path": file_path
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# -----------------------
# Run Server
# -----------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
 