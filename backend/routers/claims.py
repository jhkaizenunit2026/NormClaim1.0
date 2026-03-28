"""
NormClaim — Claims Router
Supabase PostgreSQL-backed claim lifecycle endpoints for SPA integration.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.database import SessionLocal, create_claim, get_claim, list_claims, update_claim_status
from models.schemas import ClaimCreateRequest, ClaimResponse, ClaimStatusUpdateRequest
from services.auth import require_user

router = APIRouter(prefix="/api/claims", tags=["Claims"])


@router.get("", response_model=List[ClaimResponse])
async def fetch_claims(
    status: Optional[str] = Query(default=None),
    stage: Optional[str] = Query(default=None),
    _: dict = Depends(require_user),
):
    """List claims, optionally filtered by status (or legacy stage alias)."""
    desired_status = status or stage
    with SessionLocal() as db:
        return list_claims(db, desired_status)


@router.get("/{claim_id}", response_model=ClaimResponse)
async def fetch_claim(claim_id: str, _: dict = Depends(require_user)):
    """Get claim details by claim ID."""
    with SessionLocal() as db:
        claim = get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.post("", response_model=ClaimResponse)
async def create_claim_endpoint(payload: ClaimCreateRequest, _: dict = Depends(require_user)):
    """Create a new claim at stage PRE_AUTH_INITIATED."""
    claim_id = f"CLM-{str(uuid.uuid4())[:8].upper()}"
    with SessionLocal() as db:
        return create_claim(db, claim_id, payload.model_dump())


@router.patch("/{claim_id}/status", response_model=ClaimResponse)
async def update_claim_status_endpoint(
    claim_id: str,
    payload: ClaimStatusUpdateRequest,
    _: dict = Depends(require_user),
):
    """Update claim status and optional financial fields."""
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, payload.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.post("/{claim_id}/enhancement", response_model=ClaimResponse)
async def submit_enhancement(claim_id: str, payload: dict, _: dict = Depends(require_user)):
    """Legacy enhancement endpoint used by dashboard."""
    patch = {"status": "ENHANCEMENT_REQUESTED"}
    patch.update(payload or {})
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.post("/{claim_id}/discharge", response_model=ClaimResponse)
async def submit_discharge(claim_id: str, payload: dict, _: dict = Depends(require_user)):
    """Legacy discharge endpoint used by dashboard."""
    patch = {"status": "DISCHARGE_INTIMATED"}
    patch.update(payload or {})
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.post("/{claim_id}/settlement", response_model=ClaimResponse)
async def issue_settlement(claim_id: str, payload: dict, _: dict = Depends(require_user)):
    """Legacy settlement endpoint used by dashboard."""
    patch = {"status": "SETTLEMENT_ISSUED"}
    patch.update(payload or {})
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.post("/{claim_id}/finance-entry", response_model=ClaimResponse)
async def record_finance_entry(claim_id: str, payload: dict, _: dict = Depends(require_user)):
    """Legacy finance endpoint used by dashboard."""
    patch = {"status": "FINANCE_PROCESSED"}
    patch.update(payload or {})
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.post("/{claim_id}/close", response_model=ClaimResponse)
async def close_claim(claim_id: str, _: dict = Depends(require_user)):
    """Close claim lifecycle."""
    with SessionLocal() as db:
        updated = update_claim_status(db, claim_id, {"status": "CLOSED"})
    if updated is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return updated


@router.get("/{claim_id}/documents")
async def get_claim_documents(claim_id: str, _: dict = Depends(require_user)):
    """Compatibility endpoint; current implementation returns all uploaded documents."""
    from models.database import list_documents as db_list_documents

    with SessionLocal() as db:
        docs = db_list_documents(db)

    return {"claimId": claim_id, "documents": docs}
