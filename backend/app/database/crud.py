"""
app/database/crud.py
====================
Thin data-access helpers over the ORM models. Keeping queries here means
routers/services stay readable and DB concerns live in one place.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import models


def _uuid() -> str:
    return uuid.uuid4().hex


# --- users ----------------------------------------------------------------
def get_user(db: Session, username: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.username == username))


def create_user(db: Session, username: str, password_hash: str) -> models.User:
    user = models.User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --- documents ------------------------------------------------------------
def create_document(
    db: Session, *, user_id: str, filename: str, path: str, content_hash: str
) -> models.Document:
    doc = models.Document(
        id=_uuid(),
        user_id=user_id,
        filename=filename,
        path=path,
        content_hash=content_hash,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def finalize_document(
    db: Session, doc_id: str, *, pages: int, chunk_count: int, status: str, error: str = ""
) -> None:
    doc = db.get(models.Document, doc_id)
    if not doc:
        return
    doc.pages = pages
    doc.chunk_count = chunk_count
    doc.status = status
    doc.error = error
    db.commit()


def add_chunks(db: Session, doc_id: str, chunks: list[dict]) -> None:
    db.add_all(
        [
            models.Chunk(
                doc_id=doc_id,
                chunk_id=c["chunk_id"],
                page=c.get("page", 0),
                text=c["text"],
                preview=c.get("preview", "")[:300],
            )
            for c in chunks
        ]
    )
    db.commit()


def list_documents(db: Session, user_id: str) -> list[models.Document]:
    return list(
        db.scalars(
            select(models.Document)
            .where(models.Document.user_id == user_id)
            .order_by(models.Document.upload_time.desc())
        )
    )


def get_document(db: Session, doc_id: str, user_id: str | None = None) -> models.Document | None:
    doc = db.get(models.Document, doc_id)
    if doc and user_id is not None and doc.user_id != user_id:
        return None
    return doc


def find_document_by_hash(db: Session, user_id: str, content_hash: str) -> models.Document | None:
    return db.scalar(
        select(models.Document).where(
            models.Document.user_id == user_id,
            models.Document.content_hash == content_hash,
        )
    )


def find_documents_by_filename(db: Session, user_id: str, filename: str) -> list[models.Document]:
    """All of a user's documents that share the given (already-sanitised) filename."""
    return list(
        db.scalars(
            select(models.Document).where(
                models.Document.user_id == user_id,
                models.Document.filename == filename,
            )
        )
    )


def delete_document(db: Session, doc_id: str) -> None:
    db.execute(delete(models.Document).where(models.Document.id == doc_id))
    db.commit()


def clear_chunks(db: Session, doc_id: str) -> None:
    """Delete only a document's chunk rows (keeps the documents row)."""
    db.execute(delete(models.Chunk).where(models.Chunk.doc_id == doc_id))
    db.commit()


