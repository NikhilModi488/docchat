"""Shared pytest fixtures. The LLM is stubbed so tests are fast and offline."""
from __future__ import annotations

import io
import os
import tempfile

# Isolate tests from the real DB/vector store: point at a throwaway temp dir.
# Must run BEFORE any `app.*` import so app.config picks these up.
_TMP = tempfile.mkdtemp(prefix="docchat_test_")
os.environ["RAG_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["RAG_RATE_LIMIT"] = "100000/minute"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from app.database.session import init_db

    init_db()
    return TestClient(app)


@pytest.fixture()
def stub_pipeline(monkeypatch):
    """Replace the chat pipeline's run/stream with deterministic stubs."""
    from app.api import chat as chat_mod

    def fake_run(*, question, history="", user_id=None):
        return {
            "response": f"Stub answer to: {question}",
            "citations": [{"doc_id": "x", "filename": "f.pdf", "page": 1, "score": 0.9, "chunk_id": "c", "preview": "p"}],
            "chunks": [{"doc_id": "x", "chunk_id": "c", "filename": "f.pdf", "page": 1, "score": 0.9, "content": "ctx"}],
            "pdf_name": "f.pdf",
            "pdf_path": "",
            "page_numbers": [1],
            "recommendation_questions": ["q1", "q2", "q3"],
            "ragas_score": {"faithfulness": 0.8, "answer_relevancy": 0.7, "context_precision": 0.6},
            "language": "en",
            "response_time": 0.01,
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "_english_answer": "Stub answer",
            "_english_question": question,
        }

    monkeypatch.setattr(chat_mod._pipeline, "run", fake_run)
    return chat_mod


@pytest.fixture()
def txt_file():
    content = b"Acme Corp Handbook. The vacation policy grants 20 days per year. " * 30
    return ("handbook.txt", io.BytesIO(content), "text/plain")
