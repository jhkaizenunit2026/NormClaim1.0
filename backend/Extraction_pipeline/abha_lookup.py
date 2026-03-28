"""
abha_lookup.py — ABDM ABHA patient lookup + merge with IdProof extraction
============================================================================
Per NormClaim master prompt: prefer ABHA-verified demographics over OCR.
Sandbox API is optional (off by default); hospital `patients` row is the
hackathon fallback when ABDM is unavailable.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any, Literal

import httpx
from supabase import Client

if TYPE_CHECKING:
    from .extraction_pipeline import DiagnosisReportExtraction, IdProofExtraction, ReferralExtraction

logger = logging.getLogger(__name__)

IdentitySource = Literal["abha", "hospital_db", "extraction"]

_ABHA_PATTERN = re.compile(
    r"^91-\d{4}-\d{4}-\d{4}$",
    re.IGNORECASE,
)


class ABHALookupService:
    """Resolve patient demographics: ABDM (optional) → hospital DB → extraction only."""

    FHIR_BASE = "https://healthidsbx.abdm.gov.in/api"

    def __init__(self, supabase: Client):
        self.db = supabase

    @staticmethod
    def normalize_abha_id(raw: str | None) -> str | None:
        if not raw or not str(raw).strip():
            return None
        s = str(raw).strip().upper().replace(" ", "")
        if _ABHA_PATTERN.match(s):
            return s
        digits = re.sub(r"\D", "", s)
        if len(digits) >= 14 and digits.startswith("91"):
            core = digits[2:14]
            return f"91-{core[0:4]}-{core[4:8]}-{core[8:12]}"
        return None

    def fetch_patient(self, abha_id: str) -> dict | None:
        """
        Fetch patient demographics from ABDM sandbox FHIR-style endpoint.
        Disabled unless ABDM_FETCH_PATIENT_ENABLED is truthy; returns None on failure.
        """
        enabled = os.getenv("ABDM_FETCH_PATIENT_ENABLED", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not enabled:
            return None

        url = f"{self.FHIR_BASE.rstrip('/')}/v1/ha/hip/fetchPatient/{abha_id}"
        try:
            resp = httpx.get(url, timeout=15.0)
            if resp.status_code != 200:
                logger.info(
                    "ABDM fetchPatient non-200: status=%s abha_id=%s",
                    resp.status_code,
                    abha_id,
                )
                return None
            payload = resp.json()
        except Exception as exc:
            logger.warning("ABDM fetchPatient failed: %s", exc)
            return None

        return self._flatten_abdm_patient(payload)

    def _flatten_abdm_patient(self, payload: Any) -> dict[str, Any] | None:
        """Best-effort map of unknown ABDM JSON → IdProof-relevant keys."""
        if not isinstance(payload, dict):
            return None
        patient = payload.get("patient") or payload.get("data") or payload
        if not isinstance(patient, dict):
            return None
        out: dict[str, Any] = {}
        name = patient.get("name") or patient.get("patientName")
        if isinstance(name, str) and name.strip():
            out["patient_name"] = name.strip()
        elif isinstance(name, list) and name:
            first = name[0]
            if isinstance(first, dict):
                parts = [
                    first.get("text"),
                    first.get("given"),
                    first.get("family"),
                ]
                flat = " ".join(
                    str(p).strip()
                    for p in parts
                    if p and str(p).strip()
                )
                if flat:
                    out["patient_name"] = flat
        for key, target in (
            ("birthDate", "dob"),
            ("gender", "gender"),
            ("address", "address"),
        ):
            v = patient.get(key)
            if isinstance(v, str) and v.strip():
                out[target] = v.strip()
        hid = patient.get("abhaId") or patient.get("healthId") or patient.get("abha_id")
        if isinstance(hid, str) and hid.strip():
            norm = self.normalize_abha_id(hid.strip())
            if norm:
                out["abha_id"] = norm
        return out or None

    def _load_patient_row(self, patient_id: str) -> dict[str, Any]:
        resp = (
            self.db.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        return resp.data or {}

    def _patient_row_to_demographics(self, row: dict[str, Any]) -> dict[str, Any] | None:
        out: dict[str, Any] = {}
        name = row.get("patient_name") or row.get("name")
        if isinstance(name, str) and name.strip():
            out["patient_name"] = name.strip()
        abha = row.get("abha_id")
        if isinstance(abha, str) and abha.strip():
            norm = self.normalize_abha_id(abha.strip())
            if norm:
                out["abha_id"] = norm
        for src, dest in (
            ("gender", "gender"),
            ("dob", "dob"),
            ("date_of_birth", "dob"),
            ("address", "address"),
            ("city", "city"),
            ("state", "state"),
            ("pincode", "pincode"),
            ("postal_code", "pincode"),
        ):
            v = row.get(src)
            if isinstance(v, str) and v.strip():
                out.setdefault(dest, v.strip())
        id_type = row.get("id_proof_type") or row.get("id_type")
        if isinstance(id_type, str) and id_type.strip():
            out["id_proof_type"] = id_type.strip().lower()
        id_num = row.get("id_proof_number") or row.get("id_number")
        if isinstance(id_num, str) and id_num.strip():
            out["id_proof_number"] = id_num.strip()
        return out or None

    def resolve_demographics(
        self,
        extracted_abha_id: str | None,
        patient_id: str,
    ) -> tuple[dict[str, Any] | None, IdentitySource]:
        """
        1. If ABHA (from OCR or hospital record) and ABDM fetch succeeds → abha.
        2. Else if hospital patients row has demographics → hospital_db.
        3. Else → extraction only (no overlay dict).
        """
        row = self._load_patient_row(patient_id)
        hospital_demo = self._patient_row_to_demographics(row) if row else None

        abha_norm = self.normalize_abha_id(extracted_abha_id) or self.normalize_abha_id(
            row.get("abha_id") if row else None
        )
        if abha_norm:
            abdm = self.fetch_patient(abha_norm)
            if abdm:
                return abdm, "abha"

        if hospital_demo:
            return hospital_demo, "hospital_db"

        return None, "extraction"

    def merge_with_extraction(
        self,
        abha_data: dict[str, Any] | None,
        extraction: IdProofExtraction,
    ) -> IdProofExtraction:
        """ABHA / hospital demographics take precedence over OCR extraction fields."""
        from .extraction_pipeline import IdProofExtraction as IdProofModel

        if not abha_data:
            return extraction
        data = extraction.model_dump()
        skip = frozenset({"confidence"})
        for key, value in abha_data.items():
            if key in skip or key not in data:
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            data[key] = value
        try:
            return IdProofModel(**data)
        except Exception as exc:
            logger.warning("merge_with_extraction validation failed, keeping OCR: %s", exc)
            return extraction

    def build_enhanced_identity_json(
        self,
        merged_id_proof: IdProofExtraction,
        diagnosis: DiagnosisReportExtraction | None,
        referral: ReferralExtraction | None,
        source: IdentitySource,
        *,
        documents_verified: bool = True,
    ) -> dict[str, Any]:
        """Target shape from master prompt §1b."""
        diagnosis_text: str | None = None
        if diagnosis:
            primary = next((d for d in diagnosis.diagnoses if d.is_primary), None)
            diagnosis_text = (
                primary.text
                if primary
                else diagnosis.primary_diagnosis_text
            )
        doctor_name = referral.referring_doctor_name if referral else None
        return {
            "patient_name": merged_id_proof.patient_name,
            "abha_id": merged_id_proof.abha_id,
            "diagnosis": diagnosis_text,
            "doctor_name": doctor_name,
            "documents_verified": documents_verified,
            "source": source,
        }
