"""
FastAPI backend exposing LexAI's core capabilities over HTTP.

Run with:
    uvicorn src.api.main:app --reload

Interactive API docs will be at http://localhost:8000/docs
"""
import os
import shutil
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, Response, UploadFile
from pydantic import BaseModel

from src.agents.checklist_generator import generate_checklist
from src.agents.complaint_drafting import generate_complaint
from src.agents.service_navigation import ServiceNavigationAgent
from src.agents.orchestrator import LexAIOrchestrator
from src.auth.lawyer_service import (
    add_case_document,
    create_consultation_request,
    create_lawyer_profile,
    list_case_documents,
    get_case_document,
    list_citizen_requests,
    list_lawyer_requests,
    list_messages,
    schedule_appointment,
    send_message,
    update_request_status,
)
from src.multilingual.translate import translate_text
from src.ocr.document_analysis import analyze_document, ask_about_document
from src.rag.pipeline import LexAIPipeline
from src.scam_detection.analyzer import analyze_message

app = FastAPI(
    title="LexAI",
    description="AI-powered multilingual legal rights and citizen assistance platform",
    version="0.1.0",
)

pipeline = LexAIPipeline()
nav_agent = ServiceNavigationAgent()
orchestrator = LexAIOrchestrator(pipeline=pipeline, navigation_agent=nav_agent)


class AskRequest(BaseModel):
    question: str
    language: str = "English"
    category: Optional[str] = None


class LawyerProfileRequest(BaseModel):
    user_id: int
    bar_council_number: str
    practice_areas: str
    languages: str
    bio: str = ""


class ConsultationRequest(BaseModel):
    citizen_id: int
    summary: str
    details: str
    practice_area: str
    language: str = "English"
    lawyer_id: Optional[int] = None


class RequestStatusUpdate(BaseModel):
    lawyer_id: int
    status: str


class MessageRequest(BaseModel):
    sender_id: int
    body: str


class AppointmentRequest(BaseModel):
    citizen_id: int
    lawyer_id: int
    scheduled_for: str


@app.post("/lawyers/profile")
def lawyer_profile(req: LawyerProfileRequest):
    create_lawyer_profile(req.user_id, req.bar_council_number, req.practice_areas, req.languages, req.bio)
    return {"status": "pending_verification"}


@app.get("/lawyers")
def lawyers(practice_area: Optional[str] = None, language: Optional[str] = None):
    from src.auth.lawyer_service import list_lawyers

    return {"lawyers": list_lawyers(practice_area, language)}


@app.post("/consultations")
def consultation(req: ConsultationRequest):
    request_id = create_consultation_request(
        req.citizen_id, req.summary, req.details, req.practice_area, req.language, req.lawyer_id
    )
    return {"request_id": request_id, "status": "pending"}


@app.get("/consultations/citizen/{citizen_id}")
def citizen_consultations(citizen_id: int):
    return {"requests": list_citizen_requests(citizen_id)}


@app.get("/consultations/lawyer/{lawyer_id}")
def lawyer_consultations(lawyer_id: int):
    return {"requests": list_lawyer_requests(lawyer_id)}


@app.patch("/consultations/{request_id}")
def consultation_status(request_id: int, req: RequestStatusUpdate):
    update_request_status(request_id, req.lawyer_id, req.status)
    return {"request_id": request_id, "status": req.status}


@app.post("/consultations/{request_id}/messages")
def consultation_message(request_id: int, req: MessageRequest):
    return {"message_id": send_message(request_id, req.sender_id, req.body)}


@app.get("/consultations/{request_id}/messages")
def consultation_messages(request_id: int):
    return {"messages": list_messages(request_id)}


@app.post("/consultations/{request_id}/appointments")
def consultation_appointment(request_id: int, req: AppointmentRequest):
    return {"appointment_id": schedule_appointment(request_id, req.citizen_id, req.lawyer_id, req.scheduled_for)}


@app.get("/consultations/{request_id}/documents")
def consultation_documents(request_id: int):
    return {"documents": list_case_documents(request_id)}


@app.get("/case-documents/{document_id}")
def case_document(document_id: int):
    document = get_case_document(document_id)
    if document is None:
        return Response(status_code=404)
    return Response(content=document["content"], media_type=document["mime_type"], headers={
        "Content-Disposition": f"attachment; filename=\"{document['file_name']}\""
    })


@app.post("/consultations/{request_id}/documents")
async def consultation_document(request_id: int, uploader_id: int = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    document_id = add_case_document(
        request_id,
        uploader_id,
        file.filename or "uploaded-document",
        file.content_type or "application/octet-stream",
        content,
    )
    return {"document_id": document_id}


@app.post("/ask")
def ask(req: AskRequest):
    """Ask a legal/rights/procedure question and get a structured, grounded answer."""
    return pipeline.answer(req.question, language=req.language, category=req.category)


@app.post("/orchestrate")
def orchestrate(req: AskRequest):
    """Classify a request and invoke the selected specialized agent."""
    return orchestrator.handle(req.question, language=req.language)


@app.post("/document/analyze")
async def document_analyze(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    language: str = Form("English"),
):
    """Upload a scanned/photographed legal document (FIR, agreement, notice, etc.)."""
    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        return analyze_document(tmp_path, doc_type=doc_type, language=language)
    finally:
        os.remove(tmp_path)


class DocumentQuestionRequest(BaseModel):
    document_text: str
    question: str
    language: str = "English"


@app.post("/document/ask")
def document_ask(req: DocumentQuestionRequest):
    """Ask a follow-up question about a document already analyzed via /document/analyze."""
    return {"answer": ask_about_document(req.document_text, req.question, language=req.language)}


class ComplaintRequest(BaseModel):
    situation: str
    language: str = "English"


@app.post("/complaint/draft")
def complaint_draft(req: ComplaintRequest):
    """Generate a structured complaint (consumer, police, cybercrime, labour, RTI, etc.)."""
    return generate_complaint(req.situation, language=req.language)


class NavigationRequest(BaseModel):
    problem: str
    language: str = "English"


@app.post("/service/navigate")
def service_navigate(req: NavigationRequest):
    """Get a step-by-step government service navigation plan for a citizen's problem."""
    return nav_agent.navigate(req.problem, language=req.language)


class ChecklistRequest(BaseModel):
    situation: str
    language: str = "English"


@app.post("/checklist/generate")
def checklist_generate(req: ChecklistRequest):
    """Generate a grounded document checklist for a citizen's situation."""
    return generate_checklist(req.situation, language=req.language)


class ScamCheckRequest(BaseModel):
    message: str
    language: str = "English"


@app.post("/scam/check")
def scam_check(req: ScamCheckRequest):
    """Analyze a suspicious SMS/WhatsApp/email message for scam risk."""
    return analyze_message(req.message, language=req.language)


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


@app.post("/translate")
def translate(req: TranslateRequest):
    return {"translated_text": translate_text(req.text, req.target_lang)}


@app.get("/health")
def health():
    return {"status": "ok"}
