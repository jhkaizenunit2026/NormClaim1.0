"""
NormClaim — Finance reconciliation API (Stage 9).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from Extraction_pipeline.database import get_supabase
from models.schemas import FinanceReconcileRequest, FinanceReconcileResponse
from routers.admissions import _assert_can_access_admission
from services.auth import require_user
from services.extractor import GeminiQuotaExceededError, resolved_gemini_model
from services.finance_reconciler import FinanceReconciler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/finance", tags=["Finance"])


@router.post(
    "/reconcile/{admission_id}",
    response_model=FinanceReconcileResponse,
    summary="Reconcile expected claim amount vs latest TPA settlement",
)
async def reconcile_finance(
    admission_id: str,
    body: FinanceReconcileRequest,
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

    patient_id = str(admission.get("patient_id") or "") or None
    reconciler = FinanceReconciler(supabase)
    try:
        raw = reconciler.run_for_admission(
            admission_id,
            body.expected_amount,
            body.bill_breakdown,
            body.diagnoses,
            body.settlement_override,
            patient_id=patient_id,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("finance reconcile failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FinanceReconcileResponse(
        reconciliation_id=raw["reconciliation_id"],
        admission_id=raw["admission_id"],
        expected_amount=raw["expected_amount"],
        received_amount=raw["received_amount"],
        delta=raw["delta"],
        raise_flag=raw["raise_flag"],
        mismatch_category=raw["mismatch_category"],
        deductions_analysis=list(raw.get("deductions_analysis") or []),
        recommendations=list(raw.get("recommendations") or []),
        fraud_risk_score=raw["fraud_risk_score"],
        confidence=raw["confidence"],
        status=str(raw.get("status") or "pending"),
    )
