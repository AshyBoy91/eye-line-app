"""LINE Messaging API helpers: webhook signature verification and reply."""
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx

from .config import settings

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"


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


def reply(reply_token: str, text: str) -> None:
    """Send a reply via the LINE Reply API. No-op if not configured."""
    if not settings.line_channel_access_token or not reply_token:
        return
    httpx.post(
        LINE_REPLY_URL,
        headers={
            "Authorization": f"Bearer {settings.line_channel_access_token}",
            "Content-Type": "application/json",
        },
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text[:4900]}]},
        timeout=15,
    )
