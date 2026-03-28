"""
database.py — Supabase connection factory for NormClaim pre-auth module
=======================================================================
Provides a singleton Supabase client shared across the service.
Reads credentials from environment variables / .env file.

Required env vars:


Python 3.11 required.
"""

    

from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Return a cached Supabase client.
    Uses service_role key so the pipeline can bypass RLS
    (running as trusted backend service, not as a user).
    """
    try:
        from main import supabase_admin

        if supabase_admin is not None:
            return supabase_admin
    except Exception:
        # Fall back to local env-based client for isolated usage (scripts/tests).
        pass

    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )

    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment. "
            "Copy .env.example to .env and fill in your Supabase project credentials."
        )

    client = create_client(url, key)
    logger.info("Supabase client initialised for: %s", url)
    return client


def get_google_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise EnvironmentError(
            "GOOGLE_API_KEY (or GEMINI_API_KEY) must be set in environment."
        )
    return key
