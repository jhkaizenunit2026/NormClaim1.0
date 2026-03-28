"""
NormClaim — Public Runtime Config Router
Exposes only safe browser config values.
"""

import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("/public")
async def public_config():
    """Return browser-safe runtime config for Supabase JS client bootstrap."""
    return {
        "supabaseUrl": os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL"),
        "supabaseAnonKey": os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    }
