"""Phase 2 verification: ingest a doc, run a query through the full RAG pipeline."""
from __future__ import annotations

import json
from pathlib import Path

from app.database.session import SessionLocal, init_db
from app.services import ingestion_service
from app.rag.pipeline import RAGPipeline

init_db()
db = SessionLocal()

data = Path("data/HR_Policy.pdf").read_bytes()
res = ingestion_service.ingest_file(db, user_id="p2", filename="HR_Policy.pdf", data=data)
print("Ingested:", res["chunks"], "chunks")

pipe = RAGPipeline()
out = pipe.run(question="What is the leave policy?", history="", user_id="p2")

print("\n--- RESPONSE ---")
print(out["response"][:400])
print("\nlanguage:", out["language"])
print("citations:", len(out["citations"]), "| chunks:", len(out["chunks"]))
print("page_numbers:", out["page_numbers"])
print("recommendations:", out["recommendation_questions"])
print("ragas_score:", out["ragas_score"])
print("response_time:", out["response_time"], "| tokens:", out["token_usage"])

assert out["response"], "empty response"
assert "language" in out and "ragas_score" in out
print("\nPHASE 2 OK (English query end-to-end).")

# cleanup
ingestion_service.delete_document(db, res["doc_id"], "p2")
db.close()
