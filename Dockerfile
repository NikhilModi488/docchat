# syntax=docker/dockerfile:1
#
# All-in-one image: builds the React frontend, then runs the FastAPI backend +
# Ollama (local LLM) in a single container that serves the UI and the API on
# one port. Suitable for single-container hosts such as Hugging Face Spaces.
#
#   Build:  docker build -t docchat .
#   Run:    docker run -p 7860:7860 docchat
#   Open:   http://localhost:7860
#
# The multi-service docker-compose.yml remains the recommended way to run
# locally; this image is for platforms that build a single Dockerfile.

# --- 1) Build the frontend ------------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- 2) Runtime: Python + Ollama -----------------------------------------
FROM python:3.11-slim

# Ollama + Tesseract (optional OCR) + libs some wheels need.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates zstd tesseract-ocr libgl1 libglib2.0-0 \
    && curl -fsSL https://ollama.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_HOST=http://127.0.0.1:11434 \
    OLLAMA_MODELS=/data/.ollama/models \
    HOME=/data \
    RAG_LLM_MODEL=llama3.2 \
    RAG_STATIC_DIR=/app/static \
    RAG_DATABASE_URL=sqlite:////data/rag.db \
    RAG_CORS_ORIGINS=* \
    HF_HOME=/data/hf \
    SENTENCE_TRANSFORMERS_HOME=/data/hf \
    PORT=7860

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/app ./app
COPY backend/data ./data
COPY --from=frontend /fe/dist ./static

# Writable data dir for SQLite, FAISS index, uploads, model + HF caches.
# HF Spaces runs as uid 1000; make these writable regardless of user.
RUN mkdir -p /data/hf /data/.ollama/models uploads vectorstore logs \
    && chmod -R 777 /data /app/uploads /app/vectorstore /app/logs

COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7860
ENTRYPOINT ["/entrypoint.sh"]
