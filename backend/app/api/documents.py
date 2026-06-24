"""app/api/documents.py — upload, list, get, delete, reindex, PDF page render."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.database import crud
from app.services import ingestion_service
from app.utils.logger import get_logger
from app.utils.security import validate_upload

logger = get_logger(__name__)
router = APIRouter(tags=["documents"])


def _doc_to_dict(doc) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "pages": doc.pages,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "error": doc.error,
        "upload_time": doc.upload_time.isoformat() if doc.upload_time else None,
    }


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: str = Depends(current_user),
) -> dict:
    data = await file.read()
    ok, reason = validate_upload(file.filename or "", len(data))
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    try:
        return ingestion_service.ingest_file(db, user_id=user, filename=file.filename, data=data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    docs = crud.list_documents(db, user)
    return {"documents": [_doc_to_dict(d) for d in docs]}


@router.get("/document/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    doc = crud.get_document(db, doc_id, user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _doc_to_dict(doc)


@router.delete("/document/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    if not ingestion_service.delete_document(db, doc_id, user):
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"deleted": doc_id}


@router.post("/reindex")
def reindex(doc_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> dict:
    try:
        return ingestion_service.reindex_document(db, doc_id, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/document/{doc_id}/file")
def download_file(doc_id: str, db: Session = Depends(get_db), user: str = Depends(current_user)) -> Response:
    doc = crud.get_document(db, doc_id, user)
    if not doc or not Path(doc.path).exists():
        raise HTTPException(status_code=404, detail="File not found.")
    data = Path(doc.path).read_bytes()
    media = "application/pdf" if doc.filename.lower().endswith(".pdf") else "application/octet-stream"
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'inline; filename="{doc.filename}"'
    })


@router.get("/document/{doc_id}/page/{page}.png")
def render_page(
    doc_id: str, page: int, zoom: float = 2.0, db: Session = Depends(get_db), user: str = Depends(current_user)
) -> Response:
    """Rasterise a single PDF page to PNG (for the in-app viewer). Reuses the
    proven PyMuPDF approach that sidesteps sandboxed-iframe PDF rendering."""
    doc = crud.get_document(db, doc_id, user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = Path(doc.path)
    if not path.exists() or not doc.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=404, detail="PDF not available for preview.")
    try:
        import fitz  # PyMuPDF
    except Exception:
        try:
            import pymupdf as fitz  # type: ignore
        except Exception:
            raise HTTPException(status_code=501, detail="PyMuPDF not installed.")

    zoom = max(0.5, min(zoom, 4.0))
    pdf = fitz.open(str(path))
    try:
        idx = max(1, min(page, pdf.page_count)) - 1
        pg = pdf.load_page(idx)
        pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        png = pix.tobytes("png")
    finally:
        pdf.close()
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "max-age=3600"})
