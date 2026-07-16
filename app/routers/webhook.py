"""LINE webhook and a local simulate endpoint.

`/webhook/line`     — verifies the LINE signature and processes message events.
`/webhook/simulate` — same processing path without LINE credentials, for local testing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from .. import conversation, line_client
from ..daily_briefing import build_daily_briefing, needs_daily_briefing, mark_briefing_sent
from ..database import get_db
from ..orchestrator import AgentResult, handle

router = APIRouter(tags=["webhook"])


def _process(db: DbSession, line_user_id: str, text: str, line_message_id: str | None) -> tuple[AgentResult | None, str]:
    """Run the full inbound pipeline.

    Returns (result, briefing) where result is None on duplicate and
    briefing is a non-empty string when it's the farmer's first interaction today.
    """
    if conversation.is_duplicate(db, line_message_id):
        return None, ""

    farmer = conversation.get_or_create_farmer(db, line_user_id)

    briefing = ""
    if needs_daily_briefing(farmer):
        briefing = build_daily_briefing(db)
        mark_briefing_sent(db, farmer)

    session = conversation.get_active_session(db, farmer)
    conversation.log_inbound(db, session, text, line_message_id)

    result = handle(db, text)

    conversation.log_outbound(db, session, result)
    db.commit()
    return result, briefing


@router.post("/webhook/line")
async def line_webhook(
    request: Request,
    x_line_signature: str | None = Header(default=None),
    db: DbSession = Depends(get_db),
) -> dict:
    body = await request.body()
    if not line_client.verify_signature(body, x_line_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    handled = 0
    for event in payload.get("events", []):
        if event.get("type") != "message":
            continue
        message = event.get("message", {})
        if message.get("type") != "text":
            continue
        line_user_id = event.get("source", {}).get("userId", "unknown")
        text = message.get("text", "")
        line_message_id = message.get("id")
        reply_token = event.get("replyToken", "")

        result, briefing = _process(db, line_user_id, text, line_message_id)
        if result is not None:
            # Send briefing as first bubble, answer as second (LINE supports up to 5).
            if briefing:
                line_client.reply(reply_token, briefing, result.reply)
            else:
                line_client.reply(reply_token, result.reply)
            handled += 1

    return {"status": "ok", "handled": handled}


class SimulateRequest(BaseModel):
    line_user_id: str = "U_demo"
    text: str
    line_message_id: str | None = None


@router.post("/webhook/simulate")
def simulate(req: SimulateRequest, db: DbSession = Depends(get_db)) -> dict:
    result, briefing = _process(db, req.line_user_id, req.text, req.line_message_id)
    if result is None:
        return {"status": "duplicate"}
    return {
        "status": "ok",
        "daily_briefing": briefing or None,
        "reply": result.reply,
        "intent": result.intent,
        "route": result.route,
        "confidence": result.confidence,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "citations": [{"faq_chunk_id": cid, "score": score} for cid, score in result.citations],
    }
