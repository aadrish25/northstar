from pprint import pprint
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from Helpers.resume_skill_gap_analyzer_tool import align_resume_with_job_descriptions

load_dotenv()

import os
from memory.chat_memory import chat_memory


# define llm 
llm = ChatOllama(model="deepseek-v3.1:671b-cloud")


# resume skill gap analysis system prompt
prompt = ChatPromptTemplate.from_template(
    template="""
You are a resume skill gap analysis agent.

Given:
- chat_history: {chat_history}
- user_input: {user_input}
- goals: {goals}
- skill_gap_analysis: {skill_gap_analysis}

Rules:
- Only use information present in skill_gap_analysis. Never invent skills, certifications, scores, projects, or requirements.
- If skill_gap_analysis is missing, empty, or failed, say that clearly and ask the user to refine the target role or try again.
- Prioritize the most important gaps first, especially high-priority missing skills and languages.
- Keep the response practical, specific, and easy to act on.

Response format:
- Start with a short overall match summary.
- Then list:
  1. strongest matched skills
  2. most important missing skills
  3. missing programming languages, if any
  4. recommended project focus
  5. recommended certifications, if any
  6. the single best next step
- If the user asks for advice, explain the next step in a concise, career-oriented way.
- If the analysis already looks strong, say where the resume is competitive and what would improve it further.

Tone: conversational, clear, supportive, and concise.
"""
)



# chain
skill_gap_analysis_chain = prompt | llm | StrOutputParser()


class ResumeSkillGapAnalyzerAgent:
    def __init__(self,goals=None, filters=None):
        self.tools = [align_resume_with_job_descriptions]
        self.chain = skill_gap_analysis_chain

    @staticmethod
    def _format_frequency_label(count: int, noun: str = "job descriptions") -> str:
        if count is None:
            return f"mentioned in 0 {noun}"
        return f"mentioned in {count} {noun}"

    @staticmethod
    def _format_ranked_items(items: list, key_name: str) -> list[str]:
        if not isinstance(items, list) or not items:
            return ["None"]

        lines = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue

            name = item.get(key_name) or "N/A"
            priority = item.get("priority")
            frequency = item.get("frequency", 0)
            reason = item.get("reason")

            lines.append(f"{idx}. {name}")
            if priority:
                lines.append(f"   Priority: {priority}")
            lines.append(
                f"   Frequency: {ResumeSkillGapAnalyzerAgent._format_frequency_label(frequency)}"
            )
            if reason:
                lines.append(f"   Reason: {reason}")

        return lines or ["None"]

    @staticmethod
    def _build_skill_gap_analysis_text(analysis: dict) -> str:
        if not isinstance(analysis, dict) or not analysis:
            return "Skill gap analysis is not available right now."

        target_role = analysis.get("target_role") or "Unknown Role"
        overall_match_score = analysis.get("overall_match_score", "N/A")
        summary = analysis.get("summary") or "No summary available."
        experience_gap = analysis.get("experience_gap") or "No experience gap provided."

        matched_skills = analysis.get("matched_skills") or []
        missing_skills = analysis.get("missing_skills") or []
        missing_languages = analysis.get("missing_languages") or []
        project_relevance = analysis.get("project_relevance") or {}
        certification_recommendations = analysis.get("certification_recommendations") or []

        lines = [
            f"Resume Skill Gap Analysis for {target_role}",
            "",
            f"Overall Match Score: {overall_match_score}%",
            "",
            "Summary:",
            summary,
            "",
            "Strongest Matched Skills:",
        ]

        if matched_skills:
            for idx, item in enumerate(matched_skills, start=1):
                if not isinstance(item, dict):
                    continue
                skill = item.get("skill") or "N/A"
                frequency = item.get("frequency", 0)
                lines.append(
                    f"{idx}. {skill} - {ResumeSkillGapAnalyzerAgent._format_frequency_label(frequency)}"
                )
        else:
            lines.append("None")

        lines.extend(["", "Most Important Missing Skills:"])
        lines.extend(ResumeSkillGapAnalyzerAgent._format_ranked_items(missing_skills, "skill"))

        lines.extend(["", "Missing Programming Languages:"])
        lines.extend(ResumeSkillGapAnalyzerAgent._format_ranked_items(missing_languages, "language"))

        lines.extend(["", "Project Relevance:"])
        relevant_projects = project_relevance.get("relevant_projects") or []
        if relevant_projects:
            lines.append("Relevant Projects:")
            for idx, project in enumerate(relevant_projects, start=1):
                lines.append(f"{idx}. {project}")
        else:
            lines.append("Relevant Projects:")
            lines.append("None")

        lines.append("")
        lines.append("Project Gap:")
        lines.append(project_relevance.get("gap") or "No project gap provided.")

        lines.extend(["", "Certification Recommendations:"])
        if certification_recommendations:
            for idx, cert in enumerate(certification_recommendations, start=1):
                if not isinstance(cert, dict):
                    continue
                lines.append(f"{idx}. {cert.get('name') or 'N/A'}")
                lines.append(f"   Provider: {cert.get('provider') or 'N/A'}")
                lines.append(f"   Reason: {cert.get('reason') or 'No reason provided.'}")
        else:
            lines.append("None")

        lines.extend([
            "",
            "Experience Gap:",
            experience_gap,
            "",
            "Best Next Step:",
        ])

        best_next_step = (
            project_relevance.get("gap")
            or summary
            or "Build one strong project aligned with the missing high-priority skills."
        )
        lines.append(best_next_step)

        return "\n".join(lines).strip()

    async def run(self, context:dict):
        print(f"\n[RESUME SKILL GAP ANALYZER AGENT]\n")

        analysis_error = context.get("skill_gap_analysis_error")
        analysis_items = context.get("skill_gap_analysis_items") or []
        analysis = analysis_items[0] if analysis_items and isinstance(analysis_items[0], dict) else {}

        if analysis_error:
            formatted_summary = (
                f"I couldn't perform the skill gap analysis right now because: {analysis_error}"
            )
            skill_gap_analyzer_status = "error"
        elif analysis:
            formatted_summary = self._build_skill_gap_analysis_text(analysis)
            skill_gap_analyzer_status = "ok"
        else:
            formatted_summary = "Skill gap analysis is not available right now."
            skill_gap_analyzer_status = "empty"

        return {
            "skill_gap_analyzer_response": formatted_summary,
            "agent_outputs":{
                "resume_skill_gap_analyzer_agent":{
                    "status": skill_gap_analyzer_status,
                    "error": analysis_error,
                    "summary": formatted_summary,
                    "items": analysis_items,
                    "type":"skill_gap_analysis",
                }
            }
        }
                
                
