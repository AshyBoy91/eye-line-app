"""Conversation persistence: farmer/session resolution and message logging."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .models import Citation, Consent, Farmer, Message, Session
from .orchestrator import AgentResult

SESSION_IDLE_SECONDS = 30 * 60


def get_or_create_farmer(db: DbSession, line_user_id: str) -> Farmer:
    farmer = db.scalar(select(Farmer).where(Farmer.line_user_id == line_user_id))
    if farmer:
        return farmer
    farmer = Farmer(line_user_id=line_user_id)
    db.add(farmer)
    db.flush()
    # Record baseline service consent captured at onboarding (PDPA, purpose-based).
    db.add(Consent(farmer_id=farmer.id, purpose="service", granted=True, version="1.0"))
    return farmer


def get_active_session(db: DbSession, farmer: Farmer) -> Session:
    now = datetime.now(timezone.utc)
    latest = db.scalar(
        select(Session)
        .where(Session.farmer_id == farmer.id)
        .order_by(Session.last_activity_at.desc())
    )
    if latest is not None:
        last = latest.last_activity_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() <= SESSION_IDLE_SECONDS:
            latest.last_activity_at = now
            return latest
    session = Session(farmer_id=farmer.id, channel="line", last_activity_at=now)
    db.add(session)
    db.flush()
    return session


def is_duplicate(db: DbSession, line_message_id: str | None) -> bool:
    if not line_message_id:
        return False
    existing = db.scalar(
        select(Message).where(Message.line_message_id == line_message_id)
    )
    return existing is not None


def log_inbound(db: DbSession, session: Session, text: str, line_message_id: str | None) -> Message:
    msg = Message(
        session_id=session.id,
        direction="inbound",
        role="user",
        content=text,
        content_type="text",
        line_message_id=line_message_id,
    )
    db.add(msg)
    db.flush()
    return msg


def log_outbound(db: DbSession, session: Session, result: AgentResult) -> Message:
    msg = Message(
        session_id=session.id,
        direction="outbound",
        role="agent",
        content=result.reply,
        content_type="text",
        intent=result.intent,
        route=result.route,
        model=result.model,
        confidence=result.confidence,
        latency_ms=result.latency_ms,
    )
    db.add(msg)
    db.flush()
    for chunk_id, score in result.citations:
        db.add(Citation(message_id=msg.id, faq_chunk_id=chunk_id, score=score))
    return msg
