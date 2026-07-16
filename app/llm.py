"""LLM providers.

`stub` is an offline responder used for local development and tests. For domain
questions it produces a strictly grounded, extractive answer from the retrieved FAQ
context (it never invents content). For general chat it returns safe canned Thai
replies. Set LLM_PROVIDER=openai to use a real model.

The provider contract is intentionally narrow so the orchestrator's guardrails
(grounding, citations, refusal) remain the source of truth regardless of provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .config import settings

SYSTEM_PROMPT_TH = (
    "คุณเป็นผู้ช่วยตอบคำถามด้านการเกษตรสำหรับเกษตรกรไทยผ่านแอป LINE "
    "ตอบเป็นภาษาไทยที่สุภาพและเข้าใจง่าย "
    "สำหรับคำถามเฉพาะด้านการเกษตร ให้ตอบจากข้อมูลอ้างอิงที่ให้มาเท่านั้น "
    "หากไม่มีข้อมูลอ้างอิงเพียงพอ ให้บอกว่ายังไม่มีข้อมูลและแนะนำให้ติดต่อผู้เชี่ยวชาญ "
    "ห้ามคาดเดาหรือสร้างข้อมูลขึ้นเอง"
)


class LLM(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        user_text: str,
        context_chunks: list[str] | None,
        history: list[dict] | None = None,
        image_b64: str | None = None,
    ) -> str: ...


class StubLLM(LLM):
    name = "stub-extractive"

    def generate(
        self,
        user_text: str,
        context_chunks: list[str] | None,
        history: list[dict] | None = None,
        image_b64: str | None = None,
    ) -> str:
        if image_b64:
            return (
                "ขออภัยครับ ระบบสาธิตยังไม่รองรับการวิเคราะห์รูปภาพ "
                "กรุณาอธิบายอาการเป็นข้อความแทนครับ"
            )
        if context_chunks:
            body = "\n".join(f"• {c.strip()}" for c in context_chunks)
            return (
                "จากข้อมูลในคลังความรู้:\n"
                f"{body}\n\n"
                "หากอาการยังไม่ดีขึ้น แนะนำให้ปรึกษาเจ้าหน้าที่ส่งเสริมการเกษตรในพื้นที่ครับ"
            )
        return (
            "สวัสดีครับ ผมเป็นผู้ช่วยตอบคำถามด้านการเกษตร "
            "สามารถถามเรื่องการปลูกข้าว การดูแลดิน โรคพืช หรือแมลงศัตรูพืชได้เลยครับ"
        )


def _build_user_prompt(user_text: str, context_chunks: list[str] | None) -> str:
    if context_chunks:
        context = "\n\n".join(context_chunks)
        return (
            f"ข้อมูลอ้างอิง (ตอบจากข้อมูลนี้เท่านั้น):\n{context}\n\n"
            f"คำถามของเกษตรกร: {user_text}"
        )
    return user_text


def _build_messages(
    user_text: str,
    context_chunks: list[str] | None,
    history: list[dict] | None,
    image_b64: str | None,
    for_anthropic: bool = False,
) -> list[dict]:
    """Build the messages array with optional history and image."""
    msgs: list[dict] = []

    # Inject conversation history (skip for Anthropic which uses system separately)
    for turn in (history or []):
        msgs.append({"role": turn["role"], "content": turn["content"]})

    prompt_text = _build_user_prompt(user_text, context_chunks)

    if image_b64:
        # Multimodal: image + text
        if for_anthropic:
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": prompt_text},
            ]
        else:
            content = [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt_text},
            ]
        msgs.append({"role": "user", "content": content})
    else:
        msgs.append({"role": "user", "content": prompt_text})

    return msgs


class AnthropicLLM(LLM):
    """Anthropic Claude via the Messages API.

    Requires an Anthropic *API key* (console.anthropic.com) with credits — a
    claude.ai Pro/Max subscription does not grant API access.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        self.name = f"anthropic:{model}"

    def generate(
        self,
        user_text: str,
        context_chunks: list[str] | None,
        history: list[dict] | None = None,
        image_b64: str | None = None,
    ) -> str:
        import httpx

        messages = _build_messages(user_text, context_chunks, history, image_b64, for_anthropic=True)
        model = self.model if not image_b64 else self.model  # claude-sonnet-4-5 supports vision

        resp = httpx.post(
            f"{settings.anthropic_base_url}/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "temperature": 0.2,
                "system": SYSTEM_PROMPT_TH,
                "messages": messages,
            },
            timeout=45,
        )
        if not resp.is_success:
            import sys
            print(f"[AnthropicLLM] HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
            resp.raise_for_status()
        blocks = resp.json().get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return text.strip()


class OpenAILLM(LLM):
    def __init__(self, model: str) -> None:
        self.model = model
        self.name = f"openai:{model}"

    def generate(
        self,
        user_text: str,
        context_chunks: list[str] | None,
        history: list[dict] | None = None,
        image_b64: str | None = None,
    ) -> str:
        import httpx

        messages = _build_messages(user_text, context_chunks, history, image_b64, for_anthropic=False)
        # Vision requires gpt-4o or gpt-4o-mini
        model = "gpt-4o" if image_b64 else self.model
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT_TH}] + messages

        resp = httpx.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": model, "temperature": 0.2, "messages": full_messages},
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def get_llm() -> LLM:
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicLLM(settings.anthropic_model)
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAILLM(settings.llm_model)
    return StubLLM()
