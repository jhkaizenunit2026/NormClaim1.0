"""
NormClaim — Auth Router
Session introspection endpoint backed by Supabase auth.
"""

from fastapi import APIRouter, Depends

from services.auth import require_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/session")
async def get_session(current_user: dict = Depends(require_user)):
    """Validate bearer token and return normalized user/session info."""
    return {
        "user": {
            "id": current_user.get("id"),
            "email": current_user.get("email"),
            "role": current_user.get("role"),
        }
    }
