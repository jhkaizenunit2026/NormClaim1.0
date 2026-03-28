"""
NormClaim — Claim dispatch API (Stage 7): PDF + optional email.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from Extraction_pipeline.database import get_supabase
from models.schemas import DispatchRequest, DispatchResponse
from routers.admissions import _assert_can_access_admission
from services.auth import require_user
from services.dispatch_service import DispatchService

router = APIRouter(prefix="/api/dispatch", tags=["Dispatch"])


def _iso(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


@router.post(
    "/{admission_id}",
    response_model=DispatchResponse,
    summary="Generate claim PDF, store in bucket, optionally email TPA/insurer",
)
async def dispatch_claim(
    admission_id: str,
    body: DispatchRequest,
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

    svc = DispatchService(supabase)
    try:
        raw = svc.run_dispatch(
            admission_id,
            str(body.recipient_email),
            send_email=body.send_email,
            requesting_user_id=current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dispatch failed: {exc}",
        ) from exc

    email_detail = raw.pop("email_detail", {})
    return DispatchResponse(
        dispatch_id=str(raw["id"]),
        admission_id=str(raw["admission_id"]),
        recipient_email=str(raw["recipient_email"]),
        pdf_storage_key=raw.get("pdf_storage_key"),
        dispatch_status=str(raw.get("dispatch_status") or "pending"),
        dispatched_at=_iso(raw.get("dispatched_at")),
        delivered_at=_iso(raw.get("delivered_at")),
        email_detail=email_detail if isinstance(email_detail, dict) else {},
    )


@router.get(
    "/status/{dispatch_id}",
    response_model=DispatchResponse,
    summary="Get dispatch record status",
)
async def get_dispatch_status(
    dispatch_id: str,
    current_user: dict = Depends(require_user),
):
    supabase = get_supabase()
    svc = DispatchService(supabase)
    row = svc.get_dispatch_status(dispatch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dispatch record not found")

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

    return DispatchResponse(
        dispatch_id=str(row["id"]),
        admission_id=str(row["admission_id"]),
        recipient_email=str(row["recipient_email"]),
        pdf_storage_key=row.get("pdf_storage_key"),
        dispatch_status=str(row.get("dispatch_status") or "pending"),
        dispatched_at=_iso(row.get("dispatched_at")),
        delivered_at=_iso(row.get("delivered_at")),
        email_detail={},
    )
