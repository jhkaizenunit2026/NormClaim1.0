"""
NormClaim — Extract Router
Handles AI extraction of clinical entities from uploaded documents.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import ExtractionResult
from services.extractor import extract_from_document
from routers.documents import DOCUMENTS

router = APIRouter(prefix="/api/extract", tags=["Extraction"])

# In-memory extraction results store
EXTRACTIONS: dict = {}


def _ensure_extraction_loaded(document_id: str) -> None:
    from services.persistence import load_extraction_result

    if document_id in EXTRACTIONS:
        return
    ex = load_extraction_result(document_id)
    if ex:
        EXTRACTIONS[document_id] = ex


@router.post("/{document_id}", response_model=ExtractionResult)
async def extract_document(document_id: str):
    """Run NLP extraction on an uploaded document."""
    from services.persistence import hydrate_document_for_extract, save_extraction_result
    from models.database import SessionLocal

    hydration_state = hydrate_document_for_extract(document_id)
    if hydration_state == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
    if hydration_state == "bytes_missing":
        raise HTTPException(status_code=400, detail="Document bytes missing")

    file_bytes = DOCUMENTS[document_id].get("bytes")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Document bytes missing")

    try:
        extraction_result = extract_from_document(file_bytes, document_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")

    EXTRACTIONS[document_id] = extraction_result
    try:
        with SessionLocal() as db:
            save_extraction_result(db, extraction_result)
    except Exception:
        pass
    return extraction_result


@router.get("/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    """Retrieve a previous extraction result."""
    _ensure_extraction_loaded(document_id)
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Not extracted yet")
    return EXTRACTIONS[document_id]
