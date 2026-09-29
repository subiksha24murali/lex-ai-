"""Lightweight, measurable post-generation evidence checks."""
import re
from typing import List


_STOP_WORDS = {
    "about", "after", "also", "because", "being", "could", "from", "have",
    "into", "more", "should", "that", "their", "there", "these", "they",
    "this", "through", "under", "were", "which", "with", "would", "your",
}


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
    return {word for word in words if word not in _STOP_WORDS}


def _claims(answer: str) -> List[str]:
    claims = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer):
        sentence = sentence.strip(" -*#\t")
        if len(_terms(sentence)) >= 5 and not sentence.endswith(":"):
            claims.append(sentence)
    return claims


def evaluate_grounding(answer: str, context_chunks: List[dict]) -> dict:
    """Return claim support estimates without presenting them as legal truth."""
    evidence_terms = [_terms(chunk.get("text", "")) for chunk in context_chunks]
    claims = _claims(answer)
    supported = []
    for claim in claims:
        claim_terms = _terms(claim)
        best_overlap = max(
            (len(claim_terms & terms) / len(claim_terms) for terms in evidence_terms),
            default=0.0,
        )
        supported.append({
            "claim": claim,
            "supported": best_overlap >= 0.25,
            "evidence_overlap": round(best_overlap, 3),
        })
    supported_count = sum(item["supported"] for item in supported)
    return {
        "evaluated_claims": len(supported),
        "supported_claims": supported_count,
        "grounded_claim_rate": round(supported_count / len(supported), 3) if supported else 0.0,
        "claims": supported,
        "method": "token-overlap screening; requires human or entailment-model review",
    }