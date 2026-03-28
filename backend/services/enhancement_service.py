"""
NormClaim — Stage 4: enhancement raise (Gemini + optional RAG context).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import google.genai as gen
import instructor
from pydantic import BaseModel, Field

from Extraction_pipeline.database import get_google_api_key, get_supabase
from services.extractor import resolved_gemini_model

logger = logging.getLogger(__name__)

ICD10_SYSTEM_URI = "http://hl7.org/fhir/sid/icd-10"


class CostBreakdownModel(BaseModel):
    room_charges: float = 0
    medicines: float = 0
    procedures: float = 0
    investigations: float = 0
    doctor_fees: float = 0
    nursing_charges: float = 0
    consumables: float = 0
    total: float = 0


class EnhancementLLMOutput(BaseModel):
    justification_text: str
    suggested_amount: float
    severity_score: float = Field(ge=0.0, le=1.0)
    historical_approval_rate: float = Field(ge=0.0, le=1.0)
    cost_breakdown: CostBreakdownModel
    supporting_codes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class EnhancementService:
    SYSTEM_PROMPT = f"""You are a medical insurance enhancement specialist.
Given a diagnosis, procedures, and historical approval patterns,
generate a compelling medical justification for the requested amount.

Rules:
1. Cite diagnosis severity using ICD-10 classification (system URI {ICD10_SYSTEM_URI})
2. Reference standard treatment protocols
3. Include cost breakdown justification
4. Be factual — never fabricate medical information
5. Fill every required field in the structured response; use INR for all amounts
"""

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()
        api_key = get_google_api_key()
        raw_client = gen.Client(api_key=api_key)
        self.client = instructor.from_gemini(
            client=raw_client,
            mode=instructor.Mode.GEMINI_JSON,
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
            "stage": "enhancement",
            "action": action,
            "table_affected": "enhancement_requests",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    def _historical_approval_rate(self) -> float:
        """RAG-lite: empirical approval share from past enhancement rows (stub fallback)."""
        try:
            resp = self.db.table("enhancement_requests").select("status").execute()
            rows = resp.data or []
            if not rows:
                return 0.78
            approved = sum(1 for r in rows if str(r.get("status") or "") == "approved")
            return round(approved / len(rows), 4)
        except Exception as exc:
            logger.warning("historical approval rate fallback: %s", exc)
            return 0.78

    def _fetch_admission(self, admission_id: str) -> dict | None:
        resp = (
            self.db.table("admissions")
            .select("*")
            .eq("id", admission_id)
            .single()
            .execute()
        )
        return resp.data

    def _patient_id_for_admission(self, admission_row: dict) -> str | None:
        pid = admission_row.get("patient_id")
        return str(pid) if pid else None

    def generate_enhancement(
        self,
        admission_id: str,
        diagnosis_data: list[dict],
        procedures: list[dict],
        requested_amount: float,
        requesting_user_id: str | None,
    ) -> dict:
        admission = self._fetch_admission(admission_id)
        if not admission:
            raise ValueError(f"admission {admission_id} not found")

        st = str(admission.get("status") or "").lower()
        if st in {"cancelled"}:
            raise PermissionError("Cannot create enhancement for a cancelled admission")

        hist = self._historical_approval_rate()
        payload = {
            "admission_id": admission_id,
            "admission_number": admission.get("admission_number"),
            "diagnosis_data": diagnosis_data,
            "procedures": procedures,
            "original_amount_inr": requested_amount,
            "dataset_historical_approval_rate": hist,
        }
        user_prompt = (
            "CONTEXT (JSON):\n"
            f"{json.dumps(payload, ensure_ascii=False)[:12000]}\n\n"
            "Produce justification and a fully specified cost_breakdown; "
            "suggested_amount should be at least the original_amount_inr when medically warranted."
        )

        try:
            llm: EnhancementLLMOutput = self.client.chat.completions.create(
                model=resolved_gemini_model(),
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=EnhancementLLMOutput,
            )
        except Exception as exc:
            logger.exception("Enhancement Gemini call failed")
            raise RuntimeError(f"Enhancement generation failed: {exc}") from exc

        breakdown = llm.cost_breakdown.model_dump()
        enhancement_id = str(uuid.uuid4())
        patient_id = self._patient_id_for_admission(admission)

        row = {
            "id": enhancement_id,
            "admission_id": admission_id,
            "original_amount": float(requested_amount),
            "suggested_amount": float(llm.suggested_amount),
            "justification_text": llm.justification_text,
            "severity_score": float(llm.severity_score),
            "cost_breakdown": breakdown,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.table("enhancement_requests").insert(row).execute()

        out = {
            "enhancement_id": enhancement_id,
            "admission_id": admission_id,
            "status": "draft",
            "original_amount": float(requested_amount),
            "payload": {
                "justification_text": llm.justification_text,
                "suggested_amount": float(llm.suggested_amount),
                "severity_score": float(llm.severity_score),
                "historical_approval_rate": float(llm.historical_approval_rate),
                "cost_breakdown": breakdown,
                "supporting_codes": list(llm.supporting_codes),
                "confidence": float(llm.confidence),
            },
        }

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            action="enhancement.generated",
            record_id=enhancement_id,
            diff_snapshot={
                "admission_id": admission_id,
                "suggested_amount": out["payload"]["suggested_amount"],
            },
        )
        return out

    def get_enhancement(self, enhancement_id: str) -> dict | None:
        resp = (
            self.db.table("enhancement_requests")
            .select("*")
            .eq("id", enhancement_id)
            .single()
            .execute()
        )
        return resp.data

    def update_with_tpa_response(
        self,
        enhancement_id: str,
        tpa_response: dict,
        status: str | None,
        requesting_user_id: str | None,
    ) -> dict:
        enh = self.get_enhancement(enhancement_id)
        if not enh:
            raise ValueError(f"enhancement {enhancement_id} not found")

        admission_id = str(enh.get("admission_id") or "")
        admission = self._fetch_admission(admission_id) if admission_id else None
        patient_id = self._patient_id_for_admission(admission) if admission else None

        update_payload: dict[str, Any] = {"tpa_response": tpa_response}
        if status:
            allowed = {"draft", "submitted", "approved", "rejected"}
            s = str(status).strip().lower()
            if s not in allowed:
                raise ValueError(f"Invalid status; must be one of {sorted(allowed)}")
            update_payload["status"] = s

        self.db.table("enhancement_requests").update(update_payload).eq(
            "id", enhancement_id
        ).execute()

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            action="enhancement.tpa_updated",
            record_id=enhancement_id,
            diff_snapshot={
                "admission_id": admission_id,
                "status": update_payload.get("status"),
                "tpa_response_keys": list(tpa_response.keys()) if tpa_response else [],
            },
        )
        final = self.get_enhancement(enhancement_id)
        return final or {**enh, **update_payload}
