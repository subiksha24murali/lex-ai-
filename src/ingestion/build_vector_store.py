"""
Embeds every chunk produced by loaders.py and stores it in a persistent
ChromaDB collection. Run this once after adding/updating files in data/raw.

Usage:
    python -m src.ingestion.loaders          # (re)generate chunks.jsonl
    python -m src.ingestion.build_vector_store
"""
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    PROCESSED_DATA_DIR,
    VECTOR_DB_DIR,
)


def build_vector_store():
    chunks_path = os.path.join(PROCESSED_DATA_DIR, "chunks.jsonl")
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(
            "chunks.jsonl not found. Run `python -m src.ingestion.loaders` first."
        )

    with open(chunks_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    batch_size = 64
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        texts = [r["text"] for r in batch]
        ids = [r["id"] for r in batch]
        metadatas = [
            {
                "source": r["source"],
                "category": r["category"],
                "authority": r.get("authority", ""),
                "title": r.get("title", ""),
                "legal_reference": r.get("legal_reference", ""),
                "effective_date": r.get("effective_date", ""),
                "source_url": r.get("source_url", ""),
                "imported_at": r.get("imported_at", ""),
            }
            for r in batch
        ]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"Indexed {min(start + batch_size, len(records))}/{len(records)} chunks")

    print(f"Vector store ready at {VECTOR_DB_DIR} (collection: {COLLECTION_NAME})")


if __name__ == "__main__":
    build_vector_store()
