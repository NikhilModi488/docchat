"""
scripts/reconcile_index.py
==========================
Repair index/DB drift. Two steps:

  1. Delete orphaned rows left by pre-cascade deletes (chunks without a parent
     document, messages without a conversation, feedback without a message).
  2. Rebuild the FAISS index from the surviving chunk rows so the vector store
     exactly matches the database (re-embeds chunk text — deterministic).

After this, FAISS vector count == SQLite chunk rows == sum(document.chunk_count).

Usage: python scripts/reconcile_index.py
"""

from __future__ import annotations

from langchain_core.documents import Document
from sqlalchemy import delete, select

from app.database import models
from app.database.session import SessionLocal, init_db
from app.services.resources import get_store


def reconcile() -> None:
    init_db()
    db = SessionLocal()

    # --- 1) prune orphans ------------------------------------------------
    doc_ids = set(db.scalars(select(models.Document.id)))
    conv_ids = set(db.scalars(select(models.Conversation.id)))
    msg_ids = set(db.scalars(select(models.Message.id)))

    orphan_chunks = db.execute(
        delete(models.Chunk).where(models.Chunk.doc_id.notin_(doc_ids or {""}))
    ).rowcount
    orphan_msgs = db.execute(
        delete(models.Message).where(models.Message.conversation_id.notin_(conv_ids or {""}))
    ).rowcount
    orphan_fb = db.execute(
        delete(models.Feedback).where(models.Feedback.message_id.notin_(msg_ids or {-1}))
    ).rowcount
    db.commit()
    print(f"Pruned orphans -> chunks:{orphan_chunks} messages:{orphan_msgs} feedback:{orphan_fb}")

    # --- 2) rebuild FAISS from surviving chunks --------------------------
    store = get_store()
    store.clear()

    docs_by_id = {d.id: d for d in db.scalars(select(models.Document))}
    chunks = list(db.scalars(select(models.Chunk)))
    rebuilt: list[Document] = []
    for c in chunks:
        d = docs_by_id.get(c.doc_id)
        if not d:
            continue
        rebuilt.append(
            Document(
                page_content=c.text,
                metadata={
                    "source": d.filename,
                    "page_number": c.page,
                    "chunk_id": c.chunk_id,
                    "preview": c.preview,
                    "doc_id": d.id,
                    "user_id": d.user_id,
                },
            )
        )
    if rebuilt:
        store.add_documents(rebuilt)

    # --- verify ----------------------------------------------------------
    faiss = store.count()
    rows = db.query(models.Chunk).count()
    meta = sum(d.chunk_count for d in docs_by_id.values())
    print(f"FAISS={faiss}  SQLite chunks={rows}  sum(chunk_count)={meta}")
    print("CONSISTENT" if faiss == rows == meta else "STILL MISMATCHED")
    db.close()


if __name__ == "__main__":
    reconcile()
