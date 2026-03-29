"""
NormClaim — Main FastAPI Application
AI-powered Clinical & Administrative Data Normalization Engine
for Indian SME hospitals.

Run with: uvicorn main:app --reload --port 8000
"""

import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# ── Configure logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("normclaim")

# ── Create FastAPI app ────────────────────────────────────────────────────
app = FastAPI(
    title="NormClaim API",
    description=(
        "AI-powered Clinical & Administrative Data Normalization Engine. "
        "Upload discharge summaries, extract clinical entities via Gemini AI, "
        "generate FHIR R4 bundles, and run ICD-10 claim reconciliation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS middleware ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ──────────────────────────────────────────────────────
from routers.documents import router as documents_router
from routers.extract import router as extract_router
from routers.fhir import router as fhir_router
from routers.reconcile import router as reconcile_router
from routers.review import router as review_router
from routers.feedback import router as feedback_router
from routers.validate import router as validate_router
from routers.analytics import router as analytics_router
from routers.auth import router as auth_router
from routers.config import router as config_router
from routers.claims import router as claims_router
from routers.admissions import router as admissions_router
from routers.enhancements import router as enhancements_router
from routers.discharge import router as discharge_router
from routers.dispatch import router as dispatch_router
from routers.settlements import router as settlements_router
from routers.finance_recon import router as finance_recon_router
from routers.notifications import router as notifications_router
from Extraction_pipeline.router import router as preauth_router

app.include_router(documents_router)
app.include_router(extract_router)
app.include_router(fhir_router)
app.include_router(reconcile_router)
app.include_router(review_router)
app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(validate_router)
app.include_router(auth_router)
app.include_router(config_router)
app.include_router(claims_router)
app.include_router(admissions_router)
app.include_router(enhancements_router)
app.include_router(discharge_router)
app.include_router(dispatch_router)
app.include_router(settlements_router)
app.include_router(finance_recon_router)
app.include_router(notifications_router)
app.include_router(preauth_router, prefix="/api/preauth", tags=["pre-auth"])


# ── Supabase Client Setup ────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_KEY")
    or os.environ.get("SUPABASE_KEY")
)

supabase_auth: Optional[Client] = None
supabase_admin: Optional[Client] = None
supabase: Optional[Client] = None  # Backward compatibility alias for existing modules.

if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_ROLE_KEY:
    raise EnvironmentError(
        "Supabase credentials missing. Required env vars: SUPABASE_URL, "
        "SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY"
    )

supabase_auth = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
supabase = supabase_admin
logger.info("✓  Supabase clients initialized (anon + service role)")

# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    gemini_configured = bool(os.environ.get("GEMINI_API_KEY"))
    supabase_configured = bool(SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY)
    return {
        "status": "ok",
        "service": "normclaim-backend",
        "version": "1.0.0",
        "gemini_api_key_configured": gemini_configured,
        "supabase_configured": supabase_configured,
    }


@app.get("/health/gemini", tags=["System"])
async def health_gemini():
    """
    Live Gemini check (one short model call). Use after rotating keys or to confirm quota.
    """
    from services.extractor import (
        GeminiQuotaExceededError,
        probe_gemini_api_key,
        resolved_gemini_model,
    )

    try:
        probe = probe_gemini_api_key()
        return {"status": "ok", **probe}
    except GeminiQuotaExceededError as e:
        detail: dict = {
            "code": "GEMINI_QUOTA_EXHAUSTED",
            "message": str(e),
            "model": resolved_gemini_model(),
        }
        if e.provider_details:
            detail["provider_details"] = e.provider_details
        raise HTTPException(status_code=503, detail=detail)
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail={"code": "GEMINI_NOT_CONFIGURED", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"code": "GEMINI_PROBE_FAILED", "message": str(e)},
        )


# ── Startup event ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("  NormClaim Backend — Starting up")
    logger.info("=" * 60)

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        logger.warning(
            "⚠  GEMINI_API_KEY not set! "
            "Get one free at: https://aistudio.google.com/app/apikey"
        )
    else:
        logger.info(f"✓  Gemini API key configured (ends with ...{gemini_key[-4:]})")

    fhir_url = os.environ.get("FHIR_SERVICE_URL", "http://localhost:8001/fhir/bundle")
    logger.info(f"✓  FHIR service URL: {fhir_url}")
    logger.info("✓  API docs available at: http://localhost:8000/docs")

    from services.persistence import bootstrap_memory_caches
    from Extraction_pipeline.database import get_supabase as get_extraction_supabase

    try:
        bootstrap_memory_caches()
    except Exception as e:
        logger.warning("SQLite bootstrap skipped or failed: %s", e)

    try:
        extraction_supabase = get_extraction_supabase()
        extraction_supabase.table("pre_auth_forms").select("id").limit(1).execute()
        logger.info("✓  Extraction pipeline readiness check passed")
    except Exception as e:
        logger.warning("⚠  Extraction pipeline readiness check failed: %s", e)

    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
