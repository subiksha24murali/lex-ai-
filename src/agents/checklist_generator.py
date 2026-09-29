"""
Document Checklist Agent.

Turns a citizen's situation into a grounded list of required and optional
documents, with practical guidance for obtaining difficult documents.
"""
from src.common.json_llm import call_llm_json
from src.rag.prompts import SYSTEM_PROMPT
from src.rag.retriever import Retriever


CHECKLIST_PROMPT = """Context (official sources, may be incomplete):
{context}

A citizen describes this situation: "{situation}"

Respond with ONLY a JSON object (no markdown, no commentary, no code fences), \
in {language}, with exactly these keys:

{{
  "situation_summary": "short summary of the citizen's situation",
  "required_documents": ["document 1", "document 2"],
  "optional_documents": ["document 1", "document 2"],
  "notes": "short guidance on where/how to obtain any hard-to-get document"
}}
"""


def generate_checklist(situation: str, language: str = "English") -> dict:
    retriever = Retriever()
    chunks = retriever.search(situation)
    context = (
        "\n\n---\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in chunks)
        or "No relevant context was retrieved."
    )
    prompt = CHECKLIST_PROMPT.format(context=context, situation=situation, language=language)
    result = call_llm_json(SYSTEM_PROMPT, prompt)
    result["_sources"] = [c["source"] for c in chunks]
    return result