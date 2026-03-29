"""
NormClaim — Notifications Router
Provides notification retrieval for the frontend dashboard.
"""

from typing import List, Dict, Any

from fastapi import APIRouter, Depends

from services.auth import require_user

router = APIRouter(prefix="/api", tags=["Notifications"])


@router.get("/notifications", response_model=List[Dict[str, Any]])
async def get_notifications(current_user: dict = Depends(require_user)):
    """
    Return notifications for the authenticated user.

    Currently returns an empty list — will be backed by a persistent
    notification store (Supabase table or Redis) in a future iteration.
    """
    # TODO: Query notifications from DB filtered by current_user["id"]
    return []
