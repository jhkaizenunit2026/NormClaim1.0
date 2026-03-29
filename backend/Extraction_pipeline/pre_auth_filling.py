"""
pre_auth_filling.py — NormClaim Pre-Auth Form Auto-Filler
==========================================================
Reads extraction results from ai_extraction_records and fills
the pre_auth_forms table in Supabase.

Enforces all NormClaim business rules:
  - Identity fields: prefer ABHA-verified data over extracted data
  - Clinical fields: sourced exclusively from diagnosis extraction
  - Referral fields: sourced exclusively from referral extraction
  - field_requirements_meta JSONB is updated per fill (never hardcoded)
  - auto_fill_snapshot_json captures the full audit trail
  - form_status transitions: draft → auto_filled or pending_manual
  - Every write is logged to audit_logs

Python 3.11 required.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field

from .extraction_pipeline import (
    CONFIDENCE_THRESHOLD,
    CombinedExtraction,
    DiagnosisReportExtraction,
    ExtractionPipeline,
    IdProofExtraction,
    ReferralExtraction,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# FIELD REQUIREMENT META BUILDER
# ─────────────────────────────────────────────────────────────────────────────

# NormClaim rule: field_requirements_meta JSONB drives the form renderer.
# mandatory/optional status is DATA, not code — never hardcode in UI.
BASE_FIELD_REQUIREMENTS: dict[str, str] = {
    # mandatory fields
    "id_proof_type":          "mandatory",
    "id_proof_number":        "mandatory",
    "primary_diagnosis_text": "mandatory",
    "primary_icd10_code":     "mandatory",
    "referring_doctor_name":  "mandatory",
    "policy_id":              "mandatory",
    # optional fields
    "referring_doctor_reg":   "optional",
    "referral_notes":         "optional",
    "planned_procedure":      "optional",
    "estimated_los_days":     "optional",
    "secondary_diagnoses":    "optional",
    "requested_amount_inr":   "optional",
}


def build_field_requirements_meta(filled_fields: set[str]) -> dict[str, dict]:
    """
    Build field_requirements_meta JSONB.
    Format: {field_name: {requirement: mandatory|optional, filled: true|false}}
    """
    return {
        field: {
            "requirement": requirement,
            "filled": field in filled_fields,
        }
        for field, requirement in BASE_FIELD_REQUIREMENTS.items()
    }


def all_mandatory_filled(meta: dict[str, dict]) -> bool:
    mandatory_values = [
        v
        for v in (meta or {}).values()
        if isinstance(v, dict) and v.get("requirement") == "mandatory"
    ]
    if not mandatory_values:
        return False
    return all(bool(v.get("filled")) for v in mandatory_values)


# ─────────────────────────────────────────────────────────────────────────────
# FIELD MAPPER
# ─────────────────────────────────────────────────────────────────────────────

class FieldMapping(BaseModel):
    """Represents one pre_auth_forms field ready to write."""
    field_name: str
    value: Any
    confidence: float
    source: str  # 'id_proof' | 'diagnosis_report' | 'referral' | 'abha' | 'hospital_db'
    should_write: bool  # False when confidence < threshold or ABHA conflict


class PreAuthFieldMapper:
    """
    Maps CombinedExtraction → pre_auth_forms field values.

    Priority rules (NormClaim business rules):
      1. Identity fields: ABHA-verified patient data takes precedence.
         If extraction disagrees with ABHA record by more than edit-distance
         threshold, flag but DO NOT overwrite verified data.
      2. Clinical fields: diagnosis extraction only.
      3. Referral fields: referral extraction only.
      4. Only write fields with confidence >= CONFIDENCE_THRESHOLD.
    """

    ABHA_NAME_SIMILARITY_THRESHOLD = 0.75  # Levenshtein ratio threshold

    def __init__(
        self,
        combined: CombinedExtraction,
        patient_row: dict,
        policy_row: dict | None,
    ):
        self.combined = combined
        self.patient = patient_row
        self.policy = policy_row
        self.id_proof = combined.id_proof
        self.diag = combined.diagnosis_report
        self.referral = combined.referral

    def _name_matches_abha(self, extracted_name: str | None) -> bool:
        """Check if extracted name is close enough to ABHA-verified name."""
        if not extracted_name:
            return True  # Nothing extracted, no conflict
        abha_name = self.patient.get("patient_name", "")
        if not abha_name:
            return True
        ratio = SequenceMatcher(
            None,
            extracted_name.lower().strip(),
            abha_name.lower().strip()
        ).ratio()
        return ratio >= self.ABHA_NAME_SIMILARITY_THRESHOLD

    def _id_proof_fields(self) -> list[FieldMapping]:
        """Map ID proof extraction to pre_auth_forms fields."""
        mappings: list[FieldMapping] = []
        if not self.id_proof:
            return mappings

        is_abha_verified = self.patient.get("abha_verified", False)

        # id_proof_type
        if self.id_proof.id_proof_type:
            mappings.append(FieldMapping(
                field_name="id_proof_type",
                value=self.id_proof.id_proof_type.value,
                confidence=self.id_proof.confidence,
                source="id_proof",
                should_write=self.id_proof.confidence >= CONFIDENCE_THRESHOLD,
            ))

        # id_proof_number
        if self.id_proof.id_proof_number:
            mappings.append(FieldMapping(
                field_name="id_proof_number",
                value=self.id_proof.id_proof_number,
                confidence=self.id_proof.confidence,
                source="id_proof",
                should_write=self.id_proof.confidence >= CONFIDENCE_THRESHOLD,
            ))

        # Patient name cross-validation with ABHA
        if self.id_proof.patient_name and is_abha_verified:
            name_ok = self._name_matches_abha(self.id_proof.patient_name)
            if not name_ok:
                logger.warning(
                    "Extracted name '%s' conflicts with ABHA name '%s'. "
                    "Keeping ABHA data.",
                    self.id_proof.patient_name,
                    self.patient.get("patient_name"),
                )

        return mappings

    def _diagnosis_fields(self) -> list[FieldMapping]:
        """Map diagnosis report extraction to pre_auth_forms fields."""
        mappings: list[FieldMapping] = []
        if not self.diag:
            return mappings

        conf = self.diag.overall_confidence
        ok = conf >= CONFIDENCE_THRESHOLD

        if self.diag.primary_diagnosis_text:
            mappings.append(FieldMapping(
                field_name="primary_diagnosis_text",
                value=self.diag.primary_diagnosis_text,
                confidence=conf,
                source="diagnosis_report",
                should_write=ok,
            ))

        if self.diag.primary_icd10_code:
            mappings.append(FieldMapping(
                field_name="primary_icd10_code",
                value=self.diag.primary_icd10_code,
                confidence=conf,
                source="diagnosis_report",
                should_write=ok,
            ))
            mappings.append(FieldMapping(
                field_name="primary_icd10_system",
                value="http://hl7.org/fhir/sid/icd-10",
                confidence=1.0,
                source="diagnosis_report",
                should_write=True,
            ))

        if self.diag.secondary_diagnoses:
            mappings.append(FieldMapping(
                field_name="secondary_diagnoses",
                value=self.diag.secondary_diagnoses,
                confidence=conf,
                source="diagnosis_report",
                should_write=ok,
            ))

        if self.diag.planned_procedure:
            mappings.append(FieldMapping(
                field_name="planned_procedure",
                value=self.diag.planned_procedure,
                confidence=conf,
                source="diagnosis_report",
                should_write=ok,
            ))

        if self.diag.estimated_los_days is not None:
            mappings.append(FieldMapping(
                field_name="estimated_los_days",
                value=self.diag.estimated_los_days,
                confidence=conf,
                source="diagnosis_report",
                should_write=ok,
            ))

        return mappings

    def _referral_fields(self) -> list[FieldMapping]:
        """Map referral extraction to pre_auth_forms fields."""
        mappings: list[FieldMapping] = []
        if not self.referral:
            return mappings

        conf = self.referral.confidence
        ok = conf >= CONFIDENCE_THRESHOLD

        if self.referral.referring_doctor_name:
            mappings.append(FieldMapping(
                field_name="referring_doctor_name",
                value=self.referral.referring_doctor_name,
                confidence=conf,
                source="referral",
                should_write=ok,
            ))

        if self.referral.referring_doctor_reg:
            mappings.append(FieldMapping(
                field_name="referring_doctor_reg",
                value=self.referral.referring_doctor_reg,
                confidence=conf,
                source="referral",
                should_write=ok,
            ))

        if self.referral.referral_notes:
            mappings.append(FieldMapping(
                field_name="referral_notes",
                value=self.referral.referral_notes,
                confidence=conf,
                source="referral",
                should_write=ok,
            ))

        if self.referral.requested_amount_inr is not None:
            mappings.append(FieldMapping(
                field_name="requested_amount_inr",
                value=str(self.referral.requested_amount_inr),
                confidence=conf,
                source="referral",
                should_write=ok,
            ))

        return mappings

    def get_all_mappings(self) -> list[FieldMapping]:
        """Return all field mappings across all document types."""
        return (
            self._id_proof_fields()
            + self._diagnosis_fields()
            + self._referral_fields()
        )


# ─────────────────────────────────────────────────────────────────────────────
# PRE-AUTH FILLER
# ─────────────────────────────────────────────────────────────────────────────

class PreAuthFiller:
    """
    Reads ai_extraction_records data and fills pre_auth_forms in Supabase.

    The core write method:
      1. Pull ai_extraction_records row by ID
      2. Reconstruct CombinedExtraction from stored JSONB
      3. Map fields using PreAuthFieldMapper
      4. Update pre_auth_forms with auto-filled values
      5. Update field_requirements_meta JSONB
      6. Set form_status (auto_filled or pending_manual)
      7. Log to audit_logs

    Usage:
        filler = PreAuthFiller(supabase_client)
        result = filler.fill(pre_auth_form_id, ai_extraction_id, user_id)
    """

    def __init__(self, supabase: Any):
        self.db = supabase

    # ── FETCH HELPERS ─────────────────────────────────────────────────────────

    def _fetch_pre_auth_form(self, pre_auth_form_id: str) -> dict:
        resp = (
            self.db.table("pre_auth_forms")
            .select("*")
            .eq("id", pre_auth_form_id)
            .single()
            .execute()
        )
        if not resp.data:
            raise ValueError(f"pre_auth_form {pre_auth_form_id} not found")
        return resp.data

    def _fetch_ai_extraction(self, ai_extraction_id: str) -> dict:
        resp = (
            self.db.table("ai_extraction_records")
            .select("*")
            .eq("id", ai_extraction_id)
            .single()
            .execute()
        )
        if not resp.data:
            raise ValueError(f"ai_extraction_records {ai_extraction_id} not found")
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

    def _fetch_policy(self, patient_id: str) -> dict | None:
        resp = (
            self.db.table("insurance_policies")
            .select("id, policy_number, insurer_name, tpa_name, sum_insured_inr")
            .eq("patient_id", patient_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    # ── RECONSTRUCT EXTRACTION FROM DB ────────────────────────────────────────

    def _reconstruction_from_db(
        self, extraction_row: dict
    ) -> CombinedExtraction:
        """
        Reconstruct CombinedExtraction Pydantic model from JSONB stored in
        ai_extraction_records. This avoids re-running AI extraction.

        NormClaim rule: ai_extraction_records is created once;
        discharge_summary_json and FHIR bundle reference it — no re-extraction.
        """
        from .extraction_pipeline import (
            DiagnosisItem,
            MedicationItem,
            ProcedureItem,
            Script,
        )

        diagnoses_raw = extraction_row.get("diagnoses") or []
        medications_raw = extraction_row.get("medications") or []
        procedures_raw = extraction_row.get("procedures") or []
        patient_snapshot = extraction_row.get("patient_snapshot") or {}
        encounter_snapshot = extraction_row.get("encounter_snapshot") or {}

        diag_items = [DiagnosisItem(**d) for d in diagnoses_raw]
        med_items = [MedicationItem(**m) for m in medications_raw]
        proc_items = [ProcedureItem(**p) for p in procedures_raw]

        if not diag_items:
            logger.warning(
                "ai_extraction %s has no diagnosis items — "
                "primary_diagnosis_text will not be auto-filled",
                extraction_row.get("id"),
            )

        # Identify primary diagnosis
        primary = next((d for d in diag_items if d.is_primary), None)

        diag_extraction = DiagnosisReportExtraction(
            diagnoses=diag_items,
            medications=med_items,
            procedures=proc_items,
            primary_diagnosis_text=primary.text if primary else None,
            primary_icd10_code=primary.icd10_code if primary else None,
            secondary_diagnoses=[
                {"text": d.text, "icd10_code": d.icd10_code}
                for d in diag_items
                if not d.is_primary and not d.negated
            ],
            overall_confidence=extraction_row.get("confidence_score", 0.0),
        ) if diag_items else None

        id_proof_extraction: IdProofExtraction | None = None
        id_proof_raw = patient_snapshot.get("id_proof_extraction")
        if isinstance(id_proof_raw, dict):
            try:
                id_proof_extraction = IdProofExtraction(**id_proof_raw)
            except Exception as exc:
                logger.warning("Failed to reconstruct id_proof_extraction: %s", exc)

        if id_proof_extraction is None:
            fallback_id_proof = {
                "patient_name": patient_snapshot.get("name"),
                "gender": patient_snapshot.get("sex"),
                "abha_id": patient_snapshot.get("abha_id"),
                "confidence": float(extraction_row.get("confidence_score") or 0.0),
            }
            if fallback_id_proof["patient_name"] or fallback_id_proof["abha_id"]:
                try:
                    id_proof_extraction = IdProofExtraction(**fallback_id_proof)
                except Exception as exc:
                    logger.warning("Failed to build fallback id_proof_extraction: %s", exc)

        referral_extraction: ReferralExtraction | None = None
        referral_raw = encounter_snapshot.get("referral_extraction")
        if isinstance(referral_raw, dict):
            try:
                referral_extraction = ReferralExtraction(**referral_raw)
            except Exception as exc:
                logger.warning("Failed to reconstruct referral_extraction: %s", exc)

        detected_script_val = extraction_row.get("detected_script", "English")
        try:
            detected_script = Script(detected_script_val)
        except ValueError:
            detected_script = Script.ENGLISH

        return CombinedExtraction(
            id_proof=id_proof_extraction,
            diagnosis_report=diag_extraction,
            referral=referral_extraction,
            detected_script=detected_script,
            section_map=extraction_row.get("section_map") or {},
            negated_spans=extraction_row.get("negated_spans") or [],
            low_confidence_flags=extraction_row.get("low_confidence_flags") or [],
            overall_confidence=extraction_row.get("confidence_score", 0.0),
        )

    # ── SUPPLEMENTARY: FILL ID PROOF FROM PATIENTS TABLE ─────────────────────

    def _id_proof_from_patient(
        self, patient: dict, form: dict
    ) -> list[FieldMapping]:
        """
        For identity fields, use the patients table as the source of truth.
        If patients.source = 'abha' and abha_verified = True, use that.
        Otherwise use hospital_db data from patients row.
        """
        source = "abha" if patient.get("abha_verified") else "hospital_db"
        fields = []

        existing_id_type = form.get("id_proof_type")
        if existing_id_type:
            return fields

        # Only infer from explicit patient data; never default to Aadhaar.
        patient_id_type = str(patient.get("id_proof_type") or patient.get("id_type") or "").strip().lower()
        allowed_types = {"aadhaar", "pan", "passport", "voter_id"}
        inferred_id_type: str | None = None

        if patient_id_type in allowed_types:
            inferred_id_type = patient_id_type
        elif patient.get("abha_id"):
            inferred_id_type = "aadhaar"

        if inferred_id_type:
            fields.append(
                FieldMapping(
                    field_name="id_proof_type",
                    value=inferred_id_type,
                    confidence=1.0 if patient_id_type in allowed_types else 0.65,
                    source=source,
                    should_write=True,
                )
            )

        return fields

    # ── CONFIDENCE REPORT ─────────────────────────────────────────────────────

    def _build_confidence_report(
        self, mappings: list[FieldMapping], patient_id: str
    ) -> dict:
        """
        Build a JSON confidence report stored as a document_attachment.
        Used by the Streamlit reviewer UI to highlight low-confidence fields.
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "patient_id": patient_id,
            "fields": [],
        }
        for m in mappings:
            report["fields"].append({
                "field_name": m.field_name,
                "confidence": m.confidence,
                "source": m.source,
                "needs_review": not m.should_write or m.confidence < CONFIDENCE_THRESHOLD,
                "written": m.should_write,
                # value intentionally omitted from external report
            })
        return report

    def _save_confidence_report(
        self,
        report: dict,
        pre_auth_form_id: str,
        uploaded_by: str | None = None,
    ) -> None:
        """
        Save the confidence report to Supabase Storage and register it in
        document_attachments.
        """
        report_bytes = json.dumps(report, ensure_ascii=False).encode("utf-8")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        filename = f"confidence_report_{ts}.json"
        storage_bucket = "documents"
        storage_key = f"reports/{pre_auth_form_id}/{filename}"

        storage_url: str | None = None
        try:
            self.db.storage.from_(storage_bucket).upload(storage_key, report_bytes)
            try:
                public_url_result = self.db.storage.from_(storage_bucket).get_public_url(storage_key)
                if isinstance(public_url_result, str):
                    storage_url = public_url_result
                elif isinstance(public_url_result, dict):
                    storage_url = (
                        public_url_result.get("publicURL")
                        or public_url_result.get("publicUrl")
                        or (public_url_result.get("data") or {}).get("publicUrl")
                    )
            except Exception:
                storage_url = None
        except Exception as exc:
            logger.warning("Could not upload confidence report to storage: %s", exc)
            return

        if not storage_url:
            storage_url = storage_key

        row = {
            "id": str(uuid.uuid4()),
            "entity_type": "pre_auth",
            "entity_id": pre_auth_form_id,
            "doc_type": "other",
            "is_mandatory": False,
            "is_verified": False,
            "storage_url": storage_url,
            "filename": filename,
            "file_format": "json",
            "file_size_bytes": len(report_bytes),
            "uploaded_by": uploaded_by or "system",
        }
        try:
            self.db.table("document_attachments").insert(row).execute()
        except Exception as exc:
            logger.warning("Could not save confidence report attachment: %s", exc)

    # ── AUDIT LOG ─────────────────────────────────────────────────────────────

    def _audit_log(
        self,
        patient_id: str,
        action: str,
        record_id: str | None = None,
        table_affected: str = "pre_auth_forms",
        diff_snapshot: dict | None = None,
        user_id: str | None = None,
    ) -> None:
        """Append-only audit log write. Never UPDATE or DELETE."""
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "stage": "pre_auth",
            "action": action,
            "table_affected": table_affected,
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.exception("audit_log write failed")

    # ── MAIN FILL ─────────────────────────────────────────────────────────────

    def fill(
        self,
        pre_auth_form_id: str,
        ai_extraction_id: str,
        combined_extraction: CombinedExtraction | None = None,
        requesting_user_id: str | None = None,
    ) -> dict:
        """
        Fill pre_auth_forms from ai_extraction_records data.

        Args:
            pre_auth_form_id: UUID of the pre_auth_forms row to fill
            ai_extraction_id: UUID of the ai_extraction_records row to read from
            requesting_user_id: For audit log

        Returns:
            {
                "pre_auth_form_id": str,
                "form_status": str,
                "auto_filled_fields": list[str],
                "unfilled_mandatory_fields": list[str],
                "confidence_report": dict,
            }
        """
        logger.info(
            "Filling pre_auth_form %s from ai_extraction %s",
            pre_auth_form_id, ai_extraction_id
        )

        # 1. Fetch all required rows
        form = self._fetch_pre_auth_form(pre_auth_form_id)
        patient_id = form["patient_id"]
        extraction_row = self._fetch_ai_extraction(ai_extraction_id)
        patient = self._fetch_patient(patient_id)
        policy = self._fetch_policy(patient_id)

        # Capture before-state for audit diff
        before_snapshot = {
            k: form.get(k)
            for k in BASE_FIELD_REQUIREMENTS
        }

        # 2. Reconstruct CombinedExtraction from stored JSONB unless caller
        # already provided the in-memory extraction (includes id_proof/referral).
        combined = combined_extraction or self._reconstruction_from_db(extraction_row)

        # 3. Map fields
        mapper = PreAuthFieldMapper(
            combined=combined,
            patient_row=patient,
            policy_row=policy,
        )
        mappings = mapper.get_all_mappings()

        # 4. Add identity fields from patients table (ABHA priority)
        patient_identity_mappings = self._id_proof_from_patient(patient, form)
        mappings.extend(patient_identity_mappings)

        # 5. Add policy_id if active policy found
        if policy:
            mappings.append(FieldMapping(
                field_name="policy_id",
                value=policy["id"],
                confidence=1.0,
                source="insurance_policies",
                should_write=True,
            ))

        # 6. Build update payload — only write fields that pass confidence gate
        update_payload: dict[str, Any] = {}
        auto_filled_fields: list[str] = []

        for mapping in mappings:
            if mapping.should_write and mapping.value is not None:
                if mapping.field_name not in update_payload:
                    update_payload[mapping.field_name] = mapping.value
                    auto_filled_fields.append(mapping.field_name)

        # 7. Determine auto_fill_source
        auto_fill_source = (
            "abha" if patient.get("abha_verified") else "hospital_db"
        )

        # 8. Build field_requirements_meta
        filled_set = set(auto_filled_fields)
        field_requirements_meta = build_field_requirements_meta(filled_set)
        form_status = (
            "auto_filled" if all_mandatory_filled(field_requirements_meta)
            else "pending_manual"
        )

        # 9. Build auto_fill_snapshot_json (full audit trail of what was used)
        snapshot = {
            "ai_extraction_id": ai_extraction_id,
            "extraction_confidence": combined.overall_confidence,
            "source": auto_fill_source,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "field_sources": {
                m.field_name: {
                    "source": m.source,
                    "confidence": m.confidence,
                    "written": m.should_write,
                }
                for m in mappings
            },
        }

        # 10. Add metadata fields to update payload
        update_payload.update({
            "auto_filled": True,
            "auto_fill_source": auto_fill_source,
            "auto_fill_snapshot_json": snapshot,
            "auto_filled_fields": auto_filled_fields,
            "field_requirements_meta": field_requirements_meta,
            "form_status": form_status,
        })

        # 11. Write to pre_auth_forms
        self.db.table("pre_auth_forms").update(update_payload).eq(
            "id", pre_auth_form_id
        ).execute()

        logger.info(
            "pre_auth_form %s updated. status=%s filled=%d fields",
            pre_auth_form_id, form_status, len(auto_filled_fields)
        )

        # 12. Build and save confidence report
        confidence_report = self._build_confidence_report(mappings, patient_id)
        self._save_confidence_report(
            confidence_report, pre_auth_form_id, uploaded_by=requesting_user_id
        )

        # 13. Unfilled mandatory fields for response
        unfilled_mandatory = [
            field
            for field, meta in field_requirements_meta.items()
            if meta["requirement"] == "mandatory" and not meta["filled"]
        ]

        # 14. Audit log
        self._audit_log(
            patient_id=patient_id,
            action="pre_auth.auto_filled",
            record_id=pre_auth_form_id,
            diff_snapshot={
                "before": before_snapshot,
                "after": {k: update_payload.get(k) for k in before_snapshot},
                "auto_filled_fields": auto_filled_fields,
                "form_status": form_status,
                "overall_confidence": combined.overall_confidence,
            },
            user_id=requesting_user_id,
        )

        return {
            "pre_auth_form_id": pre_auth_form_id,
            "form_status": form_status,
            "auto_filled_fields": auto_filled_fields,
            "unfilled_mandatory_fields": unfilled_mandatory,
            "confidence_report": confidence_report,
        }


