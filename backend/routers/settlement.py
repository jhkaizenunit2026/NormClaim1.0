"""
NormClaim — Settlement Router
POST /api/settlement/{admission_id}/parse
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from Extraction_pipeline.database import get_supabase
from models.schemas import SettlementLetterExtraction
from services.auth import require_user
from services.settlement_parser import SettlementParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settlement", tags=["Settlement"])


@router.post("/{admission_id}/parse")
async def parse_settlement(
    admission_id: str,
    file: UploadFile = File(...),
    file_format: str = Form("pdf"),
    current_user: dict = Depends(require_user),
):
    """
    Parse a TPA settlement letter: OCR + Gemini extraction, then persist to DB.
    Returns { settlement_id: str, extraction: SettlementLetterExtraction }.
    """
    try:
        file_bytes = await file.read()
        svc = SettlementParser(get_supabase())
        extraction: SettlementLetterExtraction = svc.parse(file_bytes, file_format)
        settlement_id = svc.persist(
            admission_id=admission_id,
            extraction=extraction,
            requesting_user_id=current_user.get("id"),
        )
        return {
            "settlement_id": settlement_id,
            "extraction": extraction.model_dump(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("parse_settlement failed for admission %s", admission_id)
        raise HTTPException(status_code=500, detail=f"Settlement parsing failed for admission {admission_id} due to an internal error.")
