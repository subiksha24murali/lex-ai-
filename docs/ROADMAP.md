# LexAI — Project Roadmap
### AI-Powered Multilingual Legal Rights and Citizen Assistance Platform (LLM + RAG)

This roadmap breaks the project into 10 phases. Each phase has a goal, concrete
tasks, and a "done when" checkpoint so you can track progress against your
project timeline / review dates.

Recommended tech stack (used in the code scaffold provided alongside this
document):

| Layer | Choice | Why |
|---|---|---|
| LLM | Anthropic API (Claude) *or* local Llama/Mistral via Ollama | Anthropic API = best quality for demos/viva; Ollama = free, offline, good for a student budget |
| Orchestration | Plain Python (no heavy framework) | Easier to explain in a viva than a black-box framework; you understand every step |
| Embeddings | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | Single model that reasonably covers English, Hindi, Tamil |
| Vector DB | ChromaDB | Simple, file-based, no server to manage |
| OCR | Tesseract (`eng+hin+tam` trained data) | Free, supports Indic scripts |
| Translation | `deep-translator` for prototype; AI4Bharat **IndicTrans2** for final system | IndicTrans2 is purpose-built for Indian languages, better quality |
| Backend | FastAPI | Async, auto-generated OpenAPI docs, easy to demo |
| Frontend | Streamlit for demo → React/Next.js for final deliverable | Streamlit = fast to build; React = more "product-like" for evaluation |
| Speech | Whisper (STT) + gTTS or Coqui TTS (TTS) | Well-documented, works offline |

---

## Phase 1 — Scope Lock & Requirement Finalization (Week 1)
- Finalize the exact list of legal domains you'll cover for v1 (recommend
  starting narrow: Consumer Protection, RTI, FIR/Police complaint process,
  Cyber crime reporting, Basic labour rights — expand later).
- Write your SRS (Software Requirements Specification): functional +
  non-functional requirements, actors (citizen, admin), constraints
  (not legal advice, disclaimer requirements).
- **Done when:** SRS approved by guide; scope frozen for v1.

## Phase 2 — Data Collection & Legal Corpus Building (Weeks 2–4)
- Collect **official** source documents only:
  - Constitution of India — `legislative.gov.in`
  - Bare Acts — `indiacode.nic.in` (Consumer Protection Act 2019, IT Act 2000,
    Code of Criminal Procedure, Labour Codes, RTI Act 2005)
  - Cybercrime guidance — `cybercrime.gov.in`
  - Consumer helpline — `consumerhelpline.gov.in`
  - National/State Legal Services Authority (NALSA) FAQs
