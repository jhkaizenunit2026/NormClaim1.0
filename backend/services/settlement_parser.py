"""
NormClaim — Stage 8: TPA settlement letter OCR + Gemini structured extraction.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import google.genai as gen
import instructor

from Extraction_pipeline.database import get_google_api_key, get_supabase
from models.schemas import SettlementLetterExtraction
from services.extractor import resolved_gemini_model

logger = logging.getLogger(__name__)


class SettlementParser:
    SYSTEM_PROMPT = """You extract structured financial data from Indian TPA / insurer settlement letters.
Rules:
1. Amounts are in INR unless another currency is explicitly stated (then convert note only in remarks).
2. UTR / reference numbers: preserve exactly as printed.
3. settlement_date as YYYY-MM-DD when possible; else ISO date string as in document.
4. deductions: line items with description, amount, optional reason.
5. final_payable is the net credited / payable to hospital after TDS and deductions when explicit.
6. If a field is missing, use null — do not invent UTRs or amounts.
7. confidence: 0.0–1.0 for overall extraction quality.
"""

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()
        api_key = get_google_api_key()
        raw_client = gen.Client(api_key=api_key)
        self._client = instructor.from_genai(
            client=raw_client,
            mode=instructor.Mode.GENAI_TOOLS,
        )

    def _audit_log(
        self,
        *,
        patient_id: str | None,
        user_id: str | None,
        action: str,
        record_id: str | None,
        diff_snapshot: dict | None = None,
    ) -> None:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "stage": "settlement",
            "action": action,
            "table_affected": "settlement_records",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    def _ocr_text(self, file_bytes: bytes, file_format: str) -> str:
        from Extraction_pipeline.extraction_pipeline import OCRProcessor

        fmt = (file_format or "pdf").lower().strip()
        return OCRProcessor.extract_text(file_bytes, fmt)

    def parse(self, file_bytes: bytes, file_format: str) -> SettlementLetterExtraction:
        raw_text = self._ocr_text(file_bytes, file_format)
        if not raw_text or len(raw_text.strip()) < 10:
            raise ValueError("Could not extract sufficient text from the settlement document")

        user_prompt = f"Document text:\n{raw_text[:12000]}\n\nExtract structured settlement fields."
        return self._client.chat.completions.create(
            model=resolved_gemini_model(),
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=SettlementLetterExtraction,
        )

    def persist(
        self,
        admission_id: str | None,
        extraction: SettlementLetterExtraction,
        *,
        requesting_user_id: str | None = None,
        patient_id: str | None = None,
    ) -> str:
        sid = str(uuid.uuid4())
        deductions_payload = [d.model_dump(exclude_none=True) for d in extraction.deductions]
        row = {
            "id": sid,
            "admission_id": admission_id,
            "utr_number": extraction.utr_number,
            "settlement_amount": extraction.settlement_amount,
            "tds_amount": extraction.tds_amount,
            "deductions": deductions_payload,
            "final_payable": extraction.final_payable,
            "settlement_date": extraction.settlement_date,
            "remarks": extraction.remarks,
            "confidence": extraction.confidence,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.table("settlement_records").insert(row).execute()
        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            action="settlement.parsed",
            record_id=sid,
            diff_snapshot={"admission_id": admission_id, "utr_number": extraction.utr_number},
        )
        return sid
