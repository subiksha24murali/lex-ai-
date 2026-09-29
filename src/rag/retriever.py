"""
Semantic retriever over the ChromaDB collection built by
src/ingestion/build_vector_store.py.
"""
from typing import List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import COLLECTION_NAME, EMBEDDING_MODEL, TOP_K, VECTOR_DB_DIR


class Retriever:
    def __init__(self):
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self._client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def search(
        self, query: str, top_k: int = TOP_K, category: Optional[str] = None
    ) -> List[dict]:
        query_embedding = self._model.encode([query]).tolist()
        where = {"category": category} if category else None

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where,
        )

        hits = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            hits.append(
                {
                    "text": doc,
                    "source": meta.get("source"),
                    "category": meta.get("category"),
                    "authority": meta.get("authority", ""),
                    "title": meta.get("title", ""),
                    "legal_reference": meta.get("legal_reference", ""),
                    "effective_date": meta.get("effective_date", ""),
                    "source_url": meta.get("source_url", ""),
                    "imported_at": meta.get("imported_at", ""),
                    "score": round(1 - dist, 3),
                }
            )
        return hits
