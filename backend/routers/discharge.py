"""
NormClaim — Discharge orchestration API (Stage 5).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, status

from Extraction_pipeline.database import get_supabase
from models.schemas import (
    BillBreakdown,
    DischargeOptimizeRequest,
    DischargeOptimizeResponse,
    DischargeProcessRequest,
    DischargeProcessResponse,
    ValidDeductionItem,
)
from routers.admissions import _assert_can_access_admission
from services.auth import require_user
from services.discharge_optimizer import DischargeOptimizer
from services.discharge_service import DischargeService
from services.extractor import GeminiQuotaExceededError, resolved_gemini_model

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/discharge", tags=["Discharge"])


@router.post(
    "/process/{admission_id}",
    response_model=DischargeProcessResponse,
    summary="Run discharge summary context, bill breakdown (Gemini), and FHIR bundle",
)
async def process_discharge(
    admission_id: str,
    body: DischargeProcessRequest = Body(default_factory=DischargeProcessRequest),
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

    service = DischargeService(supabase)
    try:
        result = await service.process_discharge(
            admission_id,
            document_id=body.document_id,
            bill_notes=body.bill_notes,
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
    except Exception as exc:
        logger.exception("discharge process failed")
        raise HTTPException(
            status_code=503,
            detail=f"Discharge processing failed: {exc}",
        ) from exc

    return DischargeProcessResponse(
        admission_id=result["admission_id"],
        discharge_summary=result["discharge_summary"],
        fhir_bundle=result["fhir_bundle"],
        bill_breakdown=BillBreakdown(**result["bill_breakdown"]),
        icp_generated=result["icp_generated"],
        fhir_source=result["fhir_source"],
    )


def _fetch_active_policy(supabase, patient_id: str) -> dict:
    resp = (
        supabase.table("insurance_policies")
        .select("*")
        .eq("patient_id", str(patient_id))
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else {}


@router.post(
    "/optimize/{admission_id}",
    response_model=DischargeOptimizeResponse,
    summary="Discharge approval optimization (copay, deductions, approval probability)",
)
async def optimize_discharge(
    admission_id: str,
    body: DischargeOptimizeRequest = Body(default_factory=DischargeOptimizeRequest),
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

    patient_id = str(admission.get("patient_id") or "")
    if not patient_id:
        raise HTTPException(status_code=400, detail="Admission has no patient_id")

    policy = _fetch_active_policy(supabase, patient_id)
    bill = body.bill_breakdown or BillBreakdown(
        confidence=0.5,
        total=0,
    )

    optimizer = DischargeOptimizer(supabase)
    raw = optimizer.optimize(
        admission_id,
        bill,
        policy,
        body.diagnoses,
        los_days=body.los_days,
        admitted_at=admission.get("admitted_at"),
        patient_id=patient_id,
        requesting_user_id=current_user.get("id"),
    )

    return DischargeOptimizeResponse(
        admission_id=raw["admission_id"],
        predicted_copay=raw["predicted_copay"],
        valid_deductions=[ValidDeductionItem(**d) for d in raw["valid_deductions"]],
        approval_probability=raw["approval_probability"],
        optimized_claim_amount=raw["optimized_claim_amount"],
        flags=raw["flags"],
        estimated_tpa_time_minutes=raw["estimated_tpa_time_minutes"],
        policy_snapshot=raw["policy_snapshot"],
    )
