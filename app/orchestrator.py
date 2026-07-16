"""Agent orchestrator: intent + safety routing and grounded answer assembly.

Enforces the anti-misinformation policy from the data architecture:
  1. High-risk topics are refused with a safe template (never generated).
  2. Domain questions are answered ONLY from retrieved, published FAQ chunks.
  3. A domain answer must carry at least one citation above the confidence
     threshold; otherwise the agent refuses rather than hallucinate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from . import guardrails
from .config import settings
from .llm import get_llm
from .retrieval import RetrievedChunk, search


@dataclass
class AgentResult:
    reply: str
    intent: str
    route: str  # smalltalk | faq_grounded | refused | escalated
    model: str
    confidence: float | None = None
    latency_ms: int = 0
    citations: list[tuple[str, float]] = field(default_factory=list)  # (faq_chunk_id, score)


def handle(db: Session, text: str) -> AgentResult:
    start = time.perf_counter()
    llm = get_llm()

    def finish(**kwargs) -> AgentResult:
        kwargs.setdefault("model", llm.name)
        kwargs["latency_ms"] = int((time.perf_counter() - start) * 1000)
        return AgentResult(**kwargs)

    # 1) Safety gate — high-risk topics are never answered generatively.
    if guardrails.is_high_risk(text):
        return finish(
            reply=guardrails.HIGH_RISK_RESPONSE_TH,
            intent="high_risk",
            route="refused",
        )

    intent = guardrails.classify_intent(text)

    # 2) General chat — guardrailed LLM, no grounding required.
    if intent == "smalltalk":
        return finish(
            reply=llm.generate(text, context_chunks=None),
            intent=intent,
            route="smalltalk",
        )

    # 3) Domain question — retrieve and ground.
    hits: list[RetrievedChunk] = search(
        db, text, top_k=settings.retrieval_top_k, min_score=settings.retrieval_min_score
    )
    if not hits:
        return finish(
            reply=guardrails.NO_ANSWER_RESPONSE_TH,
            intent=intent,
            route="refused",
            confidence=0.0,
        )

    context = [h.chunk.text for h in hits]
    answer = llm.generate(text, context_chunks=context)
    citations = [(h.chunk.id, round(h.score, 4)) for h in hits]
    top_score = hits[0].score

    # Append source attribution so farmers can see where the answer comes from.
    sources = sorted({h.doc.source for h in hits if h.doc.source})
    if sources:
        answer += "\n\nแหล่งข้อมูล: " + ", ".join(sources)

    return finish(
        reply=answer,
        intent=intent,
        route="faq_grounded",
        confidence=round(top_score, 4),
        citations=citations,
    )
