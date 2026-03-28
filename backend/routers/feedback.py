"""
NormClaim — Feedback Router
Endpoints for correction feedback and quality tracking.
"""

from typing import List

from fastapi import APIRouter, Depends

from models.schemas import FeedbackItem
from services.feedback_service import save_feedback, get_feedback
from services.auth import require_user

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


def _get_supabase_client():
    try:
        from main import supabase
        return supabase
    except Exception:
        return None


@router.post("/{document_id}", response_model=FeedbackItem)
async def submit_feedback(document_id: str, feedback: FeedbackItem, _: dict = Depends(require_user)):
    """Store a feedback event for extraction quality."""
    feedback.document_id = document_id
    return save_feedback(feedback, _get_supabase_client())


@router.get("/{document_id}", response_model=List[FeedbackItem])
async def fetch_feedback(document_id: str, _: dict = Depends(require_user)):
    """Get all feedback items for a document."""
    return get_feedback(document_id, _get_supabase_client())
