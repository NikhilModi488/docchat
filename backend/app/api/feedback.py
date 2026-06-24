"""app/api/feedback.py — thumbs up/down on assistant messages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import FeedbackRequest
from app.database import crud

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def submit_feedback(
    req: FeedbackRequest, db: Session = Depends(get_db), user: str = Depends(current_user)
) -> dict:
    if req.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'.")
    fb = crud.add_feedback(db, req.message_id, user, req.rating, req.comment)
    return {"id": fb.id, "message_id": req.message_id, "rating": req.rating}
