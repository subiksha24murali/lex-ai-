"""
Evaluation harness for LexAI. Computes metrics named in the project
proposal: retrieval accuracy and an authority/answer-content check as a
starting point. Extend TEST_SET with your own labeled question/answer
pairs (aim for 30-50 for a credible evaluation chapter in your report).

Usage:
    python -m evaluation.evaluate
"""
import json

from src.rag.pipeline import LexAIPipeline

# Add more cases as your corpus grows. expected_sources should match
# filenames in data/raw/. expected_authority_keyword is a simple substring
# check against the generated answer (case-insensitive) — a cheap proxy for
# "did the model name the right authority".
TEST_SET = [
    {
        "question": "What can I do if a shopkeeper refuses to refund a defective product?",
        "expected_sources": ["consumer_protection_overview.txt"],
        "expected_authority_keyword": "consumer",
    },
    {
        "question": "I bought a mixer that stopped working in a week, and the seller keeps ignoring me. How can I complain?",
        "expected_sources": ["consumer_protection_overview.txt"],
        "expected_authority_keyword": "consumer",
    },
    {
        "question": "A courier company lost my parcel and will not pay me back. What consumer remedy do I have?",
        "expected_sources": ["consumer_protection_overview.txt"],
        "expected_authority_keyword": "consumer",
    },
    {
        "question": "I received a suspicious link claiming to be from my bank. Where do I report it?",
        "expected_sources": ["cybercrime_reporting.txt"],
        "expected_authority_keyword": "1930",
    },
    {
        "question": "Someone used my UPI details to take money from my account. What should I do right now?",
        "expected_sources": ["cybercrime_reporting.txt"],
        "expected_authority_keyword": "1930",
    },
    {
        "question": "I am being threatened online with my private photos. How can I report this?",
        "expected_sources": ["cybercrime_reporting.txt"],
        "expected_authority_keyword": "cybercrime",
    },
    {
        "question": "My spouse has left home and we need to understand what legal options are available to us.",
        "expected_sources": ["family_law_overview.txt"],
        "expected_authority_keyword": "family",
    },
    {
        "question": "I need help understanding child custody and where to get support during a separation.",
        "expected_sources": ["family_law_overview.txt"],
        "expected_authority_keyword": "family",
    },
    {
        "question": "The police station is refusing to record my complaint. What can I do next?",
        "expected_sources": ["fir_filing_process.txt"],
        "expected_authority_keyword": "superintendent",
    },
    {
        "question": "My FIR was registered but I did not receive a copy. How can I get it?",
        "expected_sources": ["fir_filing_process.txt"],
        "expected_authority_keyword": "police",
    },
    {
        "question": "My employer has not paid my salary for two months. Where should I complain?",
        "expected_sources": ["labour_rights_overview.txt"],
        "expected_authority_keyword": "labour",
    },
    {
        "question": "I was dismissed without notice and my company is withholding my final wages. What are my options?",
        "expected_sources": ["labour_rights_overview.txt"],
        "expected_authority_keyword": "labour",
    },
    {
        "question": "My brother is trying to sell our inherited land without my consent. What should I check first?",
        "expected_sources": ["property_rights_overview.txt"],
        "expected_authority_keyword": "property",
    },
    {
        "question": "The person next door has built onto my boundary. How can I resolve this property dispute?",
        "expected_sources": ["property_rights_overview.txt"],
        "expected_authority_keyword": "property",
    },
    {
        "question": "My daughter is being denied admission under the Right to Education rules. Who can I approach?",
        "expected_sources": ["rte_education_overview.txt"],
        "expected_authority_keyword": "education",
    },
    {
        "question": "The school is asking for a fee that we cannot afford even though my child should get an RTE seat. What can I do?",
        "expected_sources": ["rte_education_overview.txt"],
        "expected_authority_keyword": "education",
    },
    {
        "question": "How can I find out why my ration card application is still pending?",
        "expected_sources": ["rti_overview.txt"],
        "expected_authority_keyword": "public information officer",
    },
    {
        "question": "I want government records about a local road project, but the office will not answer me. How do I file an RTI?",
        "expected_sources": ["rti_overview.txt"],
        "expected_authority_keyword": "public information officer",
    },
    {
        "question": "My pension has stopped and the office keeps sending me from one desk to another. Where can I get help?",
        "expected_sources": ["senior_citizens_overview.txt"],
        "expected_authority_keyword": "senior",
    },
    {
        "question": "My elderly parent is being neglected by relatives. What support or protection is available?",
        "expected_sources": ["senior_citizens_overview.txt"],
        "expected_authority_keyword": "senior",
    },
]


