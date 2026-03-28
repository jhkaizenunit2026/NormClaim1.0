"""
NormClaim — Settlement letter parsing API (Stage 8).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from Extraction_pipeline.database import get_supabase
from models.schemas import (
    SettlementParseResponse,
    SettlementRecordResponse,
    SettlementDeductionItem,
)
from routers.admissions import _assert_can_access_admission
from services.auth import require_user
from services.extractor import GeminiQuotaExceededError, resolved_gemini_model
from services.settlement_parser import SettlementParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settlements", tags=["Settlements"])


def _detect_format(filename: str, content_type: str | None) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".pdf"):
        return "pdf"
    if fn.endswith(".png"):
        return "png"
    if fn.endswith(".jpg") or fn.endswith(".jpeg"):
        return "jpg"
    if fn.endswith(".docx"):
        return "docx"
    if fn.endswith(".txt"):
        return "txt"
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return "pdf"
    if "png" in ct:
        return "png"
    if "jpeg" in ct or "jpg" in ct:
        return "jpg"
    return "pdf"


def _iso(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _row_to_response(row: dict) -> SettlementRecordResponse:
    raw_ded = row.get("deductions") or []
    deductions: list[SettlementDeductionItem] = []
    if isinstance(raw_ded, list):
        for item in raw_ded:
            if isinstance(item, dict) and item.get("description") is not None:
                try:
                    deductions.append(
                        SettlementDeductionItem(
                            description=str(item.get("description", "")),
                            amount=float(item.get("amount") or 0),
                            reason=item.get("reason"),
                        )
                    )
                except (TypeError, ValueError):
                    continue
    return SettlementRecordResponse(
        id=str(row["id"]),
        admission_id=str(row["admission_id"]) if row.get("admission_id") else None,
        utr_number=row.get("utr_number"),
        settlement_amount=row.get("settlement_amount"),
        tds_amount=row.get("tds_amount"),
        deductions=deductions,
        final_payable=row.get("final_payable"),
        settlement_date=row.get("settlement_date"),
        remarks=row.get("remarks"),
        confidence=row.get("confidence"),
        parsed_at=_iso(row.get("parsed_at")),
    )


@router.post(
    "/parse",
    response_model=SettlementParseResponse,
    summary="Upload a settlement letter; OCR + Gemini extraction; optional DB persist",
)
async def parse_settlement_letter(
    file: UploadFile = File(...),
    admission_id: Optional[str] = Form(default=None),
    persist: bool = Form(default=True),
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    patient_id: str | None = None

    if admission_id:
        adm_resp = (
            supabase.table("admissions")
            .select("*")
            .eq("id", admission_id)
            .single()
            .execute()
        )
        admission = adm_resp.data
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        _assert_can_access_admission(supabase, admission, current_user)
        patient_id = str(admission.get("patient_id") or "") or None

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    fmt = _detect_format(file.filename or "", file.content_type)
    parser = SettlementParser(supabase)
    try:
        extraction = parser.parse(data, fmt)
    except GeminiQuotaExceededError as e:
        detail: dict = {
            "code": "GEMINI_QUOTA_EXHAUSTED",
            "message": str(e),
            "model": resolved_gemini_model(),
        }
        if e.provider_details:
            detail["provider_details"] = e.provider_details
        raise HTTPException(status_code=503, detail=detail) from e
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("settlement parse failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    settlement_id: str | None = None
    saved = False
    if persist and admission_id:
        settlement_id = parser.persist(
            admission_id,
            extraction,
            requesting_user_id=current_user.get("id"),
            patient_id=patient_id,
        )
        saved = True
    elif persist and not admission_id:
        raise HTTPException(
            status_code=400,
            detail="admission_id is required when persist=true",
        )

    return SettlementParseResponse(
        settlement_id=settlement_id,
        admission_id=admission_id,
        persisted=saved,
        extraction=extraction,
    )


@router.get(
    "/{admission_id}",
    response_model=SettlementRecordResponse,
    summary="Latest parsed settlement for an admission",
)
async def get_settlement_for_admission(
    admission_id: str,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    adm_resp = (
        supabase.table("admissions")
        .select("*")
        .eq("id", admission_id)
        .single()
        .execute()
    )
    admission = adm_resp.data
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    _assert_can_access_admission(supabase, admission, current_user)

    resp = (
        supabase.table("settlement_records")
        .select("*")
        .eq("admission_id", admission_id)
        .order("parsed_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No settlement record for this admission",
        )
    return _row_to_response(rows[0])
