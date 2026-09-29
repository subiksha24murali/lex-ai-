"""Legal Education Agent for plain-language concept explanations."""
from src.rag.pipeline import LexAIPipeline


class LegalEducationAgent:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline or LexAIPipeline()

    def explain(self, question: str, language: str = "English") -> dict:
        result = self.pipeline.answer(question, language=language)
        result["agent"] = "legal_education"
        result["education_note"] = (
            "This explanation is educational legal information, not professional legal advice."
        )
        return result