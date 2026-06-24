"""
app/evaluation/ragas_eval.py
============================
RAG evaluation.

True RAGAS (faithfulness / answer relevancy / context precision / recall) needs
a judge LLM and is heavy, so by default we compute a fast, dependency-free
**heuristic** approximation based on lexical overlap between answer, question
and retrieved context. Set RAG_RAGAS_FULL=true (and install `ragas`) to attempt
the real metrics, with the heuristic as a safe fallback on any failure.

Scores are in [0, 1]; higher is better.
"""

from __future__ import annotations

import re

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def heuristic_scores(question: str, answer: str, contexts: list[str]) -> dict:
    """Cheap lexical proxy for the three headline RAGAS metrics."""
    q, a = _tokens(question), _tokens(answer)
    ctx = set().union(*[_tokens(c) for c in contexts]) if contexts else set()

    # Faithfulness: how much of the answer is grounded in the context.
    faithfulness = _overlap(a, ctx)
    # Answer relevancy: how well the answer covers the question's terms.
    answer_relevancy = _overlap(q, a)
    # Context precision: how much of the retrieved context relates to the question.
    context_precision = _overlap(ctx, q) if ctx else 0.0

    # A fallback "no info" answer should score low on faithfulness/relevancy.
    if settings.fallback_answer.lower()[:20] in (answer or "").lower():
        faithfulness = answer_relevancy = 0.0

    return {
        "faithfulness": round(min(1.0, faithfulness), 3),
        "answer_relevancy": round(min(1.0, answer_relevancy), 3),
        "context_precision": round(min(1.0, context_precision), 3),
    }


def evaluate(question: str, answer: str, contexts: list[str]) -> dict:
    if not settings.evaluation.enabled:
        return {"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0}

    if settings.evaluation.use_full_ragas:
        try:
            return _full_ragas(question, answer, contexts)
        except Exception:
            logger.exception("Full RAGAS failed; falling back to heuristic scores.")

    return heuristic_scores(question, answer, contexts)


def _full_ragas(question: str, answer: str, contexts: list[str]) -> dict:  # pragma: no cover
    """Attempt real RAGAS metrics. Requires `ragas` + a configured judge LLM."""
    from datasets import Dataset
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import answer_relevancy, context_precision, faithfulness

    ds = Dataset.from_dict(
        {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        }
    )
    result = ragas_evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
    df = result.to_pandas().iloc[0]
    return {
        "faithfulness": round(float(df.get("faithfulness", 0.0)), 3),
        "answer_relevancy": round(float(df.get("answer_relevancy", 0.0)), 3),
        "context_precision": round(float(df.get("context_precision", 0.0)), 3),
    }