# --- conversations & messages --------------------------------------------
def create_conversation(db: Session, user_id: str, title: str = "New Chat") -> models.Conversation:
    conv = models.Conversation(id=_uuid(), user_id=user_id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(db: Session, conv_id: str, user_id: str | None = None) -> models.Conversation | None:
    conv = db.get(models.Conversation, conv_id)
    if conv and user_id is not None and conv.user_id != user_id:
        return None
    return conv


def list_conversations(db: Session, user_id: str) -> list[models.Conversation]:
    return list(
        db.scalars(
            select(models.Conversation)
            .where(models.Conversation.user_id == user_id)
            .order_by(models.Conversation.updated_at.desc())
        )
    )


def rename_conversation(db: Session, conv_id: str, title: str) -> None:
    conv = db.get(models.Conversation, conv_id)
    if conv:
        conv.title = title[:300]
        db.commit()


def delete_conversation(db: Session, conv_id: str) -> None:
    db.execute(delete(models.Conversation).where(models.Conversation.id == conv_id))
    db.commit()


def add_message(db: Session, conv_id: str, role: str, content: str, **extra) -> models.Message:
    msg = models.Message(conversation_id=conv_id, role=role, content=content, **extra)
    db.add(msg)
    conv = db.get(models.Conversation, conv_id)
    if conv:
        conv.updated_at = datetime.now(timezone.utc)
        # Auto-title the conversation from the first user message.
        if role == "user" and conv.title == "New Chat":
            conv.title = content.strip()[:60] or "New Chat"
    db.commit()
    db.refresh(msg)
    return msg


def recent_messages(db: Session, conv_id: str, limit: int) -> list[models.Message]:
    msgs = list(
        db.scalars(
            select(models.Message)
            .where(models.Message.conversation_id == conv_id)
            .order_by(models.Message.created_at.desc())
            .limit(limit)
        )
    )
    return list(reversed(msgs))


# --- feedback -------------------------------------------------------------
def add_feedback(db: Session, message_id: int, user_id: str, rating: str, comment: str = "") -> models.Feedback:
    fb = models.Feedback(message_id=message_id, user_id=user_id, rating=rating, comment=comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


# --- telemetry ------------------------------------------------------------
def log_query(db: Session, **fields) -> None:
    db.add(models.QueryLog(**fields))
    db.commit()


# --- analytics ------------------------------------------------------------
def analytics(db: Session, user_id: str) -> dict:
    doc_filter = models.Document.user_id == user_id
    total_docs = db.scalar(select(func.count()).select_from(models.Document).where(doc_filter)) or 0
    total_chunks = (
        db.scalar(select(func.coalesce(func.sum(models.Document.chunk_count), 0)).where(doc_filter)) or 0
    )
    total_convs = (
        db.scalar(
            select(func.count()).select_from(models.Conversation).where(models.Conversation.user_id == user_id)
        )
        or 0
    )

    log_filter = models.QueryLog.user_id == user_id
    avg_rt = db.scalar(select(func.avg(models.QueryLog.response_time)).where(log_filter)) or 0.0
    avg_faith = db.scalar(select(func.avg(models.QueryLog.faithfulness)).where(log_filter)) or 0.0
    avg_rel = db.scalar(select(func.avg(models.QueryLog.answer_relevancy)).where(log_filter)) or 0.0
    avg_prec = db.scalar(select(func.avg(models.QueryLog.context_precision)).where(log_filter)) or 0.0
    total_prompt = db.scalar(select(func.coalesce(func.sum(models.QueryLog.prompt_tokens), 0)).where(log_filter)) or 0
    total_completion = (
        db.scalar(select(func.coalesce(func.sum(models.QueryLog.completion_tokens), 0)).where(log_filter)) or 0
    )

    top_q = db.execute(
        select(models.QueryLog.question, func.count().label("n"))
        .where(log_filter)
        .group_by(models.QueryLog.question)
        .order_by(func.count().desc())
        .limit(10)
    ).all()

    up = db.scalar(
        select(func.count()).select_from(models.Feedback).where(
            models.Feedback.user_id == user_id, models.Feedback.rating == "up"
        )
    ) or 0
    down = db.scalar(
        select(func.count()).select_from(models.Feedback).where(
            models.Feedback.user_id == user_id, models.Feedback.rating == "down"
        )
    ) or 0

    return {
        "total_documents": int(total_docs),
        "total_chunks": int(total_chunks),
        "total_conversations": int(total_convs),
        "average_response_time": round(float(avg_rt), 3),
        "average_ragas": {
            "faithfulness": round(float(avg_faith), 3),
            "answer_relevancy": round(float(avg_rel), 3),
            "context_precision": round(float(avg_prec), 3),
        },
        "token_usage": {
            "prompt_tokens": int(total_prompt),
            "completion_tokens": int(total_completion),
            "total_tokens": int(total_prompt + total_completion),
        },
        "top_questions": [{"question": q, "count": int(n)} for q, n in top_q],
        "feedback": {"up": int(up), "down": int(down)},
    }
