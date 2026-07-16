"""ORM models mapping the data architecture entities.

UUID primary keys are stored as strings for portability between SQLite (local dev)
and PostgreSQL (production). Embeddings are stored as JSON-encoded float arrays so
the same code runs on SQLite; on PostgreSQL you can migrate `faq_chunk.embedding`
to a native pgvector column.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Farmer(Base):
    __tablename__ = "farmer"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    line_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_lang: Mapped[str] = mapped_column(String(8), default="th")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|blocked|deleted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_briefing_date: Mapped["date | None"] = mapped_column(Date, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="farmer")
    consents: Mapped[list["Consent"]] = relationship(back_populates="farmer")


class Consent(Base):
    __tablename__ = "consent"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmer.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # service|analytics|contact
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(16), default="1.0")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    farmer: Mapped["Farmer"] = relationship(back_populates="consents")


class Session(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    farmer_id: Mapped[str] = mapped_column(ForeignKey("farmer.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="line")
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    farmer: Mapped["Farmer"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "message"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # inbound|outbound
    role: Mapped[str] = mapped_column(String(8))  # user|agent|system
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(16), default="text")
    media_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    route: Mapped[str | None] = mapped_column(String(16), nullable=True)  # smalltalk|faq_grounded|refused|escalated
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    line_message_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["Session"] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message")


class FaqDoc(Base):
    __tablename__ = "faq_doc"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64), index=True)
    body_th: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="published")  # draft|published|archived
    version: Mapped[int] = mapped_column(Integer, default=1)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    chunks: Mapped[list["FaqChunk"]] = relationship(
        back_populates="doc", cascade="all, delete-orphan"
    )


class FaqChunk(Base):
    __tablename__ = "faq_chunk"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    faq_doc_id: Mapped[str] = mapped_column(ForeignKey("faq_doc.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, default=list)  # float array (pgvector in prod)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    hash: Mapped[str] = mapped_column(String(64), index=True)

    doc: Mapped["FaqDoc"] = relationship(back_populates="chunks")


class Citation(Base):
    __tablename__ = "citation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("message.id"), index=True)
    faq_chunk_id: Mapped[str] = mapped_column(ForeignKey("faq_chunk.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)

    message: Mapped["Message"] = relationship(back_populates="citations")
    chunk: Mapped["FaqChunk"] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_type: Mapped[str] = mapped_column(String(16))  # admin|system
    actor_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
