"""
app/utils/security.py
=====================
Lightweight security helpers: password hashing, JWT issue/verify, file
validation, and a basic prompt-injection sanitiser.

Kept dependency-light (passlib + python-jose) per the "pragmatic core" scope —
no OAuth, no antivirus.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# Patterns commonly used in prompt-injection attempts. We don't block the
# request (false positives hurt UX); we annotate so the system prompt can warn.
_INJECTION_PATTERNS = re.compile(
    r"(ignore (all|previous|above) instructions|disregard the (system|above)|"
    r"you are now|reveal your (system )?prompt|act as)",
    re.IGNORECASE,
)


# --- passwords ------------------------------------------------------------
def _to_bytes(raw: str) -> bytes:
    # bcrypt hard-limits inputs to 72 bytes; truncate defensively.
    return raw.encode("utf-8")[:72]


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_to_bytes(raw), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(raw), hashed.encode("utf-8"))
    except Exception:
        return False


# --- JWT ------------------------------------------------------------------
def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.auth.token_expire_minutes
    )
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the username (sub) if the token is valid, else None."""
    try:
        payload = jwt.decode(
            token, settings.auth.secret_key, algorithms=[settings.auth.algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None


# --- prompt-injection sanitiser -------------------------------------------
def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION_PATTERNS.search(text or ""))


# --- file validation ------------------------------------------------------
def validate_upload(filename: str, size_bytes: int) -> tuple[bool, str]:
    """Return (ok, reason). Enforces extension allow-list and size cap."""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext not in settings.ingestion.allowed_extensions:
        return False, f"Unsupported file type '{ext}'. Allowed: {settings.ingestion.allowed_extensions}"
    max_bytes = settings.ingestion.max_file_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"File too large ({size_bytes/1e6:.1f} MB > {settings.ingestion.max_file_mb} MB)."
    if size_bytes == 0:
        return False, "Empty file."
    return True, "ok"
