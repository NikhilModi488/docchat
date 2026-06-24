"""
scripts/reset_all.py
====================
DESTRUCTIVE maintenance utility — wipes ALL indexed data for EVERY user:

  * the FAISS vector index (vectorstore/index.*),
  * every database table (documents, chunks, conversations, messages,
    feedback, query_logs) — users are kept by default,
  * every uploaded file under uploads/.

Bundled sample documents in data/ are left untouched.

Usage:
    python scripts/reset_all.py --yes              # wipe documents/convos/vectors/files
    python scripts/reset_all.py --yes --users      # also delete user accounts

NOTE: if the API server is running it holds the FAISS index in memory — restart
it after running this so it reloads the now-empty index.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from app.config import UPLOAD_DIR
from app.database import models
from app.database.session import SessionLocal, init_db
from app.services.resources import get_store


def reset(*, drop_users: bool) -> None:
    init_db()
    db = SessionLocal()

    # 1) Vector index.
    store = get_store()
    before = store.count()
    store.clear()
    print(f"FAISS: cleared {before} vectors.")

    # 2) Database rows (order respects FK cascades; explicit for clarity).
    counts = {}
    for model in (models.Feedback, models.Message, models.QueryLog, models.Chunk,
                  models.Conversation, models.Document):
        counts[model.__tablename__] = db.query(model).delete()
    if drop_users:
        counts["users"] = db.query(models.User).delete()
    db.commit()
    db.close()
    for table, n in counts.items():
        print(f"DB: deleted {n} rows from {table}")

    # 3) Uploaded files (keep the uploads/ dir itself).
    removed = 0
    if UPLOAD_DIR.exists():
        for child in UPLOAD_DIR.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
            except Exception as exc:
                print(f"  warn: could not remove {child}: {exc}")
    print(f"Files: removed {removed} upload entries from {UPLOAD_DIR}")

    print("\nDONE — all indexed data cleared for every user. Restart the API server.")


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        print("Refusing to run without --yes (this is destructive).")
        print("Run: python scripts/reset_all.py --yes [--users]")
        sys.exit(1)
    reset(drop_users="--users" in sys.argv)
