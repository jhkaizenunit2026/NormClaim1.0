"""
preauth_module — NormClaim Pre-Auth Auto-Fill Module
=====================================================
Public API surface:

    from preauth_module import PreAuthOrchestrator, CorrectionHandler
    from preauth_module.database import get_supabase, get_google_api_key

Quick start:
    from preauth_module import PreAuthOrchestrator
    from preauth_module.database import get_supabase, get_google_api_key

    orchestrator = PreAuthOrchestrator(get_supabase(), get_google_api_key())
    result = orchestrator.process(pre_auth_form_id="<uuid>", requesting_user_id="<uuid>")
    print(result["form_status"])   # "auto_filled" or "pending_manual"
    print(result["auto_filled_fields"])
"""

from .extraction_pipeline import (
    CombinedExtraction,
    DiagnosisReportExtraction,
    ExtractionPipeline,
    IdProofExtraction,
    OCRProcessor,
    ReferralExtraction,
)
from .pre_auth_filling import (
    CorrectionHandler,
    PreAuthFiller,
    PreAuthOrchestrator,
)

__all__ = [
    "ExtractionPipeline",
    "PreAuthFiller",
    "PreAuthOrchestrator",
    "CorrectionHandler",
    "OCRProcessor",
    "CombinedExtraction",
    "IdProofExtraction",
    "DiagnosisReportExtraction",
    "ReferralExtraction",
]
