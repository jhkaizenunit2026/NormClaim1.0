"""
NormClaim — Stage 5: discharge intimation orchestration (summary + bill + FHIR).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import google.genai as gen
import instructor

from Extraction_pipeline.database import get_google_api_key, get_supabase
from models.schemas import (
    BillBreakdown,
    Diagnosis,
    EncounterInfo,
    ExtractionResult,
    PatientInfo,
)
from services.extractor import resolved_gemini_model
from services.fhir_client import check_fhir_health, generate_fhir_bundle
from services.fhir_mapper import build_fhir_bundle_local
from services.persistence import load_extraction_result

logger = logging.getLogger(__name__)


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


class DischargeService:
    """Orchestrates discharge summary context, Gemini bill breakdown, and FHIR bundle."""

    BILL_SYSTEM_PROMPT = """You are a hospital billing analyst for Indian private hospitals.
Given admission context (JSON) and optional bill notes, estimate a plausible INR bill breakdown
at discharge. Use conservative, defensible amounts; align total with the ceiling_hint_inr when provided.
Rules:
1. All amounts in INR; non-negative floats.
2. total should approximately equal the sum of line categories (within 1%).
3. confidence reflects certainty given input quality (0.0–1.0).
4. Do not claim specific branded devices or fabricated procedures not implied by the context.
"""

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()
        api_key = get_google_api_key()
        raw_client = gen.Client(api_key=api_key)
        self._instructor = instructor.from_genai(
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
            "stage": "discharge",
            "action": action,
            "table_affected": "admissions",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    def _fetch_admission(self, admission_id: str) -> dict | None:
        resp = (
            self.db.table("admissions")
            .select("*")
            .eq("id", admission_id)
            .single()
            .execute()
        )
        return resp.data

    def _fetch_patient(self, patient_id: str) -> dict:
        resp = (
            self.db.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        return resp.data or {}

    def _fetch_pre_auth(self, pre_auth_form_id: str | None) -> dict:
        if not pre_auth_form_id:
            return {}
        resp = (
            self.db.table("pre_auth_forms")
            .select("*")
            .eq("id", str(pre_auth_form_id))
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}

    def _extract_bill_breakdown(
        self,
        context: dict,
        bill_notes: str | None,
    ) -> BillBreakdown:
        ceiling = context.get("ceiling_hint_inr")
        payload = {
            **context,
            "bill_notes": bill_notes or "",
            "ceiling_hint_inr": ceiling,
        }
        user_prompt = (
            "CONTEXT:\n"
            f"{json.dumps(payload, ensure_ascii=False, default=str)[:10000]}\n\n"
            "Return the structured bill breakdown."
        )
        return self._instructor.chat.completions.create(
            model=resolved_gemini_model(),
            messages=[
                {"role": "system", "content": self.BILL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=BillBreakdown,
        )

    def _fallback_extraction(
        self,
        admission_id: str,
        admission: dict,
        patient: dict,
    ) -> ExtractionResult:
        admit_ts = _iso(admission.get("admitted_at"))
        return ExtractionResult(
            document_id=f"admission-{admission_id}",
            patient=PatientInfo(
                name=patient.get("patient_name"),
                age=patient.get("age"),
                sex=patient.get("gender"),
                abha_id=patient.get("abha_id"),
            ),
            encounter=EncounterInfo(
                admit_date=admit_ts,
                discharge_date=datetime.now(timezone.utc).isoformat(),
                ward=None,
                los_days=None,
            ),
            diagnoses=[
                Diagnosis(
                    text="Discharge documentation pending or supplied via separate document",
                    icd10_code="Z09",
                    icd10_display="Encounter for follow-up examination after completed treatment",
                    is_primary=True,
                    confidence=0.35,
                    negated=False,
                    uncertainty="possible",
                    section="discharge",
                )
            ],
            procedures=[],
            medications=[],
            billed_codes=["Z09"],
            raw_text_preview="",
            detected_script=None,
            section_map={},
            negated_spans=[],
            low_confidence_flags=["synthetic_admission_stub"],
        )

    def _merge_extraction_stub(
        self,
        base: ExtractionResult,
        loaded: ExtractionResult,
    ) -> ExtractionResult:
        """Prefer stored extraction; keep document_id from loaded for FHIR traceability."""
        data = loaded.model_dump()
        data.setdefault("patient", base.patient.model_dump())
        if not data.get("patient", {}).get("name"):
            data["patient"] = base.patient.model_dump()
        return ExtractionResult(**data)

    async def _resolve_fhir_bundle(
        self,
        document_id: str | None,
        fallback: ExtractionResult,
    ) -> tuple[dict, str]:
        extraction = load_extraction_result(document_id) if document_id else None
        if extraction is not None:
            model = self._merge_extraction_stub(fallback, extraction)
        else:
            model = fallback

        healthy = await check_fhir_health()
        if healthy:
            try:
                bundle = await generate_fhir_bundle(model)
                return bundle, "hapi"
            except Exception as exc:
                logger.warning("HAPI FHIR failed, using local mapper: %s", exc)

        bundle = build_fhir_bundle_local(model)
        bundle.setdefault("meta", {})["tag"] = [{"code": "local-fallback"}]
        return bundle, "local-fallback"

    def _icp_applicable(self, extraction: ExtractionResult | None, bill: BillBreakdown) -> bool:
        if extraction is None:
            return False
        if bill.total <= 0 or bill.confidence < 0.5:
            return False
        return any(d.is_primary and not d.negated for d in extraction.diagnoses)

    async def process_discharge(
        self,
        admission_id: str,
        *,
        document_id: str | None = None,
        bill_notes: str | None = None,
        requesting_user_id: str | None = None,
    ) -> dict:
        admission = self._fetch_admission(admission_id)
        if not admission:
            raise ValueError(f"admission {admission_id} not found")

        st = str(admission.get("status") or "").lower()
        if st in {"cancelled"}:
            raise PermissionError("Cannot process discharge for a cancelled admission")

        patient_id = str(admission.get("patient_id") or "")
        if not patient_id:
            raise ValueError("Admission has no patient_id")

        patient = self._fetch_patient(patient_id)
        pre_auth = self._fetch_pre_auth(admission.get("pre_auth_form_id"))

        ceiling = pre_auth.get("requested_amount_inr")
        if ceiling is None:
            ceiling = pre_auth.get("estimated_amount_inr")

        context = {
            "admission_id": admission_id,
            "admission_number": admission.get("admission_number"),
            "patient_id": patient_id,
            "patient_name": patient.get("patient_name"),
            "pre_auth_form_id": admission.get("pre_auth_form_id"),
            "primary_diagnosis_text": pre_auth.get("primary_diagnosis_text"),
            "planned_procedure": pre_auth.get("planned_procedure"),
            "estimated_los_days": pre_auth.get("estimated_los_days"),
            "ceiling_hint_inr": float(ceiling) if ceiling is not None else None,
        }

        bill = self._extract_bill_breakdown(context, bill_notes)

        fallback = self._fallback_extraction(admission_id, admission, patient)
        loaded = load_extraction_result(document_id) if document_id else None
        extraction_for_icp = loaded if loaded is not None else None

        fhir_bundle, fhir_source = await self._resolve_fhir_bundle(document_id, fallback)

        discharge_summary = {
            "admission_id": admission_id,
            "admission_number": admission.get("admission_number"),
            "patient_id": patient_id,
            "patient_name": patient.get("patient_name"),
            "admitted_at": _iso(admission.get("admitted_at")),
            "pre_auth_snapshot": {
                "pre_auth_form_id": admission.get("pre_auth_form_id"),
                "primary_diagnosis_text": pre_auth.get("primary_diagnosis_text"),
                "requested_amount_inr": pre_auth.get("requested_amount_inr"),
            },
            "document_id": document_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bill_notes": bill_notes or "",
        }

        icp_generated = self._icp_applicable(extraction_for_icp, bill)

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            action="discharge.processed",
            record_id=admission_id,
            diff_snapshot={
                "document_id": document_id,
                "bill_total": bill.total,
                "fhir_source": fhir_source,
                "icp_generated": icp_generated,
            },
        )

        return {
            "admission_id": admission_id,
            "discharge_summary": discharge_summary,
            "fhir_bundle": fhir_bundle,
            "bill_breakdown": bill.model_dump(),
            "icp_generated": icp_generated,
            "fhir_source": fhir_source,
        }
