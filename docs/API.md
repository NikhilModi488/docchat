# DocChat API Reference

Base URL: `http://localhost:8000/api` · Interactive docs: `http://localhost:8000/docs`

Auth is optional. When `RAG_REQUIRE_AUTH=false` (default) requests act as the
shared `default` user. Otherwise send `Authorization: Bearer <jwt>`.

## Auth
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/register` | `{username, password}` | `{access_token, token_type, username}` |
| POST | `/auth/login` | `{username, password}` | `{access_token, token_type, username}` |
| GET | `/auth/me` | — | `{username}` |

## Documents
| Method | Path | Notes |
|---|---|---|
| POST | `/upload` | multipart `file`. Validates type (pdf/docx/txt/md/pptx) & size (≤25 MB). Returns `{doc_id, filename, pages, chunks}`. |
| GET | `/documents` | List the user's documents with status & chunk counts. |
| GET | `/document/{id}` | Document metadata. |
| DELETE | `/document/{id}` | Removes FAISS vectors + chunk rows + file. |
| POST | `/reindex?doc_id=...` | Re-runs ingestion from the saved file. |
| GET | `/document/{id}/file` | Original file (inline). |
| GET | `/document/{id}/page/{page}.png?zoom=2` | Rasterised PDF page (PyMuPDF) for the in-app viewer. |

## Chat
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/query` | `{query, conversation_id?}` | Full response object (below). |
| POST | `/stream-query` | `{query, conversation_id?}` | SSE stream. |

### `/query` response object
```json
{
  "response": "", "citations": [], "chunks": [],
  "pdf_name": "", "pdf_path": "", "page_numbers": [],
  "recommendation_questions": [],
  "ragas_score": {"faithfulness": 0, "answer_relevancy": 0, "context_precision": 0},
  "conversation_id": "", "language": "", "response_time": 0,
  "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
  "message_id": 0
}
```

### `/stream-query` SSE events (`data: {json}\n\n`)
- `{"type":"conversation","conversation_id":"..."}` — emitted first.
- `{"type":"sources","citations":[...],"chunks":[...],"language":"en"}`
- `{"type":"token","text":"..."}` — repeated as tokens generate.
- `{"type":"final", ...full response object..., "message_id":N}`
- `{"type":"done"}` or `{"type":"error","message":"..."}`

## Conversations
| Method | Path | Notes |
|---|---|---|
| POST | `/conversation` | Create an empty conversation. |
| GET | `/conversations` | List (most-recent first). |
| GET | `/conversation/{id}` | Conversation + full message history. |
| PATCH | `/conversation/{id}` | `{title}` — rename. |
| DELETE | `/conversation/{id}` | Delete (cascades messages). |

## Feedback & Analytics
| Method | Path | Notes |
|---|---|---|
| POST | `/feedback` | `{message_id, rating: "up"\|"down", comment?}` |
| GET | `/analytics` | Totals, avg response time, avg RAGAS, token usage, top questions, feedback stats. |

## Health
`GET /api/health` → backend status, Ollama availability, models, indexed chunk count.
