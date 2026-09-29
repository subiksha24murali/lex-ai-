"""
OCR + document understanding module.

Pipeline: PDF/image -> extracted text (Tesseract, with Hindi/Tamil trained
data) -> summarization / clause explanation / risk flagging, reusing the
same grounded LLM call used by the RAG pipeline.

Requires (system packages, not just pip):
    sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam poppler-utils
"""
from PIL import Image
from pdf2image import convert_from_path
import pytesseract

from src.rag.pipeline import _call_llm
from src.rag.prompts import SYSTEM_PROMPT

VALID_DOC_TYPES = {
    "fir",
    "rental_agreement",
    "employment_contract",
    "bank_notice",
    "government_notice",
    "general",
}


def extract_text(file_path: str, languages: str = "eng+hin+tam") -> str:
    """
    languages: tesseract language codes, e.g. 'eng+hin+tam'.
    Requires the corresponding tesseract-ocr-{lang} packages to be installed.
    """
    if file_path.lower().endswith(".pdf"):
        pages = convert_from_path(file_path)
        text = "\n".join(pytesseract.image_to_string(p, lang=languages) for p in pages)
    else:
        text = pytesseract.image_to_string(Image.open(file_path), lang=languages)
    return text.strip()


def analyze_document(file_path: str, doc_type: str = "general", language: str = "English") -> dict:
    """
    doc_type: one of VALID_DOC_TYPES (fir, rental_agreement,
    employment_contract, bank_notice, government_notice, general).
    """
    if doc_type not in VALID_DOC_TYPES:
        doc_type = "general"

    raw_text = extract_text(file_path)

    user_prompt = f"""Below is OCR-extracted text from a citizen-uploaded {doc_type} document. \
The OCR may contain minor recognition errors.

Document text:
{raw_text}

Respond in {language} with:
1. Document Type & Purpose (in simple terms)
2. Plain-Language Summary
3. Key Clauses Explained (list each important clause and what it means)
4. Anything Concerning or Unusual (flag risky/unfair clauses if present)
5. Suggested Next Steps for the Citizen
6. Disclaimer (this is general information, not legal advice)
"""
    analysis = _call_llm(SYSTEM_PROMPT, user_prompt)
    return {"extracted_text": raw_text, "analysis": analysis}


def ask_about_document(document_text: str, question: str, language: str = "English") -> str:
    """
    Answers a follow-up question about a document already analyzed by
    analyze_document() (e.g. "Can my landlord increase the rent?"), grounded
    in that document's extracted text.
    """
    user_prompt = f"""Below is the text of a document the citizen uploaded earlier.

Document text:
{document_text}

The citizen now asks: "{question}"

Answer in {language}, based on the document content above. If the document \
does not contain enough information to answer, say so clearly instead of \
guessing. Keep the answer concise and end with a one-line reminder that \
this is general information, not legal advice.
"""
    return _call_llm(SYSTEM_PROMPT, user_prompt)
