"""
NormClaim — Analytics API
GET /api/analytics — dashboard metrics (Stage 9 feedback loop + reconciliation).
"""

from fastapi import APIRouter

from models.schemas import AnalyticsSnapshot
from routers.documents import DOCUMENTS
from routers.extract import EXTRACTIONS
from routers.reconcile import REPORTS
from services.analytics_service import build_snapshot
from services.feedback_service import FEEDBACK

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _get_supabase_client():
    try:
        from main import supabase
        return supabase
    except Exception:
        return None


@router.get("", response_model=AnalyticsSnapshot)
async def get_analytics():
    """Aggregate counts, average claim delta, and feedback mix."""
    supabase = _get_supabase_client()
    doc_count = len(DOCUMENTS)
    if supabase is not None:
        try:
            rows = supabase.table("documents").select("id").execute().data or []
            doc_count = max(doc_count, len(rows))
        except Exception:
            pass
    return build_snapshot(doc_count, EXTRACTIONS, REPORTS, FEEDBACK, supabase)
