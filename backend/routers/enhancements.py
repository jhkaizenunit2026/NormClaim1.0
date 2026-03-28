"""
NormClaim — Enhancement requests API (Stage 4).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from Extraction_pipeline.database import get_supabase
from models.schemas import (
    EnhancementCreateResponse,
    EnhancementDetailResponse,
    EnhancementGeneratedPayload,
    EnhancementGenerateRequest,
    EnhancementTPAUpdateRequest,
)
from routers.admissions import _assert_can_access_admission, _dt_to_iso
from services.auth import require_user
from services.enhancement_service import EnhancementService
from services.extractor import GeminiQuotaExceededError, resolved_gemini_model

router = APIRouter(prefix="/api/enhancements", tags=["Enhancements"])


def _row_to_detail(row: dict) -> EnhancementDetailResponse:
    cb = row.get("cost_breakdown")
    tr = row.get("tpa_response")
    return EnhancementDetailResponse(
        id=str(row["id"]),
        admission_id=str(row["admission_id"]),
        original_amount=row.get("original_amount"),
        suggested_amount=row.get("suggested_amount"),
        justification_text=row.get("justification_text"),
        severity_score=row.get("severity_score"),
        cost_breakdown=dict(cb) if isinstance(cb, dict) else {},
        status=str(row.get("status") or "draft"),
        tpa_response=dict(tr) if isinstance(tr, dict) else {},
        created_at=_dt_to_iso(row.get("created_at")),
    )


@router.post(
    "/{admission_id}",
    response_model=EnhancementCreateResponse,
    summary="Generate enhancement justification for an admission",
)
async def generate_enhancement(
    admission_id: str,
    body: EnhancementGenerateRequest,
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

    service = EnhancementService(supabase)
    try:
        result = service.generate_enhancement(
            admission_id=admission_id,
            diagnosis_data=body.diagnosis_data,
            procedures=body.procedures,
            requested_amount=body.requested_amount,
            requesting_user_id=current_user.get("id"),
        )
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return EnhancementCreateResponse(
        enhancement_id=result["enhancement_id"],
        admission_id=result["admission_id"],
        status=result["status"],
        original_amount=result["original_amount"],
        payload=EnhancementGeneratedPayload(**result["payload"]),
    )


@router.get(
    "/{enhancement_id}",
    response_model=EnhancementDetailResponse,
    summary="Get enhancement request by id",
)
async def get_enhancement(
    enhancement_id: str,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    service = EnhancementService(supabase)
    row = service.get_enhancement(enhancement_id)
    if not row:
        raise HTTPException(status_code=404, detail="Enhancement not found")

    adm_resp = (
        supabase.table("admissions")
        .select("*")
        .eq("id", str(row["admission_id"]))
        .single()
        .execute()
    )
    admission = adm_resp.data
    if not admission:
        raise HTTPException(status_code=404, detail="Linked admission not found")
    _assert_can_access_admission(supabase, admission, current_user)
    return _row_to_detail(row)


@router.put(
    "/{enhancement_id}",
    response_model=EnhancementDetailResponse,
    summary="Attach TPA / insurer response to an enhancement",
)
async def update_enhancement_tpa(
    enhancement_id: str,
    body: EnhancementTPAUpdateRequest,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    service = EnhancementService(supabase)
    row = service.get_enhancement(enhancement_id)
    if not row:
        raise HTTPException(status_code=404, detail="Enhancement not found")

    adm_resp = (
        supabase.table("admissions")
        .select("*")
        .eq("id", str(row["admission_id"]))
        .single()
        .execute()
    )
    admission = adm_resp.data
    if not admission:
        raise HTTPException(status_code=404, detail="Linked admission not found")
    _assert_can_access_admission(supabase, admission, current_user)

    try:
        updated = service.update_with_tpa_response(
            enhancement_id=enhancement_id,
            tpa_response=body.tpa_response,
            status=body.status,
            requesting_user_id=current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _row_to_detail(updated)
