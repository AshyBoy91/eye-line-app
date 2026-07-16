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
from ..conversation import get_recent_history

router = APIRouter(tags=["webhook"])


def _process(
    db: DbSession,
    line_user_id: str,
    text: str,
    line_message_id: str | None,
    image_b64: str | None = None,
) -> tuple[AgentResult | None, str]:
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
    conversation.log_inbound(db, session, text or "[image]", line_message_id)

    history = get_recent_history(db, session)
    try:
        result = handle(db, text or "", history=history, image_b64=image_b64)
    except Exception as exc:
        import sys
        print(f"[webhook] LLM error for user {line_user_id}: {exc}", file=sys.stderr)
        from ..guardrails import LLM_ERROR_RESPONSE_TH
        from ..orchestrator import AgentResult
        result = AgentResult(
            reply=LLM_ERROR_RESPONSE_TH,
            intent="error",
            route="error",
            model="error",
        )

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
        msg_type = message.get("type")
        if msg_type not in ("text", "image"):
            continue
        line_user_id = event.get("source", {}).get("userId", "unknown")
        line_message_id = message.get("id")
        reply_token = event.get("replyToken", "")

        text = ""
        image_b64 = None

        if msg_type == "text":
            text = message.get("text", "")
        elif msg_type == "image":
            # Send immediate acknowledgement (consumes the reply token)
            line_client.reply(reply_token, line_client.IMAGE_INTRO_TH)
            image_b64 = line_client.get_image_b64(line_message_id)
            reply_token = ""  # already consumed

        result, briefing = _process(db, line_user_id, text, line_message_id, image_b64)
        if result is not None:
            if reply_token:
                # Text message — use reply token (briefing as first bubble)
                if briefing:
                    line_client.reply(reply_token, briefing, result.reply)
                else:
                    line_client.reply(reply_token, result.reply)
            elif image_b64:
                # Image — reply token consumed by ack; push the analysis result
                line_client.push(line_user_id, result.reply)
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
