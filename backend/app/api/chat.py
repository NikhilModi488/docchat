"""app/api/chat.py — /query (blocking) and /stream-query (SSE)."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import QueryRequest, QueryResponse
from app.database import crud
from app.database.session import SessionLocal
from app.rag.pipeline import RAGPipeline
from app.services import conversation_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])

# One pipeline instance reused across requests (LLM clients are cached inside).
_pipeline = RAGPipeline()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _persist(db: Session, conv_id: str, user: str, question: str, result: dict) -> int:
    """Store user + assistant messages and a query log; return assistant msg id."""
    crud.add_message(db, conv_id, "user", question, language=result.get("language", "en"))
    assistant = crud.add_message(
        db,
        conv_id,
        "assistant",
        result["response"],
        language=result.get("language", "en"),
        citations=result.get("citations"),
        chunks=result.get("chunks"),
        recommendations=result.get("recommendation_questions"),
        ragas_score=result.get("ragas_score"),
        token_usage=result.get("token_usage"),
        response_time=result.get("response_time", 0.0),
    )
    ragas = result.get("ragas_score", {})
    usage = result.get("token_usage", {})
    crud.log_query(
        db,
        user_id=user,
        conversation_id=conv_id,
        question=result.get("_english_question", question),
        language=result.get("language", "en"),
        response_time=result.get("response_time", 0.0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        faithfulness=ragas.get("faithfulness", 0.0),
        answer_relevancy=ragas.get("answer_relevancy", 0.0),
        context_precision=ragas.get("context_precision", 0.0),
    )
    return assistant.id


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db), user: str = Depends(current_user)) -> QueryResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Empty query.")
    conv_id = conversation_service.ensure_conversation(db, req.conversation_id, user)
    history = conversation_service.history_text(db, conv_id)

    result = _pipeline.run(question=req.query, history=history, user_id=user)
    msg_id = _persist(db, conv_id, user, req.query, result)

    result["conversation_id"] = conv_id
    result.pop("_english_answer", None)
    result.pop("_english_question", None)
    return QueryResponse(**result, message_id=msg_id)


@router.post("/stream-query")
def stream_query(req: QueryRequest, user: str = Depends(current_user)) -> StreamingResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Empty query.")

    def event_stream() -> Iterator[str]:
        # Use a dedicated DB session: the generator outlives the request-scoped one.
        db = SessionLocal()
        try:
            conv_id = conversation_service.ensure_conversation(db, req.conversation_id, user)
            history = conversation_service.history_text(db, conv_id)
            yield _sse({"type": "conversation", "conversation_id": conv_id})

            final: dict | None = None
            for kind, payload in _pipeline.stream(question=req.query, history=history, user_id=user):
                if kind == "meta":
                    yield _sse({"type": "sources", **payload})
                elif kind == "token":
                    yield _sse({"type": "token", "text": payload})
                elif kind == "final":
                    final = payload

            if final is not None:
                msg_id = _persist(db, conv_id, user, req.query, final)
                final["conversation_id"] = conv_id
                final.pop("_english_answer", None)
                final.pop("_english_question", None)
                yield _sse({"type": "final", "message_id": msg_id, **final})
            yield _sse({"type": "done"})
        except Exception as exc:  # surface cleanly to the client
            logger.exception("Stream failed")
            yield _sse({"type": "error", "message": str(exc)})
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
