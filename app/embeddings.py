"""Embedding providers.

`hashing` is a deterministic, dependency-free embedder that works offline and handles
Thai text (no word boundaries) via character n-grams. It is intended for local
development and tests. In production set EMBEDDINGS_PROVIDER=openai to use a
Thai-capable model; the vector dimension metadata is what drives re-indexing.
"""
from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod

from .config import settings

_WORD_RE = re.compile(r"[a-z0-9]+")


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _tokens(text: str) -> list[str]:
    """Latin word tokens plus character trigrams (covers space-less Thai)."""
    low = text.lower()
    toks = _WORD_RE.findall(low)
    compact = re.sub(r"\s+", "", low)
    toks += [compact[i : i + 3] for i in range(max(0, len(compact) - 2))]
    return toks


class HashingEmbedder(Embedder):
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _tokens(text):
                h = hash(tok) % self.dim
                vec[h] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str, dim: int) -> None:
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        resp = httpx.post(
            f"{settings.openai_base_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": self.model, "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        vectors = [item["embedding"] for item in data]
        self.dim = len(vectors[0]) if vectors else self.dim
        return vectors


def get_embedder() -> Embedder:
    if settings.embeddings_provider == "openai" and settings.openai_api_key:
        return OpenAIEmbedder(settings.embeddings_model, settings.embeddings_dim)
    return HashingEmbedder(settings.embeddings_dim)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
