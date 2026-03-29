"""
NormClaim — Enhancement Router
POST /api/enhancement/{admission_id}
GET  /api/enhancement/{enhancement_id}
PATCH /api/enhancement/{enhancement_id}/tpa
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Extraction_pipeline.database import get_supabase
from services.auth import require_user
from services.enhancement_service import EnhancementService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enhancement", tags=["Enhancement"])


class EnhancementRequest(BaseModel):
    diagnosis_data: List[dict]
    procedures: List[dict]
    requested_amount: float


class TPAUpdateRequest(BaseModel):
    tpa_response: dict
    status: Optional[str] = None


@router.post("/{admission_id}")
def generate_enhancement(
    admission_id: str,
    body: EnhancementRequest,
    current_user: dict = Depends(require_user),
):
    """Generate an enhancement justification for an admission."""
    try:
        svc = EnhancementService(get_supabase())
        return svc.generate_enhancement(
            admission_id=admission_id,
            diagnosis_data=body.diagnosis_data,
            procedures=body.procedures,
            requested_amount=body.requested_amount,
            requesting_user_id=current_user.get("id"),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("generate_enhancement failed for admission %s", admission_id)
        raise HTTPException(status_code=500, detail=f"Enhancement generation failed for admission {admission_id} due to an internal error.")


@router.get("/{enhancement_id}")
def get_enhancement(
    enhancement_id: str,
    current_user: dict = Depends(require_user),
):
    """Get a specific enhancement record."""
    svc = EnhancementService(get_supabase())
    result = svc.get_enhancement(enhancement_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Enhancement {enhancement_id} not found")
    return result


@router.patch("/{enhancement_id}/tpa")
def update_tpa_response(
    enhancement_id: str,
    body: TPAUpdateRequest,
    current_user: dict = Depends(require_user),
):
    """Update an enhancement record with TPA response."""
    try:
        svc = EnhancementService(get_supabase())
        return svc.update_with_tpa_response(
            enhancement_id=enhancement_id,
            tpa_response=body.tpa_response,
            status=body.status,
            requesting_user_id=current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("update_tpa_response failed for enhancement %s", enhancement_id)
        raise HTTPException(status_code=500, detail=f"TPA update failed for enhancement {enhancement_id} due to an internal error.")
