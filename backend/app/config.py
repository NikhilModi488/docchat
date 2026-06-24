"""
app/config.py
=============
Central configuration for the production RAG backend.

All tunable parameters live here so the rest of the codebase never hard-codes
magic numbers. Values can be overridden through environment variables (loaded
from a local .env via python-dotenv), which keeps the app container/CI friendly.

Design note (SRP): this module owns *configuration only*. It performs no heavy
imports and no side effects beyond creating runtime directories, so it is safe
to import from anywhere very early in startup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env (if present) before reading any variables.
load_dotenv()

# --------------------------------------------------------------------------- #
# Environment hardening — set BEFORE torch / faiss are imported anywhere.
# KMP_DUPLICATE_LIB_OK avoids OpenMP duplicate-runtime crashes in conda envs.
# --------------------------------------------------------------------------- #
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# --------------------------------------------------------------------------- #
# Filesystem locations
# --------------------------------------------------------------------------- #
# BASE_DIR = backend/  (parent of the app/ package)
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"               # bundled sample docs
UPLOAD_DIR: Path = BASE_DIR / "uploads"          # user-uploaded files at runtime
VECTORSTORE_DIR: Path = BASE_DIR / "vectorstore"  # persisted FAISS index
STATIC_DIR: Path = BASE_DIR / "static"           # served rasterised PDF pages
LOG_DIR: Path = BASE_DIR / "logs"
DB_DIR: Path = BASE_DIR / "db"

for _d in (DATA_DIR, UPLOAD_DIR, VECTORSTORE_DIR, STATIC_DIR, LOG_DIR, DB_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: str) -> bool:
    return _env(key, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class IngestionConfig:
    """Parameters that govern document loading, cleaning and chunking."""

    chunk_size: int = int(_env("RAG_CHUNK_SIZE", "800"))
    chunk_overlap: int = int(_env("RAG_CHUNK_OVERLAP", "200"))
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")
    # Chunking strategy: "page" = one chunk per page with cross-page overlap
    # (oversized pages are sub-split); "recursive" = classic size-based splitting.
    chunk_strategy: str = _env("RAG_CHUNK_STRATEGY", "page").lower()
    # A page longer than this (chars) is sub-split so the embedder doesn't truncate it.
    max_page_chars: int = int(_env("RAG_MAX_PAGE_CHARS", "1600"))
    max_file_mb: int = int(_env("RAG_MAX_FILE_MB", "25"))
    enable_ocr: bool = _env_bool("RAG_ENABLE_OCR", "true")
    enable_tables: bool = _env_bool("RAG_ENABLE_TABLES", "true")
    allowed_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md", ".pptx")


@dataclass(frozen=True)
class EmbeddingConfig:
    """Local embedding model configuration (SentenceTransformers)."""

    # all-MiniLM-L6-v2 is fast & small (384-dim). Swap to BAAI/bge-small-en-v1.5
    # by exporting RAG_EMBED_MODEL.
    model_name: str = _env("RAG_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    device: str = _env("RAG_EMBED_DEVICE", "auto")  # "auto" | "cpu" | "cuda"
    normalize: bool = True
    batch_size: int = int(_env("RAG_EMBED_BATCH", "32"))


@dataclass(frozen=True)
class RetrievalConfig:
    """Similarity search + reranking parameters."""

    top_k: int = int(_env("RAG_TOP_K", "5"))
    fetch_k: int = int(_env("RAG_FETCH_K", "20"))
    use_reranker: bool = _env_bool("RAG_USE_RERANKER", "true")
    reranker_model: str = _env("RAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    use_hybrid: bool = _env_bool("RAG_USE_HYBRID", "true")
    hybrid_alpha: float = float(_env("RAG_HYBRID_ALPHA", "0.5"))
    # Minimum rerank/similarity score to treat context as relevant. CrossEncoder
    # scores are uncalibrated logits (often negative even for good matches), so by
    # default we effectively only gate on *empty* retrieval and let the LLM's
    # system prompt emit the fallback when context is genuinely insufficient.
    min_relevance: float = float(_env("RAG_MIN_RELEVANCE", "-1e9"))
    # Context compression: keep at most this many characters of assembled context.
    max_context_chars: int = int(_env("RAG_MAX_CONTEXT_CHARS", "6000"))


@dataclass(frozen=True)
class LLMConfig:
    """Ollama local-inference configuration. One model serves all roles."""

    host: str = _env("OLLAMA_HOST", _env("OLLAMA_BASE_URL", "http://localhost:11434"))
    default_model: str = _env("RAG_LLM_MODEL", _env("OLLAMA_CHAT_MODEL", "llama3.2"))
    available_models: tuple[str, ...] = ("llama3.2", "mistral", "phi4", "gemma3")
    temperature: float = float(_env("RAG_LLM_TEMPERATURE", "0.1"))
    num_predict: int = int(_env("RAG_LLM_NUM_PREDICT", "1024"))
    request_timeout: int = int(_env("RAG_LLM_TIMEOUT", "120"))


@dataclass(frozen=True)
class MemoryConfig:
    max_interactions: int = int(_env("RAG_MEMORY_TURNS", "5"))


@dataclass(frozen=True)
class AuthConfig:
    secret_key: str = _env("RAG_JWT_SECRET", "change-me-in-production-please")
    algorithm: str = "HS256"
    token_expire_minutes: int = int(_env("RAG_TOKEN_EXPIRE_MIN", "1440"))
    # When false, requests without a token use a shared "default" user (handy for
    # local single-user development). When true, all routes require a valid JWT.
    require_auth: bool = _env_bool("RAG_REQUIRE_AUTH", "false")
    default_user: str = "default"


@dataclass(frozen=True)
class EvalConfig:
    enabled: bool = _env_bool("RAG_ENABLE_RAGAS", "true")
    # Use the lightweight heuristic scorer by default (true RAGAS is heavy and
    # needs a judge LLM). Set RAG_RAGAS_FULL=true to attempt the real library.
    use_full_ragas: bool = _env_bool("RAG_RAGAS_FULL", "false")


@dataclass(frozen=True)
class AppConfig:
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    evaluation: EvalConfig = field(default_factory=EvalConfig)

    database_url: str = _env("RAG_DATABASE_URL", f"sqlite:///{(DB_DIR / 'rag.db').as_posix()}")
    cors_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in _env(
            "RAG_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if o.strip()
    )
    rate_limit: str = _env("RAG_RATE_LIMIT", "60/minute")
    app_title: str = "Document RAG Chatbot API"
    fallback_answer: str = (
        "I could not find sufficient information in the uploaded documents."
    )


settings = AppConfig()
