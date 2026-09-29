"""
Core RAG pipeline: retrieve -> build grounded prompt -> call LLM -> return a
structured, source-grounded answer.

Usage:
    python -m src.rag.pipeline
"""
from typing import Optional

from src.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    LLM_PROVIDER,
    MULTILINGUAL_STRATEGY,
    OLLAMA_HOST,
    OLLAMA_MODEL,
)
from src.rag.prompts import SYSTEM_PROMPT, build_prompt
from src.rag.retriever import Retriever
from src.rag.grounding import evaluate_grounding

_LANG_CODE = {"English": "en", "Hindi": "hi", "Tamil": "ta"}


def _call_anthropic(system: str, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_ollama(system: str, user: str) -> str:
    import requests

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    resp = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _call_llm(system: str, user: str) -> str:
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system, user)
    if LLM_PROVIDER == "ollama":
        return _call_ollama(system, user)
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")


class LexAIPipeline:
    def __init__(self):
        self.retriever = Retriever()

    def answer(
        self, question: str, language: str = "English", category: Optional[str] = None
    ) -> dict:
        chunks = self.retriever.search(question, category=category)

        use_translation_fallback = (
            language != "English" and MULTILINGUAL_STRATEGY == "translate_output"
        )

        if use_translation_fallback:
            # Generate the full structured answer in English first (much more
            # reliable for a small local model), then translate the finished
            # text into the requested language.
            prompt = build_prompt(question, chunks, language="English")
            answer_en = _call_llm(SYSTEM_PROMPT, prompt)
            lang_code = _LANG_CODE.get(language)
            if lang_code and lang_code != "en":
                from src.multilingual.translate import translate_text

                answer_text = translate_text(answer_en, lang_code)
            else:
                answer_text = answer_en
        else:
            prompt = build_prompt(question, chunks, language=language)
            answer_text = _call_llm(SYSTEM_PROMPT, prompt)

        return {
            "question": question,
            "language": language,
            "answer": answer_text,
            "retrieved_sources": chunks,
            "grounding": evaluate_grounding(answer_text, chunks),
        }


if __name__ == "__main__":
    pipeline = LexAIPipeline()
    result = pipeline.answer(
        "What should I do if a shopkeeper refuses to refund a defective product?"
    )
    print(result["answer"])
