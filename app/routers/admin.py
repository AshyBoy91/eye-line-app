"""Admin portal: review conversations, manage FAQ, with audit logging.

Access is gated by a shared ADMIN_TOKEN (query `?token=` or `X-Admin-Token` header).
This is a minimal RBAC stand-in; production should use per-user auth with roles
(viewer/editor/dpo) as described in the data architecture. Every view of conversation
content writes an `audit_event`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from ..config import settings
from ..database import get_db
from ..llm import AnthropicLLM, OpenAILLM
from ..models import AuditEvent, FaqDoc, Message, Session
from ..seed import reembed_doc, seed_if_empty
from ..seed import reembed_doc

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

ADMIN_COOKIE = "admin_session"


class AdminAuthRequired(Exception):
    """Raised when a browser hits a protected admin page without a valid session.

    An app-level handler turns this into a redirect to the login page.
    """


def require_admin(
    request: Request,
    token: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None),
) -> str:
    # Cookie session (password login) is the primary path; the token query/header
    # is kept as a fallback for API clients (e.g. X-Admin-Token on /admin/api/*).
    cookie = request.cookies.get(ADMIN_COOKIE)
    provided = cookie or token or x_admin_token
    if not provided or provided != settings.admin_token:
        raise AdminAuthRequired()
    return "admin"


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: int = Query(default=0)) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin_login.html", {"error": error})


@router.post("/login")
def login_submit(password: str = Form(...)) -> RedirectResponse:
    if password != settings.admin_password:
        return RedirectResponse(url="/admin/login?error=1", status_code=303)
    resp = RedirectResponse(url="/admin/conversations", status_code=303)
    resp.set_cookie(
        ADMIN_COOKIE,
        settings.admin_token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=60 * 60 * 8,
    )
    return resp


@router.get("/logout")
def logout() -> RedirectResponse:
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie(ADMIN_COOKIE)
    return resp


@router.post("/reseed")
def reseed(
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> RedirectResponse:
    """Delete all FAQ docs (cascade to chunks) and re-seed from the default dataset."""
    docs = db.scalars(select(FaqDoc)).all()
    for doc in docs:
        db.delete(doc)
    db.commit()
    n = seed_if_empty(db)
    _audit(db, action="reseed_faq")
    return RedirectResponse(url=f"/admin/faq?token={token}&reseeded={n}", status_code=303)


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
    q: str = Query(default=""),
    route: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> HTMLResponse:
    stmt = (
        select(Session)
        .options(selectinload(Session.messages).selectinload(Message.citations))
        .order_by(Session.last_activity_at.desc())
    )
    if q:
        stmt = stmt.join(Message, Message.session_id == Session.id).where(
            Message.content.ilike(f"%{q}%")
        ).distinct()
    if route:
        stmt = stmt.join(Message, Message.session_id == Session.id, isouter=True).where(
            Message.route == route
        ).distinct()
    sessions = db.scalars(stmt.limit(100)).all()
    _audit(db, action="view_conversations")
    return templates.TemplateResponse(
        request,
        "admin_conversations.html",
        {"sessions": sessions, "token": token, "q": q, "route": route},
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
    valid_from: str = Form(default=""),
    valid_to: str = Form(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> RedirectResponse:
    def _parse_dt(s: str):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if s.strip() else None
    doc = FaqDoc(
        title=title.strip(), category=category.strip(),
        source=source.strip() or None, body_th=body_th.strip(),
        status="published", version=1,
        valid_from=_parse_dt(valid_from), valid_to=_parse_dt(valid_to),
    )
    db.add(doc); db.flush()
    reembed_doc(db, doc)
    _audit(db, action="create_faq", target_type="faq_doc", target_id=doc.id)
    return RedirectResponse(url=f"/admin/faq?token={token}", status_code=303)


@router.get("/faq/{doc_id}/edit", response_class=HTMLResponse)
def faq_edit_form(
    request: Request, doc_id: str,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> HTMLResponse:
    doc = db.get(FaqDoc, doc_id)
    if not doc:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(request, "admin_faq_edit.html", {"doc": doc, "token": token})


@router.post("/faq/{doc_id}/edit", response_class=RedirectResponse)
def faq_edit_save(
    doc_id: str,
    token: str = Query(default=""),
    title: str = Form(...),
    category: str = Form(...),
    source: str = Form(default=""),
    body_th: str = Form(...),
    valid_from: str = Form(default=""),
    valid_to: str = Form(default=""),
    status: str = Form(default="published"),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> RedirectResponse:
    def _parse_dt(s: str):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if s.strip() else None
    doc = db.get(FaqDoc, doc_id)
    if not doc:
        return RedirectResponse(url=f"/admin/faq?token={token}", status_code=303)
    doc.title = title.strip(); doc.category = category.strip()
    doc.source = source.strip() or None; doc.body_th = body_th.strip()
    doc.status = status; doc.version += 1
    doc.valid_from = _parse_dt(valid_from); doc.valid_to = _parse_dt(valid_to)
    reembed_doc(db, doc)
    _audit(db, action="edit_faq", target_type="faq_doc", target_id=doc.id)
    return RedirectResponse(url=f"/admin/faq?token={token}", status_code=303)


@router.post("/faq/{doc_id}/delete", response_class=RedirectResponse)
def faq_delete(
    doc_id: str,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> RedirectResponse:
    doc = db.get(FaqDoc, doc_id)
    if doc:
        db.delete(doc); db.commit()
        _audit(db, action="delete_faq", target_type="faq_doc", target_id=doc_id)
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


# ── LLM Comparison ────────────────────────────────────────────────────────────

@router.get("/compare", response_class=HTMLResponse)
def compare_page(
    request: Request,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin_compare.html",
        {
            "token": token,
            "anthropic_ready": bool(settings.anthropic_api_key),
            "openai_ready": bool(settings.openai_api_key),
            "anthropic_model": settings.anthropic_model,
            "openai_model": settings.llm_model,
        },
    )


@router.post("/api/compare")
def api_compare(
    request: Request,
    question: str = Form(...),
    context: str = Form(default=""),
    _: str = Depends(require_admin),
) -> dict:
    """Run the same question through both Claude and GPT-4o and return both answers."""
    import time

    chunks = [context.strip()] if context.strip() else None
    results = {}

    for provider, llm in [
        ("anthropic", AnthropicLLM(settings.anthropic_model) if settings.anthropic_api_key else None),
        ("openai", OpenAILLM(settings.llm_model) if settings.openai_api_key else None),
    ]:
        if llm is None:
            results[provider] = {"reply": f"⚠️ {provider} API key not configured.", "latency_ms": 0, "model": "—"}
            continue
        t0 = time.perf_counter()
        try:
            reply = llm.generate(question, context_chunks=chunks)
            latency = int((time.perf_counter() - t0) * 1000)
            results[provider] = {"reply": reply, "latency_ms": latency, "model": llm.name}
        except Exception as exc:
            results[provider] = {"reply": f"❌ Error: {exc}", "latency_ms": 0, "model": llm.name}

    return results


# ── Stats Dashboard ───────────────────────────────────────────────────────────

@router.get("/stats", response_class=HTMLResponse)
def stats_page(
    request: Request,
    token: str = Query(default=""),
    _: str = Depends(require_admin),
    db: DbSession = Depends(get_db),
) -> HTMLResponse:
    from sqlalchemy import func, case
    from ..models import FaqChunk

    # Message stats
    total_sessions = db.scalar(select(func.count()).select_from(Session)) or 0
    total_msgs = db.scalar(select(func.count()).select_from(Message)) or 0
    inbound = db.scalar(select(func.count()).select_from(Message).where(Message.direction == "inbound")) or 0

    route_counts = dict(
        db.execute(
            select(Message.route, func.count()).where(Message.route.isnot(None)).group_by(Message.route)
        ).all()
    )

    avg_conf = db.scalar(
        select(func.avg(Message.confidence)).where(
            Message.route == "faq_grounded", Message.confidence.isnot(None)
        )
    )

    avg_latency = db.scalar(
        select(func.avg(Message.latency_ms)).where(Message.latency_ms > 0)
    )

    # Daily activity (last 7 days)
    from datetime import timedelta
    from ..daily_briefing import today_bangkok
    today = today_bangkok()
    daily = {}
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        cnt = db.scalar(
            select(func.count()).select_from(Message)
            .where(
                Message.direction == "inbound",
                func.date(Message.created_at) == day,
            )
        ) or 0
        daily[day.strftime("%d/%m")] = cnt

    # FAQ stats
    faq_total = db.scalar(select(func.count()).select_from(FaqDoc)) or 0
    faq_published = db.scalar(select(func.count()).select_from(FaqDoc).where(FaqDoc.status == "published")) or 0
    chunk_total = db.scalar(select(func.count()).select_from(FaqChunk)) or 0
    faq_by_cat = dict(
        db.execute(
            select(FaqDoc.category, func.count()).where(FaqDoc.status == "published").group_by(FaqDoc.category)
        ).all()
    )

    grounded = route_counts.get("faq_grounded", 0)
    refused  = route_counts.get("refused", 0)
    smalltalk = route_counts.get("smalltalk", 0)
    image_analysis = route_counts.get("image_analysis", 0)
    error = route_counts.get("error", 0)

    return templates.TemplateResponse(
        request, "admin_stats.html",
        {
            "token": token,
            "total_sessions": total_sessions,
            "total_msgs": total_msgs,
            "inbound": inbound,
            "grounded": grounded,
            "refused": refused,
            "smalltalk": smalltalk,
            "image_analysis": image_analysis,
            "error": error,
            "avg_conf": round(avg_conf * 100) if avg_conf else None,
            "avg_latency": round(avg_latency) if avg_latency else None,
            "daily": daily,
            "faq_total": faq_total,
            "faq_published": faq_published,
            "chunk_total": chunk_total,
            "faq_by_cat": faq_by_cat,
            "grounding_rate": round(grounded / inbound * 100) if inbound else 0,
            "refusal_rate": round(refused / inbound * 100) if inbound else 0,
        },
    )
