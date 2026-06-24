"""
app/database/session.py
=======================
SQLAlchemy engine/session setup (SQLite by default).

`get_db` is a FastAPI dependency yielding a scoped session. `init_db` creates
tables on startup. SQLite needs `check_same_thread=False` because FastAPI may
touch the session from worker threads.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)


if _is_sqlite:
    # SQLite ignores FOREIGN KEY constraints (and ON DELETE CASCADE) unless this
    # pragma is enabled per-connection. Without it, deleting a document leaves
    # orphaned chunk/message/feedback rows behind.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):  # pragma: no cover
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables. Import models so they register with Base.metadata."""
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
