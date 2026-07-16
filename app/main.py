"""FastAPI application entry point.

On startup it creates tables and seeds sample FAQ content if the knowledge base is
empty, so the app is usable immediately after `uvicorn app.main:app`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import settings
from .database import SessionLocal, init_db
from .routers import admin, webhook
from .routers.admin import AdminAuthRequired
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title="Thai Farmer LINE LLM Agent", version="0.1.0", lifespan=lifespan, docs_url="/docs")
app.include_router(webhook.router)
app.include_router(admin.router)

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.exception_handler(AdminAuthRequired)
async def _admin_auth_redirect(request, exc):
    # Unauthenticated browser access to a protected admin page → login screen.
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "embeddings_provider": settings.embeddings_provider,
    }


@app.get("/", response_class=HTMLResponse)
def landing(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "landing.html", {})
