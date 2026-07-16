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
    def generate(self, user_text: str, context_chunks: list[str] | None) -> str: ...


class StubLLM(LLM):
    name = "stub-extractive"

    def generate(self, user_text: str, context_chunks: list[str] | None) -> str:
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


class AnthropicLLM(LLM):
    """Anthropic Claude via the Messages API.

    Requires an Anthropic *API key* (console.anthropic.com) with credits — a
    claude.ai Pro/Max subscription does not grant API access.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        self.name = f"anthropic:{model}"

    def generate(self, user_text: str, context_chunks: list[str] | None) -> str:
        import httpx

        resp = httpx.post(
            f"{settings.anthropic_base_url}/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1024,
                "temperature": 0.2,
                "system": SYSTEM_PROMPT_TH,
                "messages": [
                    {"role": "user", "content": _build_user_prompt(user_text, context_chunks)}
                ],
            },
            timeout=45,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return text.strip()


class OpenAILLM(LLM):
    def __init__(self, model: str) -> None:
        self.model = model
        self.name = f"openai:{model}"

    def generate(self, user_text: str, context_chunks: list[str] | None) -> str:
        import httpx

        user = _build_user_prompt(user_text, context_chunks)

        resp = httpx.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_TH},
                    {"role": "user", "content": user},
                ],
            },
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
