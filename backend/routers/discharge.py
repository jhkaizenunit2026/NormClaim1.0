"""
NormClaim — Discharge Router
POST /api/discharge/{admission_id}
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Extraction_pipeline.database import get_supabase
from services.auth import require_user
from services.discharge_service import DischargeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/discharge", tags=["Discharge"])


class DischargeRequest(BaseModel):
    document_id: Optional[str] = None
    bill_notes: Optional[str] = None


@router.post("/{admission_id}")
async def process_discharge(
    admission_id: str,
    body: DischargeRequest,
    current_user: dict = Depends(require_user),
):
    """
    Process discharge for an admission: generate bill breakdown, FHIR bundle,
    and discharge summary.
    """
    try:
        svc = DischargeService(get_supabase())
        result = await svc.process_discharge(
            admission_id,
            document_id=body.document_id,
            bill_notes=body.bill_notes,
            requesting_user_id=current_user.get("id"),
        )
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("process_discharge failed for admission %s", admission_id)
        raise HTTPException(status_code=500, detail=f"Discharge processing failed for admission {admission_id} due to an internal error.")
