"""app/api/conversations.py — list, get, rename, delete, new conversation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import RenameRequest
from app.database import crud

router = APIRouter(tags=["conversations"])


def _conv_summary(conv) -> dict:
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _msg_to_dict(m) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "language": m.language,
        "citations": m.citations or [],
        "chunks": m.chunks or [],
        "recommendation_questions": m.recommendations or [],
        "ragas_score": m.ragas_score or {},
        "token_usage": m.token_usage or {},
        "response_time": m.response_time,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.post("/conversation")
def new_conversation(db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    conv = crud.create_conversation(db, user)
    return _conv_summary(conv)


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    return {"conversations": [_conv_summary(c) for c in crud.list_conversations(db, user)]}


@router.get("/conversation/{conv_id}")
def get_conversation(conv_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    conv = crud.get_conversation(db, conv_id, user)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {**_conv_summary(conv), "messages": [_msg_to_dict(m) for m in conv.messages]}


@router.patch("/conversation/{conv_id}")
def rename_conversation(
    conv_id: str, req: RenameRequest, db: Session = Depends(get_db), user: str = Depends(current_user)
) -> dict:
    conv = crud.get_conversation(db, conv_id, user)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    crud.rename_conversation(db, conv_id, req.title)
    return {"id": conv_id, "title": req.title}


@router.delete("/conversation/{conv_id}")
def delete_conversation(conv_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    conv = crud.get_conversation(db, conv_id, user)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    crud.delete_conversation(db, conv_id)
    return {"deleted": conv_id}
