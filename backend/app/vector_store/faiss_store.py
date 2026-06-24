"""
app/vector_store/faiss_store.py
===============================
Vector store abstraction (FAISS backend).

FAISS is used because it is a self-contained, in-process library (no native
server) and is robust across Windows/conda environments. The index is persisted
to disk so the knowledge base survives restarts.

Extends the proven local-rag-chatbot store with **per-document deletion**:
deleting a document removes exactly its chunks from the index (by matching the
`doc_id` carried in each chunk's metadata), satisfying the spec requirement that
deleting a document removes its embeddings.

Thread-safety: a module-level lock guards mutations since FastAPI may call from
multiple worker threads.
"""

from __future__ import annotations

import threading
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FaissVectorStore:
    """Persisted FAISS vector store with a minimal, app-friendly interface."""

    def __init__(self, embedder: Embeddings, persist_dir: Path) -> None:
        self.embedder = embedder
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._store: FAISS | None = self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _index_exists(self) -> bool:
        return (self.persist_dir / "index.faiss").exists()

    def _load(self) -> FAISS | None:
        if not self._index_exists():
            return None
        try:
            return FAISS.load_local(
                str(self.persist_dir),
                self.embedder,
                allow_dangerous_deserialization=True,  # we created this file locally
            )
        except Exception:
            logger.exception("Failed to load FAISS index; starting empty.")
            return None

    def _save(self) -> None:
        if self._store is not None:
            self._store.save_local(str(self.persist_dir))

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #
    def add_documents(self, docs: list[Document]) -> None:
        """Add chunks (each carrying metadata['doc_id']) and persist."""
        if not docs:
            return
        with self._lock:
            if self._store is None:
                self._store = FAISS.from_documents(docs, self.embedder)
            else:
                self._store.add_documents(docs)
            self._save()

    def clear(self) -> None:
        """Wipe the entire index — drops all vectors and removes persisted files."""
        with self._lock:
            self._store = None
            for name in ("index.faiss", "index.pkl"):
                f = self.persist_dir / name
                try:
                    if f.exists():
                        f.unlink()
                except Exception:
                    logger.warning("Could not delete %s", f)
            logger.info("FAISS index cleared.")

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Remove every chunk whose metadata doc_id matches. Returns count."""
        with self._lock:
            if self._store is None:
                return 0
            ids = [
                store_id
                for store_id, doc in self._store.docstore._dict.items()
                if doc.metadata.get("doc_id") == doc_id
            ]
            if not ids:
                return 0
            self._store.delete(ids)
            self._save()
            logger.info("Deleted %d chunks for doc_id=%s", len(ids), doc_id)
            return len(ids)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def similarity_search_with_score(
        self, query: str, k: int, user_id: str | None = None
    ) -> list[tuple[Document, float]]:
        """
        Return (Document, similarity) tuples, similarity in [0, 1] (higher is
        more relevant). Optionally filter to a user's own documents.
        """
        if self._store is None:
            return []
        # Over-fetch when filtering so we still return ~k after the filter.
        fetch = k * 4 if user_id else k
        raw = self._store.similarity_search_with_score(query, k=fetch)
        out: list[tuple[Document, float]] = []
        for doc, dist in raw:
            if user_id and doc.metadata.get("user_id") not in (None, user_id):
                continue
            out.append((doc, 1.0 / (1.0 + float(dist))))
            if len(out) >= k:
                break
        return out

    def all_documents(self, user_id: str | None = None) -> list[Document]:
        """Return stored Documents (used to build the BM25 index)."""
        if self._store is None:
            return []
        docs = list(self._store.docstore._dict.values())
        if user_id:
            docs = [d for d in docs if d.metadata.get("user_id") in (None, user_id)]
        return docs

    def count(self) -> int:
        if self._store is None:
            return 0
        return self._store.index.ntotal