# ─────────────────────────────────────────────────────────────────────────────
# HUMAN CORRECTION HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class CorrectionHandler:
    """
    Handles reviewer corrections to auto-filled fields.

    Every correction:
      1. Updates pre_auth_forms field value
      2. Updates field_requirements_meta.filled = true for that field
      3. Logs correction to audit_logs
      4. Writes to preauth_corrections table (fine-tuning feedback loop)
      5. If all mandatory fields now filled, transitions form_status → submitted
    """

    def __init__(self, supabase: Any):
        self.db = supabase

    def apply_correction(
        self,
        pre_auth_form_id: str,
        field_name: str,
        corrected_value: Any,
        reviewer_user_id: str,
        original_extracted_value: Any = None,
    ) -> dict:
        """
        Apply one field correction from a human reviewer.

        Returns updated form status info.
        """
        # Fetch current form state
        resp = (
            self.db.table("pre_auth_forms")
            .select("patient_id, field_requirements_meta, form_status, auto_filled_fields")
            .eq("id", pre_auth_form_id)
            .single()
            .execute()
        )
        form = resp.data
        if not form:
            raise ValueError(f"pre_auth_form {pre_auth_form_id} not found")

        patient_id = form["patient_id"]
        meta = form.get("field_requirements_meta") or {}
        auto_filled = form.get("auto_filled_fields") or []

        # Normalize metadata before evaluating completeness so empty/malformed
        # state does not incorrectly pass mandatory checks.
        if not meta:
            meta = build_field_requirements_meta(set(auto_filled))
        else:
            normalized_meta = build_field_requirements_meta(set(auto_filled))
            for field_name_key, field_meta in meta.items():
                if isinstance(field_meta, dict):
                    if field_name_key not in normalized_meta:
                        continue  # skip unknown fields
                    normalized_meta[field_name_key]["filled"] = bool(
                        field_meta.get("filled")
                    )
            meta = normalized_meta

        # Update the specific field
        field_update: dict[str, Any] = {field_name: corrected_value}

        # Update field_requirements_meta
        if field_name in meta:
            meta[field_name]["filled"] = True
        field_update["field_requirements_meta"] = meta

        # Update auto_filled_fields list
        if field_name not in auto_filled:
            auto_filled.append(field_name)
            field_update["auto_filled_fields"] = auto_filled

        # Transition form_status if all mandatory fields now filled
        new_status = form["form_status"]
        if all_mandatory_filled(meta) and form["form_status"] == "pending_manual":
            new_status = "auto_filled"
            field_update["form_status"] = new_status

        self.db.table("pre_auth_forms").update(field_update).eq(
            "id", pre_auth_form_id
        ).execute()

        # Log to audit_logs
        audit_row = {
            "id": str(uuid.uuid4()),
            "user_id": reviewer_user_id,
            "patient_id": patient_id,
            "stage": "pre_auth",
            "action": "pre_auth.field_corrected",
            "table_affected": "pre_auth_forms",
            "record_id": pre_auth_form_id,
            "diff_snapshot": {
                "field": field_name,
                "before": original_extracted_value,
                "after": corrected_value,
                "reviewer": reviewer_user_id,
            },
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.table("audit_logs").insert(audit_row).execute()

        # Write to preauth_corrections for fine-tuning feedback loop
        try:
            correction_row = {
                "id": str(uuid.uuid4()),
                "pre_auth_form_id": pre_auth_form_id,
                "field_name": field_name,
                "original_value": str(original_extracted_value) if original_extracted_value else None,
                "corrected_value": str(corrected_value),
                "reviewer_user_id": reviewer_user_id,
                "corrected_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.table("preauth_corrections").insert(correction_row).execute()
        except Exception as exc:
            logger.warning(
                "preauth_corrections write failed (table may not exist yet): %s", exc
            )

        logger.info(
            "Correction applied: pre_auth=%s field=%s status=%s",
            pre_auth_form_id, field_name, new_status
        )

        return {
            "pre_auth_form_id": pre_auth_form_id,
            "field_name": field_name,
            "new_status": new_status,
            "all_mandatory_filled": all_mandatory_filled(meta),
        }


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR — ties extraction + filling together in one call
# ─────────────────────────────────────────────────────────────────────────────

class PreAuthOrchestrator:
    """
    Single entry point for the complete pre-auth auto-fill workflow.

    Calls ExtractionPipeline then PreAuthFiller in sequence.
    Use this from the FastAPI endpoint.

    Usage:
        orchestrator = PreAuthOrchestrator(supabase, google_api_key)
        result = orchestrator.process(pre_auth_form_id, user_id)
    """

    def __init__(self, supabase: Any, google_api_key: str):
        self.extraction_pipeline = ExtractionPipeline(supabase, google_api_key)
        self.filler = PreAuthFiller(supabase)
        self.correction_handler = CorrectionHandler(supabase)

    def process(
        self,
        pre_auth_form_id: str,
        requesting_user_id: str | None = None,
    ) -> dict:
        """
        Full pipeline: extract from documents → fill pre_auth_forms.

        Returns:
            {
                "ai_extraction_id": str,
                "pre_auth_form_id": str,
                "form_status": str,               # auto_filled | pending_manual
                "auto_filled_fields": list[str],
                "unfilled_mandatory_fields": list[str],
                "overall_confidence": float,
                "low_confidence_flags": list[str],
                "confidence_report": dict,
            }
        """
        # Step 1: Run extraction pipeline
        extraction_result = self.extraction_pipeline.run(
            pre_auth_form_id=pre_auth_form_id,
            requesting_user_id=requesting_user_id,
        )

        ai_extraction_id = extraction_result["ai_extraction_id"]

        # Step 2: Fill the form from extraction results
        fill_result = self.filler.fill(
            pre_auth_form_id=pre_auth_form_id,
            ai_extraction_id=ai_extraction_id,
            combined_extraction=extraction_result["combined_extraction"],
            requesting_user_id=requesting_user_id,
        )

        return {
            "ai_extraction_id": ai_extraction_id,
            "pre_auth_form_id": pre_auth_form_id,
            "form_status": fill_result["form_status"],
            "auto_filled_fields": fill_result["auto_filled_fields"],
            "unfilled_mandatory_fields": fill_result["unfilled_mandatory_fields"],
            "overall_confidence": extraction_result["overall_confidence"],
            "low_confidence_flags": extraction_result["low_confidence_flags"],
            "confidence_report": fill_result["confidence_report"],
        }
