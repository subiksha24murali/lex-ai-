"""
Loads raw legal source documents (.txt, .pdf) from data/raw, cleans them,
and splits them into overlapping word chunks ready for embedding.

Each chunk carries metadata (source file, category) so the RAG pipeline can
cite official sources in its structured answer.

Usage:
    python -m src.ingestion.loaders
"""
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

from pypdf import PdfReader

from src.config import CHUNK_OVERLAP, CHUNK_SIZE, PROCESSED_DATA_DIR, RAW_DATA_DIR, SOURCE_METADATA_PATH

# Map filename -> human-readable legal category. Extend this as you add
# more source documents. Files not listed default to category "General".
CATEGORY_MAP = {
    "consumer_protection_overview.txt": "Consumer Rights",
    "fir_filing_process.txt": "Police & FIR",
    "rti_overview.txt": "Right to Information",
    "cybercrime_reporting.txt": "Cyber Crime",
    "labour_rights_overview.txt": "Labour Rights",
    "rte_education_overview.txt": "Right to Education",
    "property_rights_overview.txt": "Property Rights",
   "family_law_overview.txt": "Family Law",
   "senior_citizens_overview.txt": "Senior Citizens' Rights",
}


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    category: str
    authority: str = ""
    title: str = ""
    legal_reference: str = ""
    effective_date: str = ""
    source_url: str = ""
    imported_at: str = ""


def _read_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    words = text.split(" ")
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        piece = " ".join(words[start:end])
        if piece.strip():
            chunks.append(piece)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def load_and_chunk_corpus(category_map: Optional[dict] = None) -> List[Chunk]:
    """
    Walk data/raw, load every .txt/.pdf file, chunk it, and return a list of
    Chunk objects. Also writes data/processed/chunks.jsonl for the next
    pipeline stage (build_vector_store.py).
    """
    category_map = {**CATEGORY_MAP, **(category_map or {})}
    source_metadata = {}
    if os.path.exists(SOURCE_METADATA_PATH):
        with open(SOURCE_METADATA_PATH, "r", encoding="utf-8") as metadata_file:
            source_metadata = json.load(metadata_file)
    all_chunks: List[Chunk] = []

    if not os.path.isdir(RAW_DATA_DIR):
        raise FileNotFoundError(
            f"{RAW_DATA_DIR} does not exist. Add official source documents there first."
        )

    files = sorted(
        f for f in os.listdir(RAW_DATA_DIR) if f.endswith((".txt", ".pdf"))
    )
    if not files:
        raise FileNotFoundError(
            f"No .txt or .pdf files found in {RAW_DATA_DIR}. "
            "Add legal source documents before running ingestion."
        )

    for fname in files:
        fpath = os.path.join(RAW_DATA_DIR, fname)
        raw = _read_pdf(fpath) if fname.endswith(".pdf") else _read_txt(fpath)

        text = _clean(raw)
        pieces = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        category = category_map.get(fname, "General")
        metadata = source_metadata.get(fname, {})
        imported_at = metadata.get("imported_at") or datetime.now(timezone.utc).date().isoformat()

        for i, piece in enumerate(pieces):
            all_chunks.append(Chunk(
                id=f"{fname}-{i}", text=piece, source=fname, category=category,
                authority=metadata.get("authority", ""), title=metadata.get("title", ""),
                legal_reference=metadata.get("legal_reference", ""),
                effective_date=metadata.get("effective_date", ""),
                source_url=metadata.get("source_url", ""), imported_at=imported_at,
            ))

    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    out_path = os.path.join(PROCESSED_DATA_DIR, "chunks.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    return all_chunks


if __name__ == "__main__":
    chunks = load_and_chunk_corpus()
    print(f"Loaded and chunked {len(chunks)} chunks from {RAW_DATA_DIR}")
    print(f"Written to {os.path.join(PROCESSED_DATA_DIR, 'chunks.jsonl')}")
