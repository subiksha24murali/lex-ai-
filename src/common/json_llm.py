"""
Shared helper for agents that need the LLM to return structured JSON
instead of free-form markdown (Complaint Drafting, Service Navigation).
"""
import json
import re

from src.rag.pipeline import _call_llm


def call_llm_json(system: str, user: str) -> dict:
    """
    Calls the LLM and attempts to parse its response as JSON. Strips
    accidental markdown code fences (some models wrap JSON in ```json ...```
    even when told not to). On parse failure, returns the raw text under
    "_raw" with "_parse_error": True so the caller can show something
    reasonable instead of crashing.
    """
    raw = _call_llm(system, user)
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"_raw": raw, "_parse_error": True}
