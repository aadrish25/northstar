from pprint import pprint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.chains import LLMChain
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from Helpers.kaggle_notebook_fetch_and_download import fetch_kaggle_notebooks

load_dotenv()
import os

prompt = PromptTemplate(
    template="""
You are a Kaggle notebook recommender agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- filters: {filters}
- collected_notebooks: {collected_notebooks}

Rules:
- Only use notebooks from collected_notebooks. Never invent titles, authors, votes, languages, refs, or URLs.
- If collected_notebooks is empty, say so and ask the user to refine their request.

Response format:
- Recommend 2–5 relevant notebooks.
- For each: title, why it fits the user's goal, 1–2 details (author, votes, language), link.
- Prefer notebooks that are practical, popular, and matched to the user's topic and level.
- If the user's need is still broad, end with a short clarifying question.
- If specific enough, give a clean final list.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "filters", "collected_notebooks"],
)

output_parser = StrOutputParser()

llm = ChatGroq(
    api_key = os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
    )

chain = LLMChain(
    llm=llm,
    prompt=prompt
)


class KaggleNotebooksAgent:
    def __init__(self,goals=None,filters=None):
        self.tools = [fetch_kaggle_notebooks]
        self.chain = chain
        
    async def run(self,context:dict):
        items = context.get("kaggle_notebooks_items") or context.get("collected_notebooks") or []
        kaggle_notebooks_error = context.get("kaggle_notebooks_error")

        if kaggle_notebooks_error:
            kaggle_notebooks_status = "error"
            parsed_response = f"I couldn't fetch Kaggle notebooks right now because: {kaggle_notebooks_error}"
        else:
            response = await self.chain.ainvoke({
                "user_input": context.get("user_input"),
                "chat_history": context.get("chat_history"),
                "goals": context.get("goals"),
                "filters": context.get("filters"),
                "collected_notebooks": items,
            })
            parsed_response = output_parser.parse(response['text'])
            if items:
                kaggle_notebooks_status = "ok"
            else:
                kaggle_notebooks_status = "empty"

        pprint(f"\n\n[KAGGLE NOTEBOOKS AGENT] Response: {parsed_response}\n\n")
        return {
            "kaggle_response": parsed_response,
            "kaggle_notebooks_response": parsed_response,
            "kaggle_notebooks_status": kaggle_notebooks_status,
            "kaggle_notebooks_error": kaggle_notebooks_error,
            "recommended_kaggle_notebooks": items,
            "agent_outputs": {
                "kaggle_notebooks_agent": {
                    "status": kaggle_notebooks_status,
                    "error": kaggle_notebooks_error,
                    "summary": parsed_response,
                    "items": items,
                    "type": "notebook",
                }
            }
        }
