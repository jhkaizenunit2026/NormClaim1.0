"""
NormClaim — Documents Router (v2)
Handles PDF upload with ABDM consent, document listing, metadata, and deletion.
All storage backed by SQLAlchemy (Supabase PostgreSQL or SQLite).
"""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from models.database import (
    SessionLocal,
    save_document_with_consent,
    get_document_meta,
    list_documents as db_list_documents,
    delete_document as db_delete_document,
)
from models.schemas import DocumentUploadResponse, DocumentMeta, DocumentListResponse
from services.auth import require_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# In-memory store (populated by persistence.bootstrap_memory_caches on startup)
DOCUMENTS: dict = {}

# Maximum upload size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20_971_520 bytes


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    consent_obtained: bool = Form(False),
    _: dict = Depends(require_user),
):
    """
    Upload a PDF document with ABDM consent.
    Validates PDF type, magic bytes, size, and consent flag.
    """
    # ── 1. Consent check (ABDM / DPDP Act mandate) ─────────────────────
    if not consent_obtained:
        raise HTTPException(
            status_code=400,
            detail="Patient consent is required under ABDM/DPDP Act before processing clinical documents.",
        )

    # ── 2. Content-type check ───────────────────────────────────────────
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are accepted.",
        )

    # ── 3. Read file bytes ──────────────────────────────────────────────
    file_bytes = await file.read()

    # ── 4. Size check ──────────────────────────────────────────────────
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 20MB.",
        )

    # ── 5. Magic bytes check (must start with %PDF) ────────────────────
    if not file_bytes[:4] == b"%PDF":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are accepted.",
        )

    # ── 6. Generate ID and persist ─────────────────────────────────────
    doc_id = str(uuid.uuid4())
    filename = file.filename or "upload.pdf"
    uploaded_at = datetime.now(timezone.utc)
    storage_key = f"{doc_id}/{filename}"

    # Supabase Storage is mandatory for demo/persistence source-of-truth.
    try:
        from main import supabase_admin as sb_client
    except Exception:
        sb_client = None
    if sb_client is None:
        raise HTTPException(status_code=503, detail="Supabase storage client is not configured")

    try:
        sb_client.storage.from_("documents").upload(storage_key, file_bytes)
    except Exception as e:
        logger.error("Supabase Storage upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Document storage upload failed")

    # Keep bytes in memory for downstream routes (/extract etc.)
    DOCUMENTS[doc_id] = {
        "filename": filename,
        "size": len(file_bytes),
        "bytes": file_bytes,
    }

    # Persist to database
    try:
        with SessionLocal() as db:
            save_document_with_consent(
                db=db,
                document_id=doc_id,
                filename=filename,
                file_bytes=file_bytes,
                consent_obtained=consent_obtained,
                storage_key=storage_key,
            )
    except Exception as e:
        logger.error("Database error during upload: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=filename,
        status="uploaded",
        consent_obtained=consent_obtained,
        uploaded_at=uploaded_at.isoformat() + "Z",
        message="Document uploaded successfully. Ready for extraction.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_all_documents(_: dict = Depends(require_user)):
    """List all uploaded documents with their pipeline status."""
    try:
        with SessionLocal() as db:
            docs = db_list_documents(db)
    except Exception as e:
        logger.error("Database error listing documents: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    documents = [
        DocumentMeta(
            document_id=d["document_id"],
            filename=d["filename"],
            status=d["status"],
            uploaded_at=d["uploaded_at"],
        )
        for d in docs
    ]

    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{document_id}")
async def get_document(document_id: str, _: dict = Depends(require_user)):
    """Return metadata for a single document."""
    try:
        with SessionLocal() as db:
            meta = get_document_meta(db, document_id)
    except Exception as e:
        logger.error("Database error fetching document %s: %s", document_id, e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )

    return meta


@router.delete("/{document_id}")
async def delete_document_endpoint(document_id: str, _: dict = Depends(require_user)):
    """Delete document and all associated data (extractions, FHIR bundles, reconciliations)."""
    try:
        with SessionLocal() as db:
            deleted = db_delete_document(db, document_id)
    except Exception as e:
        logger.error("Database error deleting document %s: %s", document_id, e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )

    # Clean up in-memory caches
    DOCUMENTS.pop(document_id, None)

    # Clean extraction, reconciliation, fhir in-memory caches
    try:
        from routers.extract import EXTRACTIONS
        EXTRACTIONS.pop(document_id, None)
    except Exception:
        pass
    try:
        from routers.reconcile import REPORTS
        REPORTS.pop(document_id, None)
    except Exception:
        pass
    try:
        from routers.fhir import FHIR_BUNDLES
        FHIR_BUNDLES.pop(document_id, None)
    except Exception:
        pass

    return {"message": "Document and all associated data deleted."}
