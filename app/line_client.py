"""LINE Messaging API helpers: webhook signature verification and reply."""
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx

from .config import settings

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
LINE_CONTENT_URL = "https://api-data.line.me/v2/bot/message/{message_id}/content"

IMAGE_INTRO_TH = (
    "📸 ได้รับรูปภาพแล้วครับ กำลังวิเคราะห์...\n\n"
    "ผมสามารถช่วยระบุ: โรคพืช · แมลงศัตรู · ความผิดปกติของใบและลำต้น\n"
    "กรุณารอสักครู่นะครับ 🌾"
)


def get_image_b64(message_id: str) -> str | None:
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
