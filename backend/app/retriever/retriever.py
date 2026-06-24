"""
app/retriever/retriever.py
==========================
Retrieval layer: hybrid (dense FAISS + BM25) candidate generation followed by
optional CrossEncoder reranking. `retrieve(query, user_id)` returns the top-k
(Document, score) tuples ready for context assembly and citations.

User isolation: when `user_id` is provided, both dense and BM25 candidate sets
are restricted to that user's chunks.
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.config import settings
from app.retriever.reranker import CrossEncoderReranker
from app.services.resources import get_store
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    def __init__(self) -> None:
        self.cfg = settings.retrieval
        self._reranker: CrossEncoderReranker | None = None  # lazy

    # --- candidate generation ---------------------------------------------
    def _vector_search(self, query: str, k: int, user_id: str | None) -> list[tuple[Document, float]]:
        return get_store().similarity_search_with_score(query, k=k, user_id=user_id)

    def _bm25_search(self, query: str, k: int, user_id: str | None) -> list[tuple[Document, float]]:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed; skipping BM25.")
            return []

        docs = get_store().all_documents(user_id=user_id)
        if not docs:
            return []
        corpus = [d.page_content.split() for d in docs]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query.split())
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:k]
        max_score = max((s for _, s in ranked), default=1.0) or 1.0
        return [(doc, float(s) / max_score) for doc, s in ranked]

    # --- fusion -----------------------------------------------------------
    @staticmethod
    def _fuse(vector_hits, bm25_hits, alpha: float) -> list[Document]:
        merged: dict[str, tuple[Document, float]] = {}

        def key(doc: Document) -> str:
            return doc.metadata.get("chunk_id") or doc.page_content[:80]

        for doc, score in vector_hits:
            merged[key(doc)] = (doc, alpha * score)
        for doc, score in bm25_hits:
            k = key(doc)
            if k in merged:
                d, existing = merged[k]
                merged[k] = (d, existing + (1 - alpha) * score)
            else:
                merged[k] = (doc, (1 - alpha) * score)

        ordered = sorted(merged.values(), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ordered]

    # --- public API -------------------------------------------------------
    def retrieve(self, query: str, user_id: str | None = None) -> list[tuple[Document, float]]:
        k = self.cfg.top_k
        fetch_k = self.cfg.fetch_k

        vector_hits = self._vector_search(query, fetch_k, user_id)

        if self.cfg.use_hybrid:
            bm25_hits = self._bm25_search(query, fetch_k, user_id)
            candidates = self._fuse(vector_hits, bm25_hits, self.cfg.hybrid_alpha)
        else:
            candidates = [doc for doc, _ in vector_hits]

        if self.cfg.use_reranker and candidates:
            if self._reranker is None:
                self._reranker = CrossEncoderReranker()
            return self._reranker.rerank(query, candidates[: fetch_k], top_k=k)

        sim = {id(doc): score for doc, score in vector_hits}
        top = candidates[:k]
        return [(doc, sim.get(id(doc), 0.0)) for doc in top]
