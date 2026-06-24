"""app/api/analytics.py — search analytics dashboard data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.database import crud

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    return crud.analytics(db, user)
