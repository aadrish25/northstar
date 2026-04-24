from pprint import pprint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.chains import LLMChain
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from Helpers.kaggle_dataset_fetch_and_download import fetch_kaggle_datasets

load_dotenv()
import os

prompt = PromptTemplate(
    template="""
You are a Kaggle dataset recommender agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- filters: {filters}
- collected_datasets: {collected_datasets}

Rules:
- Only use datasets from collected_datasets. Never invent titles, votes, sizes, dates, refs, or URLs.
- If collected_datasets is empty, say so and ask the user to refine their request.

Response format:
- Recommend 2–5 relevant datasets.
- For each: title, why it fits the user's goal, 1–2 details (votes, size, last_updated), link.
- Prefer datasets that are practical, popular, and matched to the user's topic and level.
- If the user's need is still broad, end with a short clarifying question.
- If specific enough, give a clean final list.

Tone: conversational, clear, concise.
""",
    input_variables=["chat_history", "user_input", "goals", "filters", "collected_datasets"],
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


class KaggleDatasetsAgent:
    def __init__(self,goals=None,filters=None):
        self.tools = [fetch_kaggle_datasets]
        self.chain = chain
        
    async def run(self,context:dict):
        # items = context.get("kaggle_dataset_items") or context.get("collected_datasets") or []
        # kaggle_datasets_error = context.get("kaggle_datasets_error")

        # if kaggle_datasets_error:
        #     kaggle_datasets_status = "error"
        #     parsed_response = f"I couldn't fetch Kaggle datasets right now because: {kaggle_datasets_error}"
        # else:
        #     response = await self.chain.ainvoke({
        #         "user_input": context.get("user_input"),
        #         "chat_history": context.get("chat_history"),
        #         "goals": context.get("goals"),
        #         "filters": context.get("filters"),
        #         "collected_datasets": items,
        #     })
        #     parsed_response = output_parser.parse(response['text'])
        #     if items:
        #         kaggle_datasets_status = "ok"
        #     else:
        #         kaggle_datasets_status = "empty"

        pprint(f"\n\n[KAGGLE DATASETS AGENT]\n")
        return {
            "agent_outputs":{
                "kaggle_datasets_agent":{
                    "status":"ok",
                    "error":None,
                    "summary":f"Here are some Kaggle datasets I found for your query :\n\n {context.get('kaggle_dataset_items', [])}",
                    "items": context.get("kaggle_dataset_items") or [],
                    "type":"dataset",
                }
            }
        }
