"""
app/services/resources.py
=========================
Process-wide singletons for the heavy, stateful components (embedder + FAISS
store). Centralising them here means every request shares one loaded model and
one in-memory index, and tests can swap them out.
"""

from __future__ import annotations

from app.config import VECTORSTORE_DIR
from app.embeddings.embedding import get_embedder
from app.vector_store.faiss_store import FaissVectorStore

_store: FaissVectorStore | None = None


def get_store() -> FaissVectorStore:
    global _store
    if _store is None:
        _store = FaissVectorStore(get_embedder(), VECTORSTORE_DIR)
    return _store


def reset_store_singleton() -> None:
    """Test hook: force the store to reload from disk on next access."""
    global _store
    _store = None
