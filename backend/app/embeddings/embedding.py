"""
app/embeddings/embedding.py
===========================
Embedding layer.

Wraps a local SentenceTransformers model behind LangChain's `Embeddings`
interface so it plugs directly into the FAISS store. Running locally means no
data ever leaves the machine.

A module-level cache avoids reloading the (hundreds of MB) model. A small
in-process query-embedding cache (hash -> vector) speeds up repeated queries.
"""

from __future__ import annotations

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings
from app.utils.helpers import sha256_text
from app.utils.logger import get_logger

logger = get_logger(__name__)

_embedder_cache: dict[str, HuggingFaceEmbeddings] = {}
_query_vec_cache: dict[str, list[float]] = {}
_QUERY_CACHE_MAX = 512


def _resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


class CachedEmbeddings(HuggingFaceEmbeddings):
    """HuggingFaceEmbeddings with a small LRU-ish cache for query vectors."""

    def embed_query(self, text: str) -> list[float]:  # type: ignore[override]
        key = sha256_text(text)
        cached = _query_vec_cache.get(key)
        if cached is not None:
            return cached
        vec = super().embed_query(text)
        if len(_query_vec_cache) >= _QUERY_CACHE_MAX:
            _query_vec_cache.clear()
        _query_vec_cache[key] = vec
        return vec


def get_embedder(model_name: str | None = None) -> HuggingFaceEmbeddings:
    """Return a cached embeddings instance exposing embed_documents/embed_query."""
    cfg = settings.embedding
    name = model_name or cfg.model_name
    if name in _embedder_cache:
        return _embedder_cache[name]

    device = _resolve_device(cfg.device)
    logger.info("Loading embedding model '%s' on %s", name, device)

    embedder = CachedEmbeddings(
        model_name=name,
        model_kwargs={"device": device},
        encode_kwargs={
            "normalize_embeddings": cfg.normalize,
            "batch_size": cfg.batch_size,
        },
    )
    _embedder_cache[name] = embedder
    return embedder
