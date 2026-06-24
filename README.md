# DocChat — Production-Grade Document RAG Chatbot (Local LLMs)

A ChatGPT/Perplexity-style assistant that answers questions over **your own
documents**, running **fully locally**: local LLM via **Ollama**, local
embeddings (SentenceTransformers), **FAISS** vector store, and **SQLite**
metadata — no external APIs, no data leaving the machine.

![stack](https://img.shields.io/badge/backend-FastAPI-009688) ![stack](https://img.shields.io/badge/frontend-React%20+%20TS%20+%20Tailwind-3178c6) ![stack](https://img.shields.io/badge/vector-FAISS-orange) ![stack](https://img.shields.io/badge/llm-Ollama%20llama3.2-5b4bdb)

## Features

**Retrieval pipeline** — language detection → translate to English → follow-up
resolution & query rephrase → **hybrid retrieval (FAISS dense + BM25)** →
**CrossEncoder reranking (top 5)** → context compression → grounded answer →
citations → 3 recommended questions → RAGAS scoring → translate back → **SSE
streaming**.

**Frontend** — streaming chat with markdown & code blocks, copy / regenerate /
stop / 👍👎, conversation sidebar (new / rename / delete / resume), drag-and-drop
multi-file upload with progress, knowledge-base management (search / filter /
reindex / delete), **citations panel**, **in-app PDF viewer** (rasterised cited
page with zoom / download / fullscreen), one-click follow-ups, an **analytics
dashboard**, multilingual input, local login, and dark/light themes.

**Hardening** — file validation, prompt-injection-aware system prompt, rate
limiting, per-user document isolation, structured logging, and a hallucination
guard ("I could not find sufficient information…").

## Architecture

```
frontend/ (React+TS+Tailwind, Vite)  ──/api (SSE)──►  backend/ (FastAPI)
                                                        ├─ ingestion (pdf/docx/txt/md/pptx, OCR, tables)
                                                        ├─ embeddings (MiniLM) ─► FAISS vectorstore/
                                                        ├─ retriever (hybrid) + CrossEncoder reranker
                                                        ├─ rag pipeline (llama3.2 via Ollama)
                                                        ├─ evaluation (RAGAS heuristic)
                                                        └─ database (SQLite: docs, chunks, convos, feedback, logs)
```

See [docs/API.md](docs/API.md) and [docs/DATABASE.md](docs/DATABASE.md).

## Prerequisites
- **Python 3.11**, **Node 20+**
- **[Ollama](https://ollama.com)** running locally with a model pulled:
  ```bash
  ollama pull llama3.2
  ```
- (Optional) **Tesseract** on PATH for OCR of scanned PDFs.

> ⚠️ **Windows/conda note:** this project is pinned to **torch 2.2.2+cpu**
> (newer torch crashes with `WinError 1114` on some setups). The pins in
> `backend/requirements.txt` are deliberate — don't bump torch.

## Quick start (local dev)

**Backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env            # adjust if needed
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxies /api → :8000)
```

Open http://localhost:5173, go to **Knowledge Base**, upload a document (sample
PDFs ship in `backend/data/`), then ask questions in **Chat**.

## Docker (one command, fully self-contained)
```bash
docker compose up --build
# frontend → http://localhost:8080   backend → http://localhost:8000
```
This starts **everything** — Ollama, the chat model (auto-pulled on first run),
the FastAPI backend, and the nginx-served React frontend — with **no host
dependencies**. The first start downloads the `llama3.2` model (~2 GB) into a
named volume, so it's cached for subsequent runs. FAISS index, uploads, the
SQLite DB, and Ollama models all persist in named volumes.

> First boot takes a few minutes while the model downloads. Override the model
> with `RAG_LLM_MODEL=<name> docker compose up`, and set a strong
> `RAG_JWT_SECRET` for any public instance.

## Configuration
All knobs live in `backend/.env` (see `.env.example`): models, chunking,
retrieval/reranking, RAGAS mode, auth toggle, CORS, rate limit. Notable:
- `RAG_REQUIRE_AUTH=false` — single-user local mode (no login required).
- `RAG_EMBED_MODEL` — swap to `BAAI/bge-small-en-v1.5` for higher quality.
- `RAG_RAGAS_FULL=false` — fast heuristic scores; `true` enables the real
  `ragas` library (heavy, needs a judge LLM).

## Testing
```bash
cd backend  && pytest -q          # unit + integration (LLM stubbed)
cd frontend && npm test           # Vitest
```

## Production deployment
- Serve the backend with multiple workers behind a reverse proxy:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` (or `gunicorn -k
  uvicorn.workers.UvicornWorker`). Keep SSE endpoints un-buffered at the proxy
  (`proxy_buffering off`, see `frontend/nginx.conf`).
- Set a strong `RAG_JWT_SECRET`, `RAG_REQUIRE_AUTH=true`, and restrict
  `RAG_CORS_ORIGINS`.
- Mount persistent volumes for `vectorstore/`, `uploads/`, `db/`.
- Build the frontend (`npm run build`) and serve `dist/` via nginx (Dockerfile
  provided).

## Project layout
```
backend/   app/{api,services,llm,embeddings,vector_store,retriever,rag,
                ingestion,database,evaluation,utils}  · data/ · tests/ · scripts/
frontend/  src/{components,pages,hooks,services,contexts,layouts,lib}
docs/      API.md · DATABASE.md
docker-compose.yml
```

## Deliverables checklist
Backend ✓ · Frontend ✓ · DB schema ✓ · FAISS setup ✓ · API docs ✓ ·
requirements.txt ✓ · Docker + Compose ✓ · README ✓ · sample PDFs ✓ ·
SSE streaming ✓ · unit + integration tests ✓ · deployment notes ✓.
