"""
app/rag/pipeline.py
===================
RAG orchestration — the heart of the backend.

Implements the spec query flow:

    history -> language detection -> translate to English -> follow-up
    resolution + rephrase -> hybrid retrieve -> rerank (top 5) -> context
    compression -> answer generation -> citations -> 3 recommendations ->
    RAGAS score -> translate answer back to original language.

Exposes:
    * `run(...)`        blocking; returns the full spec response dict.
    * `stream(...)`     generator yielding ("meta", dict) then ("token", str)
                        then ("final", dict); the final dict is the spec payload.

Language names: langdetect returns ISO codes; we map common ones to English
names for the translation prompt and pass the code through in the response.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

from langchain_core.documents import Document

from app.config import settings
from app.evaluation import ragas_eval
from app.llm.ollama_model import OllamaLLM
from app.llm.prompts import (
    QUERY_REWRITE_PROMPT,
    RAG_PROMPT,
    RECOMMEND_PROMPT,
    TRANSLATE_PROMPT,
)
from app.rag import smalltalk
from app.retriever.retriever import Retriever
from app.utils.helpers import estimate_tokens
from app.utils.logger import get_logger

logger = get_logger(__name__)

_LANG_NAMES = {
    "en": "English", "ar": "Arabic", "hi": "Hindi", "fr": "French",
    "es": "Spanish", "de": "German", "zh-cn": "Chinese", "zh": "Chinese",
    "ja": "Japanese", "ru": "Russian", "pt": "Portuguese", "it": "Italian",
    "ko": "Korean", "nl": "Dutch", "tr": "Turkish", "ur": "Urdu",
}


def detect_language(text: str) -> str:
    try:
        from langdetect import detect

        return detect(text)
    except Exception:
        return "en"


def language_name(code: str) -> str:
    return _LANG_NAMES.get(code.lower(), "English")


class RAGPipeline:
    def __init__(self, model: str | None = None) -> None:
        self.llm = OllamaLLM(model=model)
        self.retriever = Retriever()

    # --- language helpers -------------------------------------------------
    def _translate(self, text: str, target_language: str) -> str:
        try:
            out = self.llm.invoke(TRANSLATE_PROMPT, text=text, target_language=target_language)
            return out.strip() or text
        except Exception:
            logger.exception("Translation to %s failed; using original text.", target_language)
            return text

    # --- query prep -------------------------------------------------------
    def _rephrase(self, question: str, history: str) -> str:
        try:
            out = self.llm.invoke(QUERY_REWRITE_PROMPT, history=history, question=question).strip()
            return out or question
        except Exception:
            logger.exception("Rephrase failed; using original question.")
            return question

    # --- context assembly + compression ----------------------------------
    @staticmethod
    def _assemble_context(retrieved: list[tuple[Document, float]]) -> str:
        blocks = []
        for i, (doc, _s) in enumerate(retrieved, start=1):
            src = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page_number", "?")
            blocks.append(f"[Source {i}: {src}, page {page}]\n{doc.page_content}")
        context = "\n\n".join(blocks)
        # Context compression: hard cap to control token usage.
        cap = settings.retrieval.max_context_chars
        if len(context) > cap:
            context = context[:cap] + "\n[...context truncated...]"
        return context

    @staticmethod
    def _content_signature(text: str) -> str:
        """Normalised fingerprint for near-duplicate detection: lower-cased,
        whitespace-collapsed first 200 chars. Two chunks whose text differs only
        by overlap/whitespace map to the same signature."""
        return " ".join(text.lower().split())[:200]

    @classmethod
    def _build_citations(cls, retrieved: list[tuple[Document, float]]) -> tuple[list[dict], list[dict]]:
        """Return (citations, chunks). Drops near-duplicate chunks (same content
        signature) so the user never sees several copies of essentially the same
        passage; each surviving chunk is its own source with its full content."""
        citations: list[dict] = []
        chunks: list[dict] = []
        seen_ids: set[str] = set()
        seen_sigs: set[str] = set()
        for doc, score in retrieved:
            filename = doc.metadata.get("source", "unknown")
            page = int(doc.metadata.get("page_number", 0))
            chunk_id = doc.metadata.get("chunk_id", "")
            doc_id = doc.metadata.get("doc_id", "")
            # Skip exact same chunk, or a different chunk with near-identical text.
            sig = cls._content_signature(doc.page_content)
            key = chunk_id or f"{filename}:{page}:{sig[:40]}"
            if key in seen_ids or sig in seen_sigs:
                continue
            seen_ids.add(key)
            seen_sigs.add(sig)
            chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "filename": filename,
                    "page": page,
                    "score": round(float(score), 4),
                    "content": doc.page_content,
                }
            )
            citations.append(
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "page": page,
                    "score": round(float(score), 4),
                    "chunk_id": chunk_id,
                    "preview": doc.metadata.get("preview", doc.page_content[:160]),
                }
            )
        return citations, chunks

    def _recommendations(self, context: str, question: str) -> list[str]:
        try:
            raw = self.llm.invoke(RECOMMEND_PROMPT, context=context[:2000], question=question)
            lines = [
                line.strip().lstrip("0123456789.)-• ").strip()
                for line in raw.splitlines()
                if line.strip()
            ]
            return [l for l in lines if l][:3]
        except Exception:
            logger.exception("Recommendation generation failed.")
            return []

    def _is_relevant(self, retrieved: list[tuple[Document, float]]) -> bool:
        if not retrieved:
            return False
        best = max(s for _, s in retrieved)
        return best >= settings.retrieval.min_relevance

    # --- shared prep ------------------------------------------------------
    def _prepare(self, question: str, history: str):
        lang = detect_language(question)
        english_q = question if lang == "en" else self._translate(question, "English")
        search_q = self._rephrase(english_q, history)
        return lang, english_q, search_q

    def _smalltalk_payload(
        self, *, question: str, lang: str, english_q: str, answer_en: str, start: float, translate_back: bool = True
    ) -> dict:
        """Build a full response object for a chit-chat reply (no retrieval)."""
        answer = answer_en if (lang == "en" or not translate_back) else self._translate(answer_en, language_name(lang))
        completion_tokens = estimate_tokens(answer_en)
        return {
            "response": answer,
            "citations": [],
            "chunks": [],
            "pdf_name": "",
            "pdf_path": "",
            "page_numbers": [],
            "recommendation_questions": [],
            "ragas_score": {"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0},
            "language": lang,
            "response_time": round(time.time() - start, 3),
            "token_usage": {"prompt_tokens": estimate_tokens(english_q), "completion_tokens": completion_tokens, "total_tokens": estimate_tokens(english_q) + completion_tokens},
            "_english_answer": answer_en,
            "_english_question": english_q,
        }

    # --- blocking ---------------------------------------------------------
    def run(self, *, question: str, history: str = "", user_id: str | None = None) -> dict:
        start = time.time()

        # Fast chit-chat path on the RAW question — instant, no translation
        # (langdetect is unreliable on short greetings, so we skip it here).
        category = smalltalk.detect(question)
        if category:
            return self._smalltalk_payload(
                question=question, lang="en", english_q=question,
                answer_en=smalltalk.response(category), start=start, translate_back=False,
            )

        lang = detect_language(question)
        english_q = question if lang == "en" else self._translate(question, "English")

        # Second check after translation catches greetings in other languages.
        category = smalltalk.detect(english_q)
        if category:
            return self._smalltalk_payload(
                question=question, lang=lang, english_q=english_q,
                answer_en=smalltalk.response(category), start=start,
            )

        search_q = self._rephrase(english_q, history)
        retrieved = self.retriever.retrieve(search_q, user_id=user_id)
        relevant = self._is_relevant(retrieved)
        context = self._assemble_context(retrieved) if relevant else ""
        citations, chunks = self._build_citations(retrieved) if relevant else ([], [])

        if not relevant:
            english_answer = settings.fallback_answer
            recommendations: list[str] = []
        else:
            english_answer = self.llm.invoke(
                RAG_PROMPT, history=history, context=context, question=english_q
            ).strip()
            recommendations = self._recommendations(context, english_q)

        answer = english_answer if lang == "en" else self._translate(english_answer, language_name(lang))

        ragas = ragas_eval.evaluate(english_q, english_answer, [c["content"] for c in chunks])

        prompt_tokens = estimate_tokens(context) + estimate_tokens(english_q) + estimate_tokens(history)
        completion_tokens = estimate_tokens(english_answer)
        elapsed = round(time.time() - start, 3)

        pdf_name = citations[0]["filename"] if citations else ""
        page_numbers = sorted({c["page"] for c in citations})

        return {
            "response": answer,
            "citations": citations,
            "chunks": chunks,
            "pdf_name": pdf_name,
            "pdf_path": "",  # filled by the route (needs doc lookup)
            "page_numbers": page_numbers,
            "recommendation_questions": recommendations,
            "ragas_score": ragas,
            "conversation_id": "",  # filled by the route
            "language": lang,
            "response_time": elapsed,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "_english_answer": english_answer,
            "_english_question": english_q,
        }

    # --- streaming --------------------------------------------------------
    def stream(self, *, question: str, history: str = "", user_id: str | None = None) -> Iterator[tuple]:
        start = time.time()

        # Fast chit-chat path on the RAW question (no translation round-trip).
        category = smalltalk.detect(question)
        st_payload: dict | None = None
        if category:
            st_payload = self._smalltalk_payload(
                question=question, lang="en", english_q=question,
                answer_en=smalltalk.response(category), start=start, translate_back=False,
            )
        else:
            lang0 = detect_language(question)
            english_q0 = question if lang0 == "en" else self._translate(question, "English")
            category = smalltalk.detect(english_q0)
            if category:
                st_payload = self._smalltalk_payload(
                    question=question, lang=lang0, english_q=english_q0,
                    answer_en=smalltalk.response(category), start=start,
                )

        if st_payload is not None:
            yield ("meta", {"citations": [], "chunks": [], "language": st_payload["language"]})
            words = st_payload["response"].split(" ")
            for i, w in enumerate(words):
                yield ("token", (" " if i else "") + w)
            yield ("final", st_payload)
            return

        lang = detect_language(question)
        english_q = question if lang == "en" else self._translate(question, "English")
        search_q = self._rephrase(english_q, history)
        retrieved = self.retriever.retrieve(search_q, user_id=user_id)
        relevant = self._is_relevant(retrieved)
        context = self._assemble_context(retrieved) if relevant else ""
        citations, chunks = self._build_citations(retrieved) if relevant else ([], [])

        yield ("meta", {"citations": citations, "chunks": chunks, "language": lang})

        # When the original language is English we can stream tokens directly.
        # For other languages we must translate the full answer, so we generate
        # then translate, then emit the translation as a single token block.
        collected: list[str] = []
        if not relevant:
            english_answer = settings.fallback_answer
            if lang == "en":
                yield ("token", english_answer)
            collected.append(english_answer)
            recommendations = []
        elif lang == "en":
            for tok in self.llm.stream(RAG_PROMPT, history=history, context=context, question=english_q):
                collected.append(tok)
                yield ("token", tok)
            english_answer = "".join(collected).strip()
            recommendations = self._recommendations(context, english_q)
        else:
            english_answer = self.llm.invoke(
                RAG_PROMPT, history=history, context=context, question=english_q
            ).strip()
            recommendations = self._recommendations(context, english_q)

        if lang == "en":
            answer = english_answer
        else:
            answer = self._translate(english_answer, language_name(lang))
            yield ("token", answer)

        ragas = ragas_eval.evaluate(english_q, english_answer, [c["content"] for c in chunks])
        prompt_tokens = estimate_tokens(context) + estimate_tokens(english_q) + estimate_tokens(history)
        completion_tokens = estimate_tokens(english_answer)
        elapsed = round(time.time() - start, 3)
        pdf_name = citations[0]["filename"] if citations else ""
        page_numbers = sorted({c["page"] for c in citations})

        yield (
            "final",
            {
                "response": answer,
                "citations": citations,
                "chunks": chunks,
                "pdf_name": pdf_name,
                "pdf_path": "",
                "page_numbers": page_numbers,
                "recommendation_questions": recommendations,
                "ragas_score": ragas,
                "language": lang,
                "response_time": elapsed,
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                "_english_answer": english_answer,
                "_english_question": english_q,
            },
        )
