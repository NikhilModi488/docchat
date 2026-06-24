# Deployment

DocChat ships as a single all-in-one image ([`Dockerfile`](Dockerfile)) that
builds the frontend and runs the FastAPI backend + Ollama together, serving the
UI and API on **one port (7860)**. The multi-service
[`docker-compose.yml`](docker-compose.yml) is the recommended way to run locally.

## Run the all-in-one image anywhere
```bash
docker build -t docchat .
docker run -p 7860:7860 docchat
# open http://localhost:7860  (first run downloads the model, ~2GB)
```

## Free public hosting — Hugging Face Spaces (CPU, 16 GB RAM)

The free tier can run the full local-LLM stack. Caveats: CPU inference is slow
(~20–60s/answer), the Space sleeps when idle and cold-starts, and free-tier disk
is ephemeral (uploads/index reset on restart).

1. Create a free account at https://huggingface.co and a **New Space** →
   **Docker** (blank template), name it `docchat`, visibility **Public**.
2. The Space is a git repo. Push this project to it, with the Hugging Face
   `README.md` (the one in [`deploy/huggingface/README.md`](deploy/huggingface/README.md),
   which carries the required `sdk: docker` / `app_port: 7860` front-matter) at
   the repo **root**:
   ```bash
   git clone https://huggingface.co/spaces/<your-user>/docchat hf-space
   cd hf-space
   # copy the project in, then use the HF front-matter README at the root:
   cp -r /path/to/docchat/* .
   cp deploy/huggingface/README.md ./README.md
   git add -A && git commit -m "Deploy DocChat" && git push
   ```
   (Authenticate the push with your Hugging Face username + an access token
   created at https://huggingface.co/settings/tokens — `write` scope.)
3. The Space builds the root `Dockerfile` and boots. Watch the **Logs** tab;
   first build takes several minutes (installs torch + Ollama, pulls the model).
4. Your public URL: `https://huggingface.co/spaces/<your-user>/docchat`.

### Configuration (Space → Settings → Variables and secrets)
- `RAG_LLM_MODEL` — chat model to pull (default `llama3.2`; try `qwen2.5:1.5b`
  for faster CPU responses).
- `RAG_REQUIRE_AUTH` — set `true` to require login.
- `RAG_JWT_SECRET` — set a strong secret for any non-throwaway instance.

## Paid alternatives (faster / persistent)
- **Fly.io / Render** with a Docker deploy and a plan that has ≥8 GB RAM for
  Ollama, plus a persistent volume mounted at `/data`.
- Or set `LLM_BACKEND=claude` + `ANTHROPIC_API_KEY` to run a lightweight backend
  (no local model) on a small/cheap instance.
