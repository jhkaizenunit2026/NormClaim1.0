"""
NormClaim pre-auth / extraction package.

Heavy modules (OCR, PyMuPDF, Gemini pipeline) load only when accessed, so
`from Extraction_pipeline.database import get_supabase` works without importing pymupdf.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ABHALookupService",
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


def __getattr__(name: str) -> Any:
    if name == "ABHALookupService":
        from .abha_lookup import ABHALookupService

        return ABHALookupService
    if name in (
        "CombinedExtraction",
        "DiagnosisReportExtraction",
        "ExtractionPipeline",
        "IdProofExtraction",
        "OCRProcessor",
        "ReferralExtraction",
    ):
        from . import extraction_pipeline as _ep

        return getattr(_ep, name)
    if name in ("PreAuthFiller", "PreAuthOrchestrator", "CorrectionHandler"):
        from . import pre_auth_filling as _pf

        return getattr(_pf, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
