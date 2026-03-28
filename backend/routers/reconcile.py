"""
NormClaim — Reconciliation Router
Runs the ICD-10 claim gap analysis comparing extracted vs billed codes.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import ReconciliationReport
from services.reconciler import reconcile
from routers.extract import EXTRACTIONS

router = APIRouter(prefix="/api/reconcile", tags=["Reconciliation"])

# In-memory report store
REPORTS: dict = {}


def _ensure_extraction_for_reconcile(document_id: str) -> None:
    from services.persistence import load_extraction_result

    if document_id in EXTRACTIONS:
        return
    ex = load_extraction_result(document_id)
    if ex:
        EXTRACTIONS[document_id] = ex


@router.post("/{document_id}", response_model=ReconciliationReport)
async def run_reconciliation(document_id: str):
    """Run reconciliation on an extracted document."""
    _ensure_extraction_for_reconcile(document_id)
    if document_id not in EXTRACTIONS:
        raise HTTPException(
            status_code=404,
            detail="Extract first: POST /api/extract/{id}",
        )
    report = reconcile(EXTRACTIONS[document_id])
    REPORTS[document_id] = report
    from services.persistence import save_reconciliation_report
    from models.database import SessionLocal

    try:
        with SessionLocal() as db:
            save_reconciliation_report(db, report)
    except Exception:
        pass
    return report


@router.get("/{document_id}", response_model=ReconciliationReport)
async def get_report(document_id: str):
    """Retrieve a previous reconciliation report."""
    if document_id not in REPORTS:
        from services.persistence import load_reconciliation_report

        report = load_reconciliation_report(document_id)
        if report:
            REPORTS[document_id] = report
        else:
            raise HTTPException(status_code=404, detail="No report found")
    return REPORTS[document_id]
