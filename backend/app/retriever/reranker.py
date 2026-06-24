"""
app/retriever/reranker.py
=========================
Reranking layer (advanced feature).

A CrossEncoder reads each (query, passage) pair jointly and scores relevance far
more accurately than the bi-encoder. We over-fetch candidates with hybrid
search, then rerank and keep the best top-k. Loaded lazily and cached.
"""

from __future__ import annotations

from langchain_core.documents import Document

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_reranker_cache: dict[str, object] = {}


class CrossEncoderReranker:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.retrieval.reranker_model
        self._model = self._load(self.model_name)

    @staticmethod
    def _load(model_name: str):
        if model_name in _reranker_cache:
            return _reranker_cache[model_name]
        from sentence_transformers import CrossEncoder

        logger.info("Loading CrossEncoder reranker '%s'", model_name)
        model = CrossEncoder(model_name)
        _reranker_cache[model_name] = model
        return model

    def rerank(self, query: str, docs: list[Document], top_k: int) -> list[tuple[Document, float]]:
        if not docs:
            return []
        pairs = [(query, d.page_content) for d in docs]
        scores = self._model.predict(pairs)
        scored = list(zip(docs, (float(s) for s in scores)))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]
        for doc, score in top:
            doc.metadata["rerank_score"] = round(score, 4)
        return top
