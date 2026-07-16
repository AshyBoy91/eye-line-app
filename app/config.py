"""Environment-driven application settings.

Kept dependency-light (stdlib only) so the app starts with no external config
libraries. A local .env file is loaded if present.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). Does not override real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _normalize_db_url(url: str) -> str:
    """Render/Heroku hand out `postgres://` URLs; SQLAlchemy needs an explicit
    driver. Map them to the psycopg (v3) driver."""
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class Settings:
    app_env: str = os.environ.get("APP_ENV", "development")
    database_url: str = _normalize_db_url(
        os.environ.get("DATABASE_URL", "sqlite:///./farmeragent.db")
    )

    line_channel_secret: str = os.environ.get("LINE_CHANNEL_SECRET", "")
    line_channel_access_token: str = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    embeddings_provider: str = os.environ.get("EMBEDDINGS_PROVIDER", "hashing")
    embeddings_dim: int = _get_int("EMBEDDINGS_DIM", 256)
    embeddings_model: str = os.environ.get("EMBEDDINGS_MODEL", "text-embedding-3-small")

    # LLM: stub (offline) | anthropic (Claude) | openai
    llm_provider: str = os.environ.get("LLM_PROVIDER", "stub")
    llm_model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    openai_base_url: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Anthropic Claude (Messages API — requires an API key, not a claude.ai subscription)
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    anthropic_base_url: str = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

    retrieval_top_k: int = _get_int("RETRIEVAL_TOP_K", 4)
    retrieval_min_score: float = _get_float("RETRIEVAL_MIN_SCORE", 0.18)

    admin_token: str = os.environ.get("ADMIN_TOKEN", "change-me-admin-token")
    admin_password: str = os.environ.get("ADMIN_PASSWORD", "6969")

    # Daily briefing — weather via OpenWeatherMap (free tier, 1000 calls/day).
    # Leave blank to skip weather in the briefing.
    openweather_api_key: str = os.environ.get("OPENWEATHER_API_KEY", "")
    openweather_city: str = os.environ.get("OPENWEATHER_CITY", "Chiang Mai,TH")


settings = Settings()