STRUCTURED_SECTION_LABELS = {
    "Identified Issue": ["Identified Issue", "पहचानी गई समस्या", "அடையாளம் காணப்பட்ட பிரச்சினை"],
    "Relevant Legal Information": [
        "Relevant Legal Information",
        "प्रासंगिक कानूनी जानकारी",
        "தொடர்புடைய சட்ட தகவல்கள்",
    ],
    "Your Rights as a Citizen": [
        "Your Rights as a Citizen",
        "एक नागरिक के रूप में आपके अधिकार",
        "குடிமகனாக உங்கள் உரிமைகள்",
    ],
    "Recommended Next Steps": [
        "Recommended Next Steps",
        "अनुशंसित अगले कदम",
        "பரிந்துரைக்கப்பட்ட அடுத்த படிகள்",
    ],
    "Required Documents": ["Required Documents", "आवश्यक दस्तावेज़", "தேவையான ஆவணங்கள்"],
    "Responsible Authority / Where to Go": [
        "Responsible Authority / Where to Go",
        "जिम्मेदार प्राधिकरण / कहाँ जाएँ",
        "பொறுப்பான அதிகாரம் / எங்கு செல்ல வேண்டும்",
    ],
    "Applicable Timelines (if available in context)": [
        "Applicable Timelines (if available in context)",
        "लागू समय-सीमा (यदि संदर्भ में उपलब्ध हो)",
        "பொருந்தும் காலக்கெடுக்கள் (சூழலில் இருந்தால்)",
    ],
    "Official Sources Used": [
        "Official Sources Used",
        "इस्तेमाल किए गए आधिकारिक स्रोत",
        "பயன்படுத்தப்பட்ட அதிகாரப்பூர்வ ஆதாரங்கள்",
    ],
    "Disclaimer": [
        "Disclaimer",
        "अस्वीकरण",
        "மறுப்பு",
    ],
}


def retrieval_hit_rate(pipeline: LexAIPipeline, test_set=TEST_SET) -> float:
    """Fraction of questions for which at least one expected source was retrieved."""
    hits = 0
    for case in test_set:
        chunks = pipeline.retriever.search(case["question"])
        retrieved_sources = {c["source"] for c in chunks}
        if retrieved_sources & set(case["expected_sources"]):
            hits += 1
    return hits / len(test_set)


def authority_keyword_accuracy(pipeline: LexAIPipeline, test_set=TEST_SET) -> float:
    """Fraction of answers that mention the expected responsible authority."""
    matches = 0
    for case in test_set:
        result = pipeline.answer(case["question"])
        if case["expected_authority_keyword"].lower() in result["answer"].lower():
            matches += 1
    return matches / len(test_set)


def multilingual_consistency_check(pipeline: LexAIPipeline, test_set=TEST_SET) -> dict:
    """Check that English, Hindi, and Tamil answers retain all 9 sections."""
    counts = {language: {"passed": 0, "failed": 0} for language in ("English", "Hindi", "Tamil")}

    for case in test_set:
        for language in counts:
            result = pipeline.answer(case["question"], language=language)
            answer = result["answer"]
            has_all_sections = all(
                any(label.lower() in answer.lower() for label in labels)
                for labels in STRUCTURED_SECTION_LABELS.values()
            )
            counts[language]["passed" if has_all_sections else "failed"] += 1

    return counts


if __name__ == "__main__":
    pipeline = LexAIPipeline()
    metrics = {
        "retrieval_hit_rate": retrieval_hit_rate(pipeline),
        "authority_keyword_accuracy": authority_keyword_accuracy(pipeline),
        "multilingual_consistency": multilingual_consistency_check(pipeline),
        "test_set_size": len(TEST_SET),
    }
    print(json.dumps(metrics, indent=2))
