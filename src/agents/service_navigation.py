"""
Government Service Navigation Agent.

Turns a citizen's problem into a step-by-step navigation flow: the
recommended authority, documents needed, the procedure to follow, and any
relevant official portal/helpline — grounded in the retrieved legal/
government context where possible.
"""
from src.common.json_llm import call_llm_json
from src.rag.prompts import SYSTEM_PROMPT
from src.rag.retriever import Retriever

NAVIGATION_PROMPT = """Context (official sources, may be incomplete):
{context}

A citizen describes this problem: "{problem}"

Respond with ONLY a JSON object (no markdown, no commentary, no code fences), \
in {language}, with exactly these keys:

{{
  "problem_identified": "short label for the problem",
  "recommended_authority": "the specific government body/department/authority to approach",
  "documents_required": ["list", "of", "documents", "needed"],
  "procedure_steps": ["step 1", "step 2", "step 3"],
  "official_portal_name": "name of the relevant official portal/helpline if mentioned in context, else empty string",
  "official_portal_note": "a short note on how to find/use it. Do not invent a URL that isn't in the context."
}}
"""


class ServiceNavigationAgent:
    def __init__(self):
        self.retriever = Retriever()

    def navigate(self, problem: str, language: str = "English") -> dict:
        chunks = self.retriever.search(problem)
        context = (
            "\n\n---\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)
            or "No relevant context was retrieved."
        )
        prompt = NAVIGATION_PROMPT.format(context=context, problem=problem, language=language)
        result = call_llm_json(SYSTEM_PROMPT, prompt)
        result["_sources"] = [c["source"] for c in chunks]
        return result
