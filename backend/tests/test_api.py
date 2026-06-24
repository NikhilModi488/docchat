"""Integration tests over the FastAPI app (LLM stubbed via stub_pipeline)."""
from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["vector_store"] == "faiss"


def test_auth_register_login_me(client):
    r = client.post("/api/auth/register", json={"username": "carol", "password": "pw1234"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["username"] == "carol"
    # duplicate registration rejected
    assert client.post("/api/auth/register", json={"username": "carol", "password": "pw1234"}).status_code == 409
    # wrong password rejected
    assert client.post("/api/auth/login", json={"username": "carol", "password": "nope"}).status_code == 401


def test_upload_list_delete_document(client, txt_file):
    h = _user(client, "doer")
    r = client.post("/api/upload", files={"file": txt_file}, headers=h)
    assert r.status_code == 200, r.text
    doc_id = r.json()["doc_id"]
    assert r.json()["chunks"] >= 1

    docs = client.get("/api/documents", headers=h).json()["documents"]
    assert any(d["id"] == doc_id for d in docs)

    assert client.delete(f"/api/document/{doc_id}", headers=h).status_code == 200
    docs2 = client.get("/api/documents", headers=h).json()["documents"]
    assert not any(d["id"] == doc_id for d in docs2)


def test_same_name_upload_replaces_previous(client):
    import io

    h = _user(client, "replacer")
    v1 = ("notes.txt", io.BytesIO(b"First version about apples. " * 30), "text/plain")
    r1 = client.post("/api/upload", files={"file": v1}, headers=h)
    assert r1.status_code == 200, r1.text
    old_id = r1.json()["doc_id"]

    # Re-upload SAME filename, different content -> should replace, new id.
    v2 = ("notes.txt", io.BytesIO(b"Second version about bananas and oranges. " * 30), "text/plain")
    r2 = client.post("/api/upload", files={"file": v2}, headers=h)
    assert r2.status_code == 200, r2.text
    new_id = r2.json()["doc_id"]
    assert r2.json()["replaced"] is True
    assert new_id != old_id

    # Only ONE document with that name remains, and it's the new one.
    docs = client.get("/api/documents", headers=h).json()["documents"]
    notes = [d for d in docs if d["filename"] == "notes.txt"]
    assert len(notes) == 1
    assert notes[0]["id"] == new_id
    # The old document is gone.
    assert client.get(f"/api/document/{old_id}", headers=h).status_code == 404


def test_user_isolation(client, txt_file):
    ha = _user(client, "alpha")
    hb = _user(client, "beta")
    doc_id = client.post("/api/upload", files={"file": txt_file}, headers=ha).json()["doc_id"]
    # beta cannot see or fetch alpha's doc
    assert client.get(f"/api/document/{doc_id}", headers=hb).status_code == 404
    assert all(d["id"] != doc_id for d in client.get("/api/documents", headers=hb).json()["documents"])


def test_query_and_conversation_flow(client, stub_pipeline):
    h = _user(client, "chatter")
    r = client.post("/api/query", json={"query": "hello?"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["response"].startswith("Stub answer")
    assert len(body["recommendation_questions"]) == 3
    assert body["conversation_id"]
    conv_id = body["conversation_id"]
    msg_id = body["message_id"]

    # conversation persisted with user + assistant messages
    conv = client.get(f"/api/conversation/{conv_id}", headers=h).json()
    assert len(conv["messages"]) == 2

    # feedback on the assistant message
    fb = client.post("/api/feedback", json={"message_id": msg_id, "rating": "up"}, headers=h)
    assert fb.status_code == 200

    # rename + list + delete
    assert client.patch(f"/api/conversation/{conv_id}", json={"title": "Renamed"}, headers=h).status_code == 200
    assert any(c["id"] == conv_id for c in client.get("/api/conversations", headers=h).json()["conversations"])
    assert client.delete(f"/api/conversation/{conv_id}", headers=h).status_code == 200


def test_analytics_shape(client):
    h = _user(client, "analyst")
    a = client.get("/api/analytics", headers=h).json()
    for key in ("total_documents", "total_chunks", "total_conversations", "average_ragas", "token_usage", "top_questions", "feedback"):
        assert key in a


def _user(client, name: str) -> dict:
    r = client.post("/api/auth/register", json={"username": name, "password": "pw1234"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
