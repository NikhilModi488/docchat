"""Phase 1 verification: ingest a sample PDF, assert vectors + DB rows, then delete."""
from __future__ import annotations

from pathlib import Path

from app.database.session import SessionLocal, init_db
from app.database import crud
from app.services import ingestion_service
from app.services.resources import get_store

init_db()
db = SessionLocal()
store = get_store()

sample = Path("data/HR_Policy.pdf")
data = sample.read_bytes()
before = store.count()
print(f"FAISS chunks before: {before}")

res = ingestion_service.ingest_file(db, user_id="tester", filename="HR_Policy.pdf", data=data)
print("Ingest result:", res)

after = store.count()
docs = crud.list_documents(db, "tester")
print(f"FAISS chunks after: {after} (+{after - before})")
print(f"DB documents for tester: {len(docs)}; chunk_count={docs[0].chunk_count}, pages={docs[0].pages}, status={docs[0].status}")
assert after > before, "vectors not added"
assert docs and docs[0].chunk_count == res["chunks"], "chunk count mismatch"

# delete and confirm removal
ok = ingestion_service.delete_document(db, res["doc_id"], "tester")
post = store.count()
docs2 = crud.list_documents(db, "tester")
print(f"Deleted={ok}; FAISS chunks after delete: {post}; DB docs: {len(docs2)}")
assert post == before, "vectors not fully removed on delete"
assert len(docs2) == 0, "doc row not removed"
print("\nPHASE 1 OK: ingest -> vectors+rows added; delete -> vectors+rows removed.")
db.close()
