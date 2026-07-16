"""FastAPI application entry point.

On startup it creates tables and seeds sample FAQ content if the knowledge base is
empty, so the app is usable immediately after `uvicorn app.main:app`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .config import settings
from .database import SessionLocal, init_db
from .routers import admin, webhook
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title="Thai Farmer LINE LLM Agent", version="0.1.0", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "embeddings_provider": settings.embeddings_provider,
    }


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
