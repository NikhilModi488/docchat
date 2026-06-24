"""
app/services/conversation_service.py
====================================
Conversation memory helpers backed by SQLite.

Builds the plain-text transcript the prompts expect from the most recent N
messages of a conversation, and ensures a conversation row exists.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.database import crud


def ensure_conversation(db: Session, conversation_id: str | None, user_id: str) -> str:
    """Return a valid conversation id, creating a new conversation if needed."""
    if conversation_id:
        conv = crud.get_conversation(db, conversation_id, user_id)
        if conv:
            return conv.id
    return crud.create_conversation(db, user_id).id


def history_text(db: Session, conversation_id: str) -> str:
    """Render the last N turns as a transcript for the prompt."""
    msgs = crud.recent_messages(db, conversation_id, settings.memory.max_interactions * 2)
    if not msgs:
        return "(no prior conversation)"
    lines = []
    for m in msgs:
        speaker = "User" if m.role == "user" else "Assistant"
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)
