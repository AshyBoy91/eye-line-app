"""Retrieval over published FAQ chunks (RAG).

Cosine similarity is computed in Python so the same code runs on SQLite. On
PostgreSQL with pgvector, replace `search` with an ORDER BY embedding <=> query
query for native, indexed nearest-neighbour search.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .embeddings import cosine, get_embedder
from .models import FaqChunk, FaqDoc


@dataclass
class RetrievedChunk:
    chunk: FaqChunk
    doc: FaqDoc
    score: float


def search(db: Session, query: str, top_k: int, min_score: float) -> list[RetrievedChunk]:
    embedder = get_embedder()
    q_vec = embedder.embed_one(query)
    now = datetime.now(timezone.utc)

    rows = db.execute(
        select(FaqChunk, FaqDoc)
        .join(FaqDoc, FaqChunk.faq_doc_id == FaqDoc.id)
        .where(FaqDoc.status == "published")
    ).all()

    scored: list[RetrievedChunk] = []
    for chunk, doc in rows:
        if doc.valid_from and doc.valid_from > now:
            continue
        if doc.valid_to and doc.valid_to < now:
            continue
        score = cosine(q_vec, chunk.embedding or [])
        if score >= min_score:
            scored.append(RetrievedChunk(chunk=chunk, doc=doc, score=score))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
