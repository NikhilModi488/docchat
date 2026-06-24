# Database Schema (SQLite via SQLAlchemy)

File: `backend/db/rag.db`. Models in `backend/app/database/models.py`.

```
users
  id PK · username UNIQUE · password_hash · created_at

documents
  id PK (uuid) · user_id (idx) · filename · path · content_hash (idx)
  pages · chunk_count · status (processing|ready|error) · error · upload_time
  └─ 1:N chunks   (cascade delete)

chunks
  id PK · doc_id FK→documents (cascade) · chunk_id (filename::p{n}::c{i})
  page · text · preview
  # Powers BM25 corpus, citations, and reindex.

conversations
  id PK (uuid) · user_id (idx) · title · created_at · updated_at
  └─ 1:N messages (cascade delete)

messages
  id PK · conversation_id FK→conversations (cascade) · role (user|assistant)
  content · language · citations(JSON) · chunks(JSON) · recommendations(JSON)
  ragas_score(JSON) · token_usage(JSON) · response_time · created_at
  └─ 1:N feedback (cascade delete)

feedback
  id PK · message_id FK→messages (cascade) · user_id · rating (up|down) · comment · created_at

query_logs
  id PK · user_id (idx) · conversation_id · question · language
  response_time · prompt_tokens · completion_tokens
  faithfulness · answer_relevancy · context_precision · created_at
  # Telemetry source for the analytics dashboard.
```

## Vector store
FAISS index persisted at `backend/vectorstore/` (`index.faiss` + `index.pkl`).
Each chunk's metadata carries `doc_id` and `user_id`, enabling per-document
deletion and per-user retrieval isolation. The SQLite `chunks` table mirrors the
chunk text so the index can be rebuilt and BM25 can run without re-reading files.

## Notes
- Tables are created automatically on startup (`init_db`).
- To use PostgreSQL instead, set `RAG_DATABASE_URL=postgresql+psycopg://…`
  (add the driver to requirements); the ORM models are backend-agnostic.
