---
title: DocChat
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# DocChat — Document RAG Chatbot (local LLM)

Ask questions over your own documents. Hybrid retrieval + reranking, citations
with an in-app PDF viewer, multilingual support, and SSE streaming — running a
local LLM (`llama3.2`) via Ollama, all in one container.

> ⚠️ **Free CPU Space caveats:** the first request after the Space wakes is slow
> while the model loads, and answers take ~20–60s on CPU. Uploaded documents and
> the index are stored on ephemeral disk and reset when the Space restarts.

Source & docs: https://github.com/NikhilModi488/docchat

**This `README.md` (with the YAML header above) must be at the root of the
Hugging Face Space repo** so the Space builds with the Docker SDK on port 7860.
