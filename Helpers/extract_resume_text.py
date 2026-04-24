from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama
from langchain_core.output_parsers import JsonOutputParser

import pymupdf
import asyncio

# global variable
user_resume_text = None

# ============================== RESUME EXTRACTION SYSTEM PROMPT ==============================
RESUME_EXTRACTION_SYSTEM = ChatPromptTemplate.from_template(template="""
You are a resume parser. Extract structured information from the resume text and return ONLY a valid JSON object with no markdown, no backticks, no preamble.

Use exactly this schema:
{{
  "user_skills": [
    // All technical skills, frameworks, libraries, tools, and concepts mentioned
    // Include everything: ML concepts, frameworks, cloud tools, databases, deployment tools
    // Do NOT include soft skills, hobbies, or spoken languages
  ],
  "user_known_languages": [
    // Programming languages only (Python, Java, C++, etc.)
    // Do NOT include spoken/natural languages
  ],
  "user_projects": [
    {{
      "name": "project name as written",
      "description": "one sentence summary of what was built and the outcome",
      "tech_stack": ["technologies used in this specific project"],
      "domain": "one of: Machine Learning / Deep Learning / NLP / Computer Vision / Data Engineering / Web Development / Other"
    }}
  ],
  "user_certifications": [
    // Full certification name with issuer, e.g. "Machine Learning – Coursera (Andrew Ng)"
  ],
  "user_experience": [
    {{
      "role": "job title",
      "company": "company name",
      "duration_months": <integer>,
      "contributions": [
        // 2-4 bullet points describing what they actually did, not copied verbatim
      ]
    }}
  ],
  "user_education": {{
    "degree": "full degree name and field",
    "institution": "institution name",
    "graduation_year": <integer>,
    "cgpa": <float or null if not mentioned>
  }},
  "user_profile_summary": "2-3 sentence summary covering: current status (year/degree), strongest technical areas, and experience level. Be factual, no fluff."
}}

Rules:
- Return ONLY the JSON. No explanation, no markdown, no extra text.
- If a field has no data, return an empty list [] or null.
- duration_months: calculate from dates if given, estimate if only years are given.
- Do not invent or infer skills not explicitly mentioned in the resume.



\n\n RESUME TEXT:\n\n
{resume_text}
""")


# define llm
llm = ChatOllama(model="deepseek-v3.1:671b-cloud")



# ============================== RESUME EXTRACTION FUNCTION ==============================
# extract raw text from PDF using pymupdf (fitz)
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = pymupdf.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

# extract resume info in a structured format using the LLM and the system prompt
async def extract_resume_info(resume_text: str) -> dict:
    """"Extract structured information from a resume text using an LLM."""
    
    resume_info_extract_chain = RESUME_EXTRACTION_SYSTEM | llm | JsonOutputParser()
    
    response = await resume_info_extract_chain.ainvoke({"resume_text": resume_text})
    
    return response
# =======================================================================================   


async def extract_resume_info_from_pdf(pdf_path: str) -> dict:
    """Extract structured information from a resume PDF."""
    global user_resume_text
    if user_resume_text is None:
      resume_text = extract_text_from_pdf(pdf_path)
    resume_info = await extract_resume_info(resume_text)
    return resume_info
  

async def main():
  resume_text = await extract_resume_info_from_pdf(pdf_path=r"sample_resume/sample_resume.pdf")
  return resume_text
if __name__=="__main__":
    asyncio.run(main())