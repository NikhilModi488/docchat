"""
app/services/ingestion_service.py
=================================
Orchestrates the full ingestion pipeline for a single uploaded file:

    save bytes -> load (multi-format) -> clean -> chunk -> embed+index (FAISS)
    -> persist metadata + chunk rows (SQLite).

Each chunk's metadata is tagged with `doc_id` and `user_id` so the vector store
can later (a) filter by user for document isolation and (b) delete exactly this
document's vectors. Deleting a document removes its FAISS vectors, its chunk
rows, the metadata row, and the saved file.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import crud
from app.ingestion.chunker import DocumentChunker
from app.ingestion.cleaner import TextCleaner
from app.ingestion.loader import DocumentLoader
from app.services.resources import get_store
from app.utils.helpers import safe_filename, sha256_bytes
from app.utils.logger import get_logger

logger = get_logger(__name__)

_loader = DocumentLoader()
_cleaner = TextCleaner()
_chunker = DocumentChunker()


def ingest_file(db: Session, *, user_id: str, filename: str, data: bytes) -> dict:
    """
    Ingest one uploaded file. Returns a summary dict with the new document id,
    page count and chunk count. Raises ValueError on unextractable content.
    """
    content_hash = sha256_bytes(data)
    safe = safe_filename(filename)

    # Same-name replacement: if this user already has a document with the same
    # filename, remove the old one entirely (FAISS vectors + chunk rows + file +
    # metadata row) before ingesting the new upload. This keeps one live version
    # per filename and prevents stale duplicates in the index.
    replaced = 0
    for old in crud.find_documents_by_filename(db, user_id, safe):
        logger.info("Replacing existing '%s' (%s) for user %s", safe, old.id, user_id)
        delete_document(db, old.id, user_id)
        replaced += 1

    # Save to disk under uploads/<user_id>/<filename> (after deleting the old file).
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / safe
    dest.write_bytes(data)

    doc_row = crud.create_document(
        db, user_id=user_id, filename=safe, path=str(dest), content_hash=content_hash
    )
    result = _index_into(db, doc_id=doc_row.id, user_id=user_id, path=Path(dest), filename=safe)
    result["replaced"] = replaced > 0
    return result


def _index_into(db: Session, *, doc_id: str, user_id: str, path: Path, filename: str) -> dict:
    """Load → clean → chunk → embed+index → persist chunk rows, into an existing
    document row. Shared by upload and reindex so the doc_id is stable."""
    try:
        pages = _loader.load(path)
        cleaned = _cleaner.clean_documents(pages)
        chunks = _chunker.chunk(cleaned)
        if not chunks:
            raise ValueError("No extractable text found in the file.")

        # Tag each chunk so the store can filter/delete by document & user.
        for ch in chunks:
            ch.metadata["doc_id"] = doc_id
            ch.metadata["user_id"] = user_id

        get_store().add_documents(chunks)
        crud.add_chunks(
            db,
            doc_id,
            [
                {
                    "chunk_id": ch.metadata.get("chunk_id", ""),
                    "page": int(ch.metadata.get("page_number", 0)),
                    "text": ch.page_content,
                    "preview": ch.metadata.get("preview", ""),
                }
                for ch in chunks
            ],
        )
        crud.finalize_document(
            db,
            doc_id,
            pages=len({c.metadata.get("page_number", 1) for c in cleaned}) or len(pages),
            chunk_count=len(chunks),
            status="ready",
        )
        logger.info("Indexed %s -> %d chunks", filename, len(chunks))
        return {
            "doc_id": doc_id,
            "filename": filename,
            "pages": len(pages),
            "chunks": len(chunks),
            "duplicate": False,
        }
    except Exception as exc:
        logger.exception("Indexing failed for %s", filename)
        crud.finalize_document(db, doc_id, pages=0, chunk_count=0, status="error", error=str(exc))
        raise


def delete_document(db: Session, doc_id: str, user_id: str) -> bool:
    """Remove a document's vectors, chunk rows, metadata row and file."""
    doc = crud.get_document(db, doc_id, user_id)
    if not doc:
        return False
    get_store().delete_by_doc_id(doc_id)
    # Remove the saved file (best-effort).
    try:
        p = Path(doc.path)
        if p.exists():
            p.unlink()
    except Exception:
        logger.warning("Could not delete file for %s", doc_id)
    crud.delete_document(db, doc_id)  # cascade removes chunk rows
    return True


def reindex_document(db: Session, doc_id: str, user_id: str) -> dict:
    """Re-run ingestion for an existing document from its saved file, PRESERVING
    the doc_id so citations in existing conversations keep resolving."""
    doc = crud.get_document(db, doc_id, user_id)
    if not doc:
        raise ValueError("Document not found.")
    path = Path(doc.path)
    if not path.exists():
        raise ValueError("Original file is no longer on disk; re-upload it.")
    # Drop only this doc's vectors + chunk rows; keep the documents row & id.
    get_store().delete_by_doc_id(doc_id)
    crud.clear_chunks(db, doc_id)
    crud.finalize_document(db, doc_id, pages=0, chunk_count=0, status="processing")
    return _index_into(db, doc_id=doc_id, user_id=user_id, path=path, filename=doc.filename)
