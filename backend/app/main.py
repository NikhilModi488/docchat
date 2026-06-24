"""
app/main.py
===========
FastAPI application factory.

Mounts all routers under /api, configures CORS + rate limiting, initialises the
database on startup, and exposes a health endpoint. The heavy ML singletons
(embedder, FAISS store, reranker) are loaded lazily on first use so startup is
fast and import-safe.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import analytics, auth, chat, conversations, documents, feedback
from app.config import settings
from app.database.session import init_db
from app.llm.ollama_model import OllamaLLM
from app.services.resources import get_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("Database initialised. CORS origins: %s", settings.cors_origins)
    yield


app = FastAPI(title=settings.app_title, version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request, exc):  # pragma: no cover
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ollama_available": OllamaLLM.is_available(),
        "models": OllamaLLM.list_models(),
        "default_model": settings.llm.default_model,
        "embedding_model": settings.embedding.model_name,
        "vector_store": "faiss",
        "chunks_indexed": get_store().count(),
        "require_auth": settings.auth.require_auth,
    }


# Mount routers under /api (matches the spec endpoint paths).
for r in (auth.router, documents.router, chat.router, conversations.router, feedback.router, analytics.router):
    app.include_router(r, prefix="/api")