- Convert to clean `.txt`/`.pdf` files, one per Act/topic, and drop them in
  `data/raw/`. Keep a spreadsheet mapping filename → official source URL →
  last-updated date (you'll need this for your source-citation requirement
  and for your report's "data sources" section).
- **Done when:** you have 15–30 source documents covering your Phase-1 scope.

## Phase 3 — Knowledge Base / Vector Store (Week 5)
- Run the ingestion scripts (`src/ingestion/loaders.py` then
  `src/ingestion/build_vector_store.py`) provided in the scaffold.
- Tune chunk size/overlap for legal text (legal clauses are dense — smaller
  chunks with overlap tend to retrieve better than huge chunks).
- **Done when:** you can run a test query and get back relevant chunks with
  correct source attribution.

## Phase 4 — Core RAG Pipeline (Weeks 6–7)
- Wire retrieval → structured prompt → LLM using `src/rag/pipeline.py`.
- Lock the **structured answer schema** (issue, legal info, rights, next
  steps, documents, authority, timeline, sources, disclaimer) — this is
  already encoded in `src/rag/prompts.py`.
- Test on 15–20 hand-written questions across your legal domains.
- **Done when:** answers are consistently structured, grounded, and cite
  real sources from your corpus.

## Phase 5 — Multilingual Layer (Weeks 8–9)
- Start with `deep-translator` (Google backend) for a working prototype.
- For the final system, integrate **IndicTrans2** for higher-quality
  Hindi/Tamil, since it's built specifically for Indian languages.
- Decide on strategy: (a) translate user query → English → retrieve/generate
  in English → translate back, or (b) ask the LLM to answer directly in the
  target language using multilingual embeddings for retrieval. Try both and
  report on quality (this is a great evaluation section for your report).
- **Done when:** the same question in English, Hindi, and Tamil returns
  answers of comparable quality/structure.

## Phase 6 — OCR & Document Analysis Module (Weeks 10–11)
- Use `src/ocr/document_analysis.py` to extract text from uploaded FIRs,
  rental agreements, employment contracts, notices.
- Feed extracted text into the same grounded LLM call for summarization,
  clause explanation, and Q&A.
- Handle OCR noise (misread characters) — add a cleanup step if accuracy is
  low on scanned documents.
- **Done when:** you can upload a sample scanned document and get an
  accurate plain-language summary + flagged clauses.

## Phase 7 — Scam & Fraud Message Analysis (Week 12)
- Use `src/scam_detection/analyzer.py`: rule-based pre-filter (fast, catches
  obvious patterns) + LLM reasoning pass (nuance, explanation).
- Build a small labeled test set of real-world scam message examples (UPI
  fraud, fake job offers, digital arrest scams, phishing) — this becomes
  your evaluation set for precision/recall.
- **Done when:** the module correctly flags risk level and gives an accurate
  "where to report" answer (cybercrime.gov.in, 1930 helpline, etc.).

## Phase 8 — Speech Interface (Week 13, optional/stretch)
- Whisper for speech-to-text input.
- gTTS/Coqui for reading answers aloud.
- Useful for users who can't type easily — mention this explicitly in your
  report as an accessibility contribution.
- **Done when:** a spoken question produces a spoken, structured answer.

## Phase 9 — Frontend, API & Integration (Weeks 14–15)
- `src/api/main.py` (FastAPI) already exposes `/ask`, `/document/analyze`,
  `/scam/check`, `/translate`.
- Use `frontend/streamlit_app.py` for quick demos; build a proper React UI
  if you want a more "shippable" final deliverable (chat interface, document
  upload, language switcher, complaint/draft generator, checklist view).
- **Done when:** a user can complete an end-to-end flow (ask → get structured
  answer → download checklist/draft) through the UI, not just the API.

## Phase 10 — Evaluation, Documentation & Report (Weeks 16–18)
Evaluate across the dimensions named in your proposal:

| Metric | How to measure |
|---|---|
| Retrieval accuracy | Hit rate / precision@k on a labeled question→source test set (`evaluation/evaluate.py`) |
| Answer relevance | Human rating (1–5) by a small panel on a held-out question set |
| Factual grounding / hallucination rate | % of claims in the answer traceable to retrieved context (manual or LLM-as-judge audit) |
| Multilingual performance | Compare structure/quality of EN vs HI vs TA answers to the same question |
| Response usefulness | User study: did the answer let them know what to do next? |
| Document-analysis performance | Accuracy of clause explanation vs a human-reviewed ground truth on sample documents |
| User satisfaction | Simple post-task survey (System Usability Scale is a good standard instrument) |

- Write up methodology, results, limitations (e.g., not a substitute for a
  lawyer, coverage limited to included Acts, translation quality variance).
- Package the final report, PPT, and demo video.
- **Done when:** report + evaluation results + working demo are ready for
  submission/viva.

---

## Suggested Timeline (18 weeks / ~4.5 months)
Phases 1–3: Weeks 1–5 · Phase 4: Weeks 6–7 · Phase 5: Weeks 8–9 ·
Phase 6: Weeks 10–11 · Phase 7: Week 12 · Phase 8: Week 13 (optional) ·
Phase 9: Weeks 14–15 · Phase 10: Weeks 16–18.
Compress phases 1–4 if your deadline is shorter — they're the backbone the
rest depends on.

## Responsible-AI Notes for Your Report
- Every answer must carry the "not a substitute for a lawyer" disclaimer —
  already built into the prompt template.
- Never let the system state something as fact if it wasn't retrieved from
  the corpus — this is your hallucination-reduction claim, and your
  evaluation should test it directly (ask questions outside your corpus and
  confirm the system says so instead of guessing).
- Log low-confidence/out-of-scope queries — useful both as a safety
  mechanism and as evidence for your evaluation chapter.
