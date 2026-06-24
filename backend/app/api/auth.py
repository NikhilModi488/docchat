"""app/api/auth.py — local login (register + token)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.api.schemas import RegisterRequest, TokenResponse
from app.database import crud
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if crud.get_user(db, req.username):
        raise HTTPException(status_code=409, detail="Username already taken.")
    crud.create_user(db, req.username, hash_password(req.password))
    token = create_access_token(req.username)
    return TokenResponse(access_token=token, username=req.username)


@router.post("/login", response_model=TokenResponse)
def login(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = crud.get_user(db, req.username)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = create_access_token(req.username)
    return TokenResponse(access_token=token, username=req.username)


@router.get("/me")
def me(user: str = Depends(current_user)) -> dict:
    return {"username": user}
