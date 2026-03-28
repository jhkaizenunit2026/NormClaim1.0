"""
NormClaim — Admissions API (Stage 3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from Extraction_pipeline.database import get_supabase
from Extraction_pipeline.router import (
    _assert_can_access_pre_auth_form,
    _find_owner_user_id,
    _is_admin_user,
)
from models.schemas import AdmissionCreatedResponse, AdmissionDetailResponse
from services.admission_service import AdmissionService
from services.auth import require_user

router = APIRouter(prefix="/api/admissions", tags=["Admissions"])


def _assert_can_access_admission(
    supabase,
    admission_row: dict,
    current_user: dict,
) -> None:
    if _is_admin_user(current_user):
        return
    uid = str(current_user.get("id") or "")
    if not uid:
        raise HTTPException(status_code=401, detail="Authenticated user id missing")

    patient_id = admission_row.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=403, detail="Admission has no linked patient")

    patient_resp = (
        supabase.table("patients")
        .select("*")
        .eq("id", str(patient_id))
        .single()
        .execute()
    )
    patient_row = patient_resp.data or {}
    owner = _find_owner_user_id(patient_row)
    if owner is not None and owner == uid:
        return

    pre_auth_id = admission_row.get("pre_auth_form_id")
    if pre_auth_id:
        form_resp = (
            supabase.table("pre_auth_forms")
            .select("*")
            .eq("id", str(pre_auth_id))
            .single()
            .execute()
        )
        form_row = form_resp.data or {}
        form_owner = _find_owner_user_id(form_row)
        if form_owner is not None and form_owner == uid:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this admission",
    )


def _dt_to_iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@router.post(
    "/{pre_auth_form_id}",
    response_model=AdmissionCreatedResponse,
    summary="Create admission from an approved pre-auth form",
)
async def create_admission(
    pre_auth_form_id: str,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    _assert_can_access_pre_auth_form(supabase, pre_auth_form_id, current_user)
    service = AdmissionService(supabase)
    try:
        result = service.admit_patient(
            pre_auth_form_id,
            current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    msg = (
        "Admission already exists for this pre-auth form."
        if result.get("already_existed")
        else "Admission created."
    )
    return AdmissionCreatedResponse(
        admission_id=result["admission_id"],
        admission_number=result["admission_number"],
        pre_auth_form_id=result["pre_auth_form_id"],
        patient_id=result["patient_id"],
        message=msg,
        already_existed=bool(result.get("already_existed")),
    )


@router.get(
    "/{admission_id}",
    response_model=AdmissionDetailResponse,
    summary="Get admission by id",
)
async def get_admission(
    admission_id: str,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    service = AdmissionService(supabase)
    row = service.get_admission(admission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Admission not found")
    _assert_can_access_admission(supabase, row, current_user)
    return AdmissionDetailResponse(
        id=str(row["id"]),
        admission_number=str(row["admission_number"]),
        patient_id=str(row["patient_id"]),
        pre_auth_form_id=str(row["pre_auth_form_id"])
        if row.get("pre_auth_form_id")
        else None,
        admitted_at=_dt_to_iso(row.get("admitted_at")),
        discharge_at=_dt_to_iso(row.get("discharge_at")),
        status=str(row.get("status") or "admitted"),
        created_by=str(row["created_by"]) if row.get("created_by") else None,
    )
