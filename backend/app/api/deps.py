"""
app/api/deps.py
===============
Shared FastAPI dependencies: DB session + current-user resolution.

Auth is optional (config.auth.require_auth). When disabled, requests without a
token map to a shared "default" user — convenient for local single-user dev.
When enabled, a valid Bearer JWT is required and its subject is the user id.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.utils.security import decode_access_token

__all__ = ["get_db", "current_user"]


def current_user(authorization: str | None = Header(default=None)) -> str:
    """Resolve the acting user id from the Authorization header."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if token:
        username = decode_access_token(token)
        if username:
            return username
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if settings.auth.require_auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return settings.auth.default_user
