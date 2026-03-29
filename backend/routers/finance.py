"""
NormClaim — Finance Reconciliation Router
POST /api/finance/{admission_id}/reconcile
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Extraction_pipeline.database import get_supabase
from services.auth import require_user
from services.finance_reconciler import FinanceReconciler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/finance", tags=["Finance"])


class ReconcileRequest(BaseModel):
    expected_amount: float
    bill_breakdown: Dict[str, Any]
    diagnoses: List[Dict[str, Any]]
    settlement_override: Optional[Dict[str, Any]] = None


@router.post("/{admission_id}/reconcile")
def reconcile_finance(
    admission_id: str,
    body: ReconcileRequest,
    current_user: dict = Depends(require_user),
):
    """
    Run finance reconciliation for an admission: compare expected vs TPA settlement.
    """
    try:
        svc = FinanceReconciler(get_supabase())
        return svc.run_for_admission(
            admission_id=admission_id,
            expected_amount=body.expected_amount,
            bill_breakdown=body.bill_breakdown,
            diagnoses=body.diagnoses,
            settlement_override=body.settlement_override,
            requesting_user_id=current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("reconcile_finance failed for admission %s", admission_id)
        raise HTTPException(status_code=500, detail=f"Finance reconciliation failed for admission {admission_id} due to an internal error.")
