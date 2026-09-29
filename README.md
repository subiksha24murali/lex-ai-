# LexAI

AI-Powered Multilingual Legal Rights and Citizen Assistance Platform using
LLMs and Retrieval-Augmented Generation (RAG).

**Educational legal information system — not a substitute for a lawyer.**

See `docs/ROADMAP.md` for the full phased project plan.

## Project Structure

```
lexai/
├── data/
│   ├── raw/              # Official source documents go here (.txt / .pdf)
│   ├── processed/        # Auto-generated chunked corpus (chunks.jsonl)
│   └── vector_store/     # Auto-generated ChromaDB persistent store
├── src/
│   ├── config.py         # All settings (env-var driven)
│   ├── ingestion/        # Load, clean, chunk, and embed source documents
│   ├── rag/               # Retriever, prompt templates, RAG pipeline
│   ├── multilingual/     # Translation wrapper (EN/HI/TA)
│   ├── ocr/               # Document OCR + analysis (FIRs, agreements, notices)
│   ├── scam_detection/   # Scam/fraud message analysis
│   └── api/               # FastAPI backend
├── frontend/
│   └── streamlit_app.py  # Quick demo UI
├── evaluation/
│   └── evaluate.py       # Retrieval accuracy / answer-quality metrics
├── docs/
│   └── ROADMAP.md        # Full phased project roadmap
├── requirements.txt
└── .env.example
```

## Setup

1. **Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **System dependencies for OCR** (skip if you're not building Phase 6 yet)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam poppler-utils
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # then edit .env and add your ANTHROPIC_API_KEY
   # (or set LLM_PROVIDER=ollama to use a free local model instead)
   ```

4. **Add real legal source documents**
   The `data/raw/` folder currently contains placeholder demo files clearly
   marked `[DEMO PLACEHOLDER CONTENT]` so you can test the pipeline
   end-to-end immediately. Before using this for anything beyond a demo,
   replace/supplement them with real official texts from indiacode.nic.in,
   legislative.gov.in, and cybercrime.gov.in (see `docs/ROADMAP.md` Phase 2).

## Deploying to Streamlit Community Cloud

Set the app entrypoint to `frontend/streamlit_app.py` when creating the
Streamlit Community Cloud app. Do not upload `.env` or commit API keys. Add
secrets in the app's **Settings > Secrets** panel instead, for example:

```toml
ANTHROPIC_API_KEY = "your-anthropic-key"
LLM_PROVIDER = "anthropic"
ANTHROPIC_MODEL = "claude-sonnet-5"
```

`src/config.py` reads normal environment variables first (including values
from a local `.env`), then falls back to `st.secrets` when running on
Streamlit Cloud. The equivalent lookup pattern is:

```python
def _setting(name, default=""):
   value = os.getenv(name)
   if value is not None:
      return value
   try:
      return st.secrets.get(name, default)
   except Exception:
      return default
```

The generated vector store and processed chunks are excluded from Git. Build
them during setup or provide the required data through the deployment process.

## Running the System

**1. Build the knowledge base** (run whenever you add/update files in `data/raw/`):
```bash
python -m src.ingestion.loaders
python -m src.ingestion.build_vector_store
```

**2. Try the pipeline directly:**
```bash
python -m src.rag.pipeline
```

**3. Run the API backend:**
```bash
uvicorn src.api.main:app --reload
# Docs at http://localhost:8000/docs
```

**4. Run the demo UI:**
```bash
streamlit run frontend/streamlit_app.py
```

**5. Run the evaluation harness:**
```bash
python -m evaluation.evaluate
```

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/ask` | POST | Ask a legal/rights/procedure question |
| `/document/analyze` | POST | Upload and analyze a scanned legal document |
| `/scam/check` | POST | Analyze a suspicious message for scam risk |
| `/translate` | POST | Translate text between EN/HI/TA |
| `/health` | GET | Health check |

## Notes on Using a Free LLM Instead of a Paid API

If you don't have Anthropic API credits, install [Ollama](https://ollama.com),
pull a model (`ollama pull llama3.1`), set `LLM_PROVIDER=ollama` in `.env`,
and everything else works unchanged — `src/rag/pipeline.py` already
supports both providers.

## Next Steps

Follow `docs/ROADMAP.md` starting from Phase 2 (real data collection) —
Phases 1, 3, and 4's code scaffolding is already in place here.
