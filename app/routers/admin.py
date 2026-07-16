"""Admin portal: review conversations, manage FAQ, with audit logging.

Access is gated by a shared ADMIN_TOKEN (query `?token=` or `X-Admin-Token` header).
This is a minimal RBAC stand-in; production should use per-user auth with roles
(viewer/editor/dpo) as described in the data architecture. Every view of conversation
content writes an `audit_event`.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from ..config import settings
from ..database import get_db
from ..models import AuditEvent, FaqDoc, Message, Session
from ..seed import reembed_doc

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def require_admin(
    token: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None),
) -> str:
    provided = token or x_admin_token
    if not provided or provided != settings.admin_token:
        raise HTTPException(status_code=401, detail="Admin token required")
    return "admin"


def _audit(db: DbSession, action: str, target_type: str | None = None, target_id: str | None = None) -> None:
    db.add(
        AuditEvent(
            actor_type="admin",
            actor_id="admin",
            action=action,
            target_type=target_type,
            target_id=target_id,
        )
    )
    db.commit()


@router.get("", response_class=RedirectResponse)
def admin_home(token: str = Query(default="")) -> RedirectResponse:
    return RedirectResponse(url=f"/admin/conversations?token={token}")


@router.get("/conversations", response_class=HTMLResponse)
def conversations(
    request: Request,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> HTMLResponse:
    sessions = db.scalars(
        select(Session)
        .options(selectinload(Session.messages).selectinload(Message.citations))
        .order_by(Session.last_activity_at.desc())
        .limit(50)
    ).all()
    _audit(db, action="view_conversations")
    return templates.TemplateResponse(
        request,
        "admin_conversations.html",
        {"sessions": sessions, "token": token},
    )


@router.get("/faq", response_class=HTMLResponse)
def faq_list(
    request: Request,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> HTMLResponse:
    docs = db.scalars(select(FaqDoc).order_by(FaqDoc.updated_at.desc())).all()
    return templates.TemplateResponse(
        request, "admin_faq.html", {"docs": docs, "token": token}
    )


@router.post("/faq", response_class=RedirectResponse)
def faq_create(
    token: str = Query(default=""),
    title: str = Form(...),
    category: str = Form(...),
    source: str = Form(default=""),
    body_th: str = Form(...),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> RedirectResponse:
    doc = FaqDoc(
        title=title.strip(),
        category=category.strip(),
        source=source.strip() or None,
        body_th=body_th.strip(),
        status="published",
        version=1,
    )
    db.add(doc)
    db.flush()
    reembed_doc(db, doc)  # chunk + embed for retrieval
    _audit(db, action="create_faq", target_type="faq_doc", target_id=doc.id)
    return RedirectResponse(url=f"/admin/faq?token={token}", status_code=303)


@router.get("/api/messages")
def api_messages(
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
    limit: int = Query(default=100, le=500),
) -> list[dict]:
    rows = db.scalars(select(Message).order_by(Message.created_at.desc()).limit(limit)).all()
    _audit(db, action="export_messages")
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "direction": m.direction,
            "role": m.role,
            "content": m.content,
            "intent": m.intent,
            "route": m.route,
            "confidence": m.confidence,
            "model": m.model,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]
