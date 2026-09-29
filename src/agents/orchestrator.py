"""Deterministic first-pass router for LexAI's six core agents."""
from dataclasses import dataclass
from typing import Optional

from src.agents.legal_education import LegalEducationAgent
from src.agents.service_navigation import ServiceNavigationAgent
from src.rag.pipeline import LexAIPipeline
from src.scam_detection.analyzer import analyze_message
from src.agents.complaint_drafting import generate_complaint


@dataclass
class RouteDecision:
    intent: str
    agent: str
    reason: str


class LexAIOrchestrator:
    def __init__(self, pipeline=None, navigation_agent=None, education_agent=None):
        self.pipeline = pipeline or LexAIPipeline()
        self.navigation_agent = navigation_agent or ServiceNavigationAgent()
        self.education_agent = education_agent or LegalEducationAgent(self.pipeline)

    def classify(self, query: str) -> RouteDecision:
        text = query.lower()
        if any(term in text for term in ("scam", "fraud", "phishing", "otp", "suspicious message")):
            return RouteDecision("scam_detection", "scam_detection", "message-risk language detected")
        if any(term in text for term in ("complaint", "complain", "draft a letter", "write a complaint")):
            return RouteDecision("complaint_drafting", "complaint_drafting", "complaint-writing intent detected")
        if any(term in text for term in ("where do i go", "which department", "official portal", "how do i file")):
            return RouteDecision("service_navigation", "service_navigation", "government-procedure intent detected")
        if any(term in text for term in ("what does", "meaning of", "explain the term", "what is a")):
            return RouteDecision("legal_education", "legal_education", "concept-explanation intent detected")
        return RouteDecision("legal_advice_information", "legal_advisor", "general legal-information intent")

    def handle(self, query: str, language: str = "English") -> dict:
        decision = self.classify(query)
        if decision.agent == "scam_detection":
            result = analyze_message(query, language=language)
        elif decision.agent == "complaint_drafting":
            result = generate_complaint(query, language=language)
        elif decision.agent == "service_navigation":
            result = self.navigation_agent.navigate(query, language=language)
        elif decision.agent == "legal_education":
            result = self.education_agent.explain(query, language=language)
        else:
            result = self.pipeline.answer(query, language=language)
        return {
            "routing": {"intent": decision.intent, "agent": decision.agent, "reason": decision.reason},
            "result": result,
        }