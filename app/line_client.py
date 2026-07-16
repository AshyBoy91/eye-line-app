"""LINE Messaging API helpers: webhook signature verification and reply."""
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx

from .config import settings

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_URL  = "https://api.line.me/v2/bot/message/push"
LINE_CONTENT_URL = "https://api-data.line.me/v2/bot/message/{message_id}/content"

IMAGE_INTRO_TH = (
    "📸 ได้รับรูปภาพแล้วครับ — กำลังวิเคราะห์ด้วย AI\n\n"
    "ผมสามารถระบุ:\n"
    "• โรคพืช (ใบจุด ราสนิม ไหม้ เน่า ฯลฯ)\n"
    "• แมลงศัตรูพืช (เพลี้ย หนอน ไรแดง ฯลฯ)\n"
    "• ความผิดปกติ (ใบเหลือง เหี่ยว แห้ง ฯลฯ)\n"
    "• สภาพรากและดิน\n\n"
    "⏳ กรุณารอสักครู่ ผลจะส่งให้ทันทีครับ 🌾"
)

HOW_IT_WORKS_TH = (
    "🌾 วิธีใช้งานผู้ช่วยเกษตรกรไทย\n"
    "────────────────────────\n\n"
    "✅ ถามได้เลย (พิมพ์เป็นภาษาไทย)\n"
    "• โรคพืช เช่น ข้าวใบเหลือง เพลี้ยกระโดด\n"
    "• ดิน ปุ๋ย การปรับปรุงดิน\n"
    "• การเก็บเกี่ยว ช่วงเวลาที่เหมาะสม\n"
    "• แมลงศัตรูพืช วิธีป้องกัน\n\n"
    "📸 ส่งรูปภาพ\n"
    "• ถ่ายรูปพืชที่มีปัญหาแล้วส่งมาได้เลย\n"
    "• AI จะวิเคราะห์โรค แมลง หรือความผิดปกติ\n\n"
    "📋 กดปุ่มเมนูด้านล่างเพื่อเลือกหัวข้อ\n\n"
    "⚠️ หมายเหตุ\n"
    "• คำตอบอ้างอิงจากข้อมูลผู้เชี่ยวชาญเท่านั้น\n"
    "• คำถามเรื่องยาฆ่าแมลง/กฎหมาย/การเงิน จะส่งต่อผู้เชี่ยวชาญ\n"
    "• พัฒนาโดย ดร.ตวงพร & ดร.ดารารัตน์ คณะเกษตรศาสตร์ มช."
)


def push(user_id: str, *texts: str) -> None:
    """Send one or more messages to a user via the LINE Push API.

    Unlike reply(), push() can be called at any time (not limited to a single
    reply-token window). Used for image analysis results where the reply token
    was already consumed by the acknowledgement message.
    """
    if not settings.line_channel_access_token or not user_id:
        return
    messages = [{"type": "text", "text": t[:4900]} for t in texts if t]
    if not messages:
        return
    httpx.post(
        LINE_PUSH_URL,
        headers={
            "Authorization": f"Bearer {settings.line_channel_access_token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": messages},
        timeout=15,
    )
    """Download image content from LINE and return as base64 string."""
    if not settings.line_channel_access_token:
        return None
    try:
        import base64
        resp = httpx.get(
            LINE_CONTENT_URL.format(message_id=message_id),
            headers={"Authorization": f"Bearer {settings.line_channel_access_token}"},
            timeout=20,
        )
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("utf-8")
    except Exception:
        return None


def verify_signature(body: bytes, signature: str | None) -> bool:
    """Verify the X-Line-Signature HMAC-SHA256 header.

    In local development (no channel secret configured) verification is skipped so
    the simulate endpoint and manual testing work without LINE credentials.
    """
    if not settings.line_channel_secret:
        return True
    if not signature:
        return False
    mac = hmac.new(
        settings.line_channel_secret.encode("utf-8"), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def reply(reply_token: str, *texts: str) -> None:
    """Send one or more messages via the LINE Reply API. No-op if not configured.

    Pass multiple positional text arguments to send them as separate chat bubbles
    (LINE allows up to 5 messages per reply). Each text is truncated to 4900 chars.
    """
    if not settings.line_channel_access_token or not reply_token:
        return
    messages = [{"type": "text", "text": t[:4900]} for t in texts if t]
    if not messages:
        return
    httpx.post(
        LINE_REPLY_URL,
        headers={
            "Authorization": f"Bearer {settings.line_channel_access_token}",
            "Content-Type": "application/json",
        },
        json={"replyToken": reply_token, "messages": messages},
        timeout=15,
    )
