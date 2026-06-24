"""
app/utils/helpers.py
====================
Small pure helpers shared across services: file hashing, safe filenames,
token estimation, and a tiny LRU-ish cache key builder.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sha256_bytes(data: bytes) -> str:
    """Stable content hash — used for dedupe and embedding cache keys."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def safe_filename(name: str) -> str:
    """Strip path components and unsafe characters from an uploaded filename."""
    base = Path(name).name
    base = unicodedata.normalize("NFKD", base)
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "upload"
    return cleaned[:200]


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — good enough for usage metrics."""
    if not text:
        return 0
    return max(1, len(text) // 4)
