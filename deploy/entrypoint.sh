#!/usr/bin/env bash
# Start Ollama, ensure the chat model is present, then launch the API+UI server.
set -e

PORT="${PORT:-7860}"
MODEL="${RAG_LLM_MODEL:-llama3.2}"

echo "[entrypoint] starting ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for the Ollama HTTP API to come up (max ~60s).
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[entrypoint] ollama is up."
    break
  fi
  sleep 1
done

echo "[entrypoint] pulling model '${MODEL}' (first run downloads ~2GB; cached afterwards)..."
ollama pull "${MODEL}" || echo "[entrypoint] WARN: model pull failed; will retry on first request."

echo "[entrypoint] launching DocChat on :${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
