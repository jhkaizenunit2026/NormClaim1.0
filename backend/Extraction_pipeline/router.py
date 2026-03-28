"""
router.py — FastAPI endpoints for the pre-auth auto-fill module
===============================================================
Mount this router into your main NormClaim FastAPI app:

    from Extraction_pipeline.router import router as preauth_router
    app.include_router(preauth_router, prefix="/api/preauth", tags=["pre-auth"])

Endpoints:
    POST /api/preauth/auto-fill/{pre_auth_form_id}   — run full pipeline
    GET  /api/preauth/status/{pre_auth_form_id}       — get current form status
    POST /api/preauth/correct/{pre_auth_form_id}      — apply human correction
    GET  /api/preauth/confidence/{pre_auth_form_id}   — get confidence report

Python 3.11 required.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .database import get_google_api_key, get_supabase
from .pre_auth_filling import CorrectionHandler, PreAuthOrchestrator
from services.auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter()

ADMIN_ROLES = {"admin", "superadmin"}
OWNER_FIELD_CANDIDATES = (
    "user_id",
    "owner_user_id",
    "created_by",
    "created_by_user_id",
    "assigned_user_id",
)


def _is_admin_user(current_user: dict) -> bool:
    return str(current_user.get("role", "")).strip().lower() in ADMIN_ROLES


def _find_owner_user_id(row: dict | None) -> str | None:
    if not row:
        return None
    for field in OWNER_FIELD_CANDIDATES:
        value = row.get(field)
        if value:
            return str(value)
    return None


def _assert_can_access_pre_auth_form(supabase: Any, pre_auth_form_id: str, current_user: dict) -> dict:
    """Authorize access to a pre-auth form by direct owner or linked patient owner."""
    form_resp = (
        supabase.table("pre_auth_forms")
        .select("*")
        .eq("id", pre_auth_form_id)
        .single()
        .execute()
    )
    form_row = form_resp.data
    if not form_row:
        raise HTTPException(status_code=404, detail="pre_auth_form not found")

    if _is_admin_user(current_user):
        return form_row

    current_user_id = str(current_user.get("id") or "")
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authenticated user id missing")

    form_owner = _find_owner_user_id(form_row)
    if form_owner is not None:
        if form_owner == current_user_id:
            return form_row
        raise HTTPException(status_code=403, detail="Not authorized to access this pre-auth form")

    patient_id = form_row.get("patient_id")
    if patient_id:
        patient_resp = (
            supabase.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        patient_row = patient_resp.data or {}
        patient_owner = _find_owner_user_id(patient_row)
        if patient_owner is not None:
            if patient_owner == current_user_id:
                return form_row
            raise HTTPException(status_code=403, detail="Not authorized to access this pre-auth form")

    logger.warning(
        "Denied pre-auth access because no owner mapping is available: form=%s user=%s",
        pre_auth_form_id,
        current_user_id,
    )
    raise HTTPException(
        status_code=403,
        detail="Pre-auth ownership is not configured for this record",
    )


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class AutoFillResponse(BaseModel):
    ai_extraction_id: str
    pre_auth_form_id: str
    form_status: str
    auto_filled_fields: list[str]
    unfilled_mandatory_fields: list[str]
    overall_confidence: float
    low_confidence_flags: list[str]
    message: str


class StatusResponse(BaseModel):
    pre_auth_form_id: str
    form_status: str
    auto_filled: bool
    auto_filled_fields: list[str]
    field_requirements_meta: dict


class CorrectionRequest(BaseModel):
    field_name: str = Field(description="pre_auth_forms column name to correct")
    corrected_value: Any = Field(description="New value from human reviewer")
    original_value: Any = Field(None, description="Original extracted value for audit")


class CorrectionResponse(BaseModel):
    pre_auth_form_id: str
    field_name: str
    new_status: str
    all_mandatory_filled: bool
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/auto-fill/{pre_auth_form_id}",
    response_model=AutoFillResponse,
    summary="Run full extraction + form fill pipeline for a pre-auth form",
)
async def auto_fill_pre_auth(
    pre_auth_form_id: str,
    current_user: dict = Depends(require_user),
):
    """
    Triggers the full pipeline:
      1. Fetches document_attachments for this pre_auth_form
      2. OCR + extracts entities with Gemini
      3. Writes to ai_extraction_records
      4. Maps fields → pre_auth_forms
      5. Updates field_requirements_meta and form_status
      6. Logs to audit_logs

    Requires: consent_obtained = TRUE on the patient record.
    Requires: at least one document_attachment uploaded for this form.
    """
    try:
        supabase = get_supabase()
        google_api_key = get_google_api_key()
        _assert_can_access_pre_auth_form(supabase, pre_auth_form_id, current_user)

        orchestrator = PreAuthOrchestrator(supabase, google_api_key)
        result = orchestrator.process(
            pre_auth_form_id=pre_auth_form_id,
            requesting_user_id=current_user.get("id"),
        )

        return AutoFillResponse(
            **result,
            message=(
                "Form auto-filled successfully. All mandatory fields filled."
                if result["form_status"] == "auto_filled"
                else f"Partial fill. {len(result['unfilled_mandatory_fields'])} mandatory "
                     f"field(s) require manual input: "
                     f"{', '.join(result['unfilled_mandatory_fields'])}"
            ),
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    except Exception as exc:
        logger.exception("auto_fill failed for %s", pre_auth_form_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Extraction pipeline failed due to an internal error.",
        )


@router.get(
    "/status/{pre_auth_form_id}",
    response_model=StatusResponse,
    summary="Get current fill status of a pre-auth form",
)
async def get_fill_status(
    pre_auth_form_id: str,
    current_user: dict = Depends(require_user),
):
    """Returns current form_status, auto_filled_fields, and field_requirements_meta."""
    supabase = get_supabase()
    data = _assert_can_access_pre_auth_form(supabase, pre_auth_form_id, current_user)
    return StatusResponse(
        pre_auth_form_id=pre_auth_form_id,
        form_status=data.get("form_status", "draft"),
        auto_filled=data.get("auto_filled", False),
        auto_filled_fields=data.get("auto_filled_fields") or [],
        field_requirements_meta=data.get("field_requirements_meta") or {},
    )


@router.post(
    "/correct/{pre_auth_form_id}",
    response_model=CorrectionResponse,
    summary="Apply a human reviewer correction to an auto-filled field",
)
async def apply_correction(
    pre_auth_form_id: str,
    body: CorrectionRequest,
    current_user: dict = Depends(require_user),
):
    """
    Called by the Streamlit reviewer UI when a human corrects a field.
    Writes to pre_auth_forms, updates field_requirements_meta,
    logs to audit_logs, and writes to preauth_corrections (fine-tuning feedback).
    """
    try:
        supabase = get_supabase()
        _assert_can_access_pre_auth_form(supabase, pre_auth_form_id, current_user)
        handler = CorrectionHandler(supabase)
        result = handler.apply_correction(
            pre_auth_form_id=pre_auth_form_id,
            field_name=body.field_name,
            corrected_value=body.corrected_value,
            reviewer_user_id=current_user.get("id"),
            original_extracted_value=body.original_value,
        )

        return CorrectionResponse(
            **result,
            message=(
                "Correction applied. All mandatory fields now filled — form ready to submit."
                if result["all_mandatory_filled"]
                else "Correction applied. Some mandatory fields still require input."
            ),
        )

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("correction failed for %s", pre_auth_form_id)
        raise HTTPException(
            status_code=500,
            detail="Correction could not be applied due to an internal error.",
        )


@router.get(
    "/confidence/{pre_auth_form_id}",
    summary="Get confidence report for a pre-auth form",
)
async def get_confidence_report(
    pre_auth_form_id: str,
    current_user: dict = Depends(require_user),
):
    """
    Returns the confidence report from the last auto-fill run.
    Used by the reviewer UI to highlight which fields need human attention.
    """
    supabase = get_supabase()
    _assert_can_access_pre_auth_form(supabase, pre_auth_form_id, current_user)
    resp = (
        supabase.table("document_attachments")
        .select("storage_url, filename, uploaded_at")
        .eq("entity_type", "pre_auth")
        .eq("entity_id", pre_auth_form_id)
        .eq("doc_type", "other")
        .execute()
    )
    rows = resp.data or []
    report_rows = [
        r for r in rows
        if str(r.get("filename") or "").startswith("confidence_report")
    ]
    if not report_rows:
        raise HTTPException(
            status_code=404,
            detail="No confidence report found. Run auto-fill first."
        )

    latest = sorted(
        report_rows,
        key=lambda r: str(r.get("uploaded_at") or ""),
        reverse=True,
    )[0]
    confidence_report_url = latest.get("storage_url")

    parsed = urlparse(str(confidence_report_url or ""))
    if parsed.scheme not in {"http", "https"}:
        confidence_report_url = None

    return {
        "pre_auth_form_id": pre_auth_form_id,
        "confidence_report_url": confidence_report_url,
        "message": (
            "Fetch this URL from Supabase Storage to view the full report."
            if confidence_report_url
            else "Report exists but public URL is unavailable; check storage permissions."
        ),
    }
