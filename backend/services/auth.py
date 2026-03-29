"""
NormClaim — Supabase Auth Helpers
Token validation and user extraction for protected API routes.
"""

from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException


def _parse_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return token.strip()


def validate_access_token(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """Validate a Supabase JWT and return normalized user claims."""
    token = _parse_bearer_token(authorization)

    try:
        from main import supabase_auth
    except ImportError as exc:
        raise HTTPException(status_code=503,
            detail=f"Auth service unavailable: {exc}") from exc

    if supabase_auth is None:
        raise HTTPException(status_code=503, detail="Supabase auth client not configured")

    try:
        auth_response = supabase_auth.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(exc)}") from exc

    user = getattr(auth_response, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Unable to resolve user for token")

    user_meta = getattr(user, "user_metadata", {}) or {}
    app_meta = getattr(user, "app_metadata", {}) or {}

    return {
        "id": getattr(user, "id", ""),
        "email": getattr(user, "email", None),
        "role": user_meta.get("role") or app_meta.get("role") or "USER",
    }


def require_user(current_user: Dict[str, Any] = Depends(validate_access_token)) -> Dict[str, Any]:
    """FastAPI dependency to require authenticated Supabase user."""
    return current_user
