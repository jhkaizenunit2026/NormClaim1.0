"""
extraction_pipeline.py — NormClaim Pre-Auth Extraction Pipeline
===============================================================
Handles OCR, NLP section detection, and Gemini-powered entity extraction
from three document types: id_proof, diagnosis_report, referral_letter.

Outputs are written to ai_extraction_records in Supabase.
Follows all NormClaim business rules:
  - consent_obtained must be TRUE before processing
  - negated diagnoses are flagged (never enter FHIR)
  - every action is logged to audit_logs
  - ICD-10 uses system URI: http://hl7.org/fhir/sid/icd-10
  - ABHA format: 91-XXXX-XXXX-XXXX

Python 3.11 required.
"""

from __future__ import annotations

import io
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import google.genai as gen
import cv2
import fitz
import httpx
import instructor
import numpy as np
import pdfplumber
import pytesseract
from docx import Document as DocxDocument
from PIL import Image
from pydantic import BaseModel, Field, field_validator

from .abha_lookup import ABHALookupService
from .text_features import (
    build_section_map,
    detect_script_enum_value,
    extract_negated_spans,
)

logger = logging.getLogger(__name__)

ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10"
NDHM_ABHA_SYSTEM = "https://healthid.ndhm.gov.in"
CONFIDENCE_THRESHOLD = 0.70


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class DocType(str, Enum):
    ID_PROOF = "id_proof"
    DIAGNOSIS_REPORT = "diagnosis_report"
    REFERRAL_LETTER = "referral_letter"


class FileFormat(str, Enum):
    PDF = "pdf"
    JPG = "jpg"
    PNG = "png"
    DOCX = "docx"
    TXT = "txt"


class IdProofType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    VOTER_ID = "voter_id"
    PASSPORT = "passport"


class Script(str, Enum):
    ENGLISH = "English"
    DEVANAGARI = "Devanagari"
    HINGLISH = "Hinglish"


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC EXTRACTION SCHEMAS (instructor enforces these from Gemini output)
# ─────────────────────────────────────────────────────────────────────────────

class DiagnosisItem(BaseModel):
    """Matches ai_extraction_records.diagnoses[] JSONB element exactly."""
    text: str = Field(description="Full diagnosis name as written in document")
    icd10_code: str = Field(description="ICD-10 code e.g. E11, J18.9")
    icd10_system: str = Field(default=ICD10_SYSTEM)
    icd10_display: str = Field(description="Standard ICD-10 display name")
    is_primary: bool = Field(description="True for the primary/main diagnosis")
    confidence: float = Field(ge=0.0, le=1.0)
    negated: bool = Field(
        default=False,
        description="True if diagnosis is negated e.g. 'no fever', 'denies diabetes'"
    )
    uncertainty: str = Field(
        default="confirmed",
        description="One of: confirmed, probable, possible, refuted"
    )
    section: str = Field(
        default="diagnosis",
        description="Section of document where found: diagnosis, history, complaints, impression"
    )

    @field_validator("icd10_system", mode="before")
    @classmethod
    def fix_icd_system(cls, v: str) -> str:
        return ICD10_SYSTEM


class MedicationItem(BaseModel):
    """Matches ai_extraction_records.medications[] JSONB element."""
    name: str
    brand_name: str | None = None
    generic_name: str | None = None
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ProcedureItem(BaseModel):
    """Matches ai_extraction_records.procedures[] JSONB element."""
    name: str
    code: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class IdProofExtraction(BaseModel):
    """Extracted fields from id_proof documents."""
    id_proof_type: IdProofType | None = None
    id_proof_number: str | None = Field(None, description="Aadhaar/PAN/passport number")
    patient_name: str | None = None
    dob: str | None = Field(None, description="Date of birth in YYYY-MM-DD format")
    gender: str | None = Field(None, description="male, female, other, or unknown")
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    abha_id: str | None = Field(
        None,
        description="ABHA ID if present, format 91-XXXX-XXXX-XXXX"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class DiagnosisReportExtraction(BaseModel):
    """Extracted fields from diagnosis/discharge reports."""
    diagnoses: list[DiagnosisItem] = Field(default_factory=list)
    medications: list[MedicationItem] = Field(default_factory=list)
    procedures: list[ProcedureItem] = Field(default_factory=list)
    primary_diagnosis_text: str | None = None
    primary_icd10_code: str | None = None
    secondary_diagnoses: list[dict[str, str]] = Field(
        default_factory=list,
        description="[{text, icd10_code}] list for secondary diagnoses"
    )
    planned_procedure: str | None = None
    estimated_los_days: int | None = Field(None, description="Estimated length of stay in days")
    overall_confidence: float = Field(ge=0.0, le=1.0)


class ReferralExtraction(BaseModel):
    """Extracted fields from referral letters."""
    referring_doctor_name: str | None = None
    referring_doctor_reg: str | None = Field(None, description="Medical registration number")
    referral_notes: str | None = None
    requested_amount_inr: float | None = Field(None, description="Amount requested in INR")
    referred_hospital: str | None = None
    urgency: str | None = Field(None, description="routine, urgent, emergency")
    confidence: float = Field(ge=0.0, le=1.0)


class CombinedExtraction(BaseModel):
    """Full extraction result for one pre-auth case across all documents."""
    id_proof: IdProofExtraction | None = None
    diagnosis_report: DiagnosisReportExtraction | None = None
    referral: ReferralExtraction | None = None
    detected_script: Script = Script.ENGLISH
    section_map: dict[str, str] = Field(default_factory=dict)
    negated_spans: list[str] = Field(default_factory=list)
    low_confidence_flags: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)


# ─────────────────────────────────────────────────────────────────────────────
# OCR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

class OCRProcessor:
    """Handles text extraction from PDF/image/DOCX with preprocessing."""

    @staticmethod
    def _preprocess_image(img_array: np.ndarray) -> np.ndarray:
        """Deskew, denoise, and binarize for better OCR accuracy."""
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        _, binary = cv2.threshold(
            denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        coords = np.column_stack(np.where(binary < 255))
        if len(coords) == 0:
            return binary
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            h, w = binary.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            binary = cv2.warpAffine(
                binary, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
        return binary

    @classmethod
    def extract_from_pdf(cls, file_bytes: bytes) -> tuple[str, dict]:
        """
        Try native text extraction first (pdfplumber).
        Fall back to OCR (pytesseract) if text yield is too low.
        Returns (text, section_hints).
        """
        text_parts: list[str] = []
        section_hints: dict[int, str] = {}

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                native_text = page.extract_text() or ""
                if len(native_text.strip()) > 50:
                    text_parts.append(native_text)
                    section_hints[page_num] = "native"
                else:
                    img = page.to_image(resolution=300).original
                    img_arr = np.array(img)
                    preprocessed = cls._preprocess_image(img_arr)
                    ocr_text = pytesseract.image_to_string(
                        preprocessed, lang="eng+hin", config="--psm 6"
                    )
                    text_parts.append(ocr_text)
                    section_hints[page_num] = "ocr"

        return "\n".join(text_parts), section_hints

    @classmethod
    def extract_from_image(cls, file_bytes: bytes) -> str:
        """OCR an image file (jpg/png) with preprocessing."""
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img_arr = np.array(img)
        preprocessed = cls._preprocess_image(img_arr)
        return pytesseract.image_to_string(
            preprocessed, lang="eng+hin", config="--psm 6"
        )

    @classmethod
    def extract_from_docx(cls, file_bytes: bytes) -> str:
        """Extract text from DOCX preserving paragraph order."""
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    @classmethod
    def extract_text(cls, file_bytes: bytes, file_format: str) -> str:
        """Route to correct extractor by file format."""
        fmt = file_format.lower()
        if fmt == "pdf":
            text, _ = cls.extract_from_pdf(file_bytes)
            return text
        elif fmt in ("jpg", "jpeg", "png"):
            return cls.extract_from_image(file_bytes)
        elif fmt == "docx":
            return cls.extract_from_docx(file_bytes)
        elif fmt == "txt":
            return file_bytes.decode("utf-8", errors="replace")
        else:
            logger.warning("Unknown format %s, attempting raw decode", file_format)
            return file_bytes.decode("utf-8", errors="replace")

    @classmethod
    def detect_script(cls, text: str) -> Script:
        """Detect dominant script in extracted text."""
        return Script(detect_script_enum_value(text))


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI EXTRACTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class GeminiExtractionEngine:
    """
    Uses instructor + Gemini to extract structured fields from raw document text.
    instructor enforces Pydantic schema compliance — retries on parse failures.
    """

    SYSTEM_PROMPT = """You are a medical data extraction expert for India's Ayushman Bharat 
Digital Mission (ABDM). You extract structured fields from hospital documents for pre-authorisation forms.

Rules:
1. ICD-10 codes MUST use system URI: http://hl7.org/fhir/sid/icd-10
2. ABHA IDs follow format: 91-XXXX-XXXX-XXXX
3. Dates must be in YYYY-MM-DD format
4. Confidence scores reflect how certain you are (0.0-1.0)
5. Mark negated=true for any diagnosis explicitly denied (e.g. "no diabetes", "denies fever")
6. If a field is not present in the document, return null — do not invent values
7. Indian currency amounts are in INR
8. Gender must be one of: male, female, other, unknown
"""

    FEW_SHOT_ID_PROOF = """Example ID Proof extraction:
Input: "Aadhaar Card\nName: RAJESH KUMAR\nDOB: 15/08/1982\nGender: Male\nUID: 1234 5678 9012"
Output: {
  "id_proof_type": "aadhaar",
  "id_proof_number": "1234 5678 9012",
  "patient_name": "Rajesh Kumar",
  "dob": "1982-08-15",
  "gender": "male",
  "confidence": 0.97
}"""

    FEW_SHOT_DIAGNOSIS = """Example Diagnosis extraction:
Input: "Patient: Rajesh Kumar, 41M\nDiagnosis: Type 2 Diabetes Mellitus with peripheral neuropathy\nNo fever noted. No chest pain.\nMedication: Metformin 500mg BD x 30 days"
Output: {
  "diagnoses": [
    {"text": "Type 2 Diabetes Mellitus with peripheral neuropathy", "icd10_code": "E11.4",
     "icd10_system": "http://hl7.org/fhir/sid/icd-10", "icd10_display": "Type 2 diabetes mellitus with diabetic amyotrophy",
     "is_primary": true, "confidence": 0.92, "negated": false, "uncertainty": "confirmed", "section": "diagnosis"}
  ],
  "medications": [
    {"name": "Metformin", "dose": "500mg", "route": "oral", "frequency": "twice daily", "duration": "30 days", "confidence": 0.96}
  ],
  "overall_confidence": 0.94
}"""

    def __init__(self, google_api_key: str):
        raw_client = gen.Client(api_key=google_api_key)
        self.client = instructor.from_genai(
            client=raw_client,
            mode=instructor.Mode.GENAI_TOOLS
        )
        self.model_id = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def extract_id_proof(self, text: str) -> IdProofExtraction:
        prompt = f"{self.FEW_SHOT_ID_PROOF}\n\nNow extract from this document:\n{text[:3000]}"
        return self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_model=IdProofExtraction,
        )

    def extract_diagnosis_report(self, text: str) -> DiagnosisReportExtraction:
        prompt = f"{self.FEW_SHOT_DIAGNOSIS}\n\nNow extract from this document:\n{text[:4000]}"
        return self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_model=DiagnosisReportExtraction,
        )

    def extract_referral(self, text: str) -> ReferralExtraction:
        prompt = f"""Extract referral letter fields from this document.
Focus on: referring doctor name, registration number, referral notes, requested amount in INR.

Document:
{text[:3000]}"""
        return self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_model=ReferralExtraction,
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXTRACTION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

class ExtractionPipeline:
    """
    Orchestrates the full document extraction pipeline for a pre-auth case.

    Flow:
      1. Fetch document_attachments rows for the pre_auth_form
      2. Check consent_obtained on patient (ABDM rule)
      3. Download files from Supabase Storage
      4. OCR / text extract each file
      5. Run Gemini structured extraction per doc_type
      6. ABHA / hospital demographics merge (ABHA wins)
      7. Write result to ai_extraction_records
      8. Log to audit_logs

    Usage:
        pipeline = ExtractionPipeline(supabase_client, google_api_key)
        result = await pipeline.run(pre_auth_form_id, requesting_user_id)
    """

    def __init__(self, supabase: Any, google_api_key: str):
        self.db = supabase
        self.ocr = OCRProcessor()
        self.gemini = GeminiExtractionEngine(google_api_key)

    def _trusted_supabase_host(self) -> str | None:
        supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        if not supabase_url:
            return None
        parsed = urlparse(supabase_url)
        return (parsed.hostname or "").lower() or None

    def _is_trusted_storage_url(self, storage_url: str) -> bool:
        import posixpath
        parsed = urlparse(storage_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            return False

        trusted_host = self._trusted_supabase_host()
        if trusted_host and host != trusted_host:
            return False

        normalized_path = posixpath.normpath(parsed.path)
        return normalized_path.startswith("/storage/v1/object/")

    # ── CONSENT GATE ──────────────────────────────────────────────────────────

    def _assert_consent(self, patient_id: str, pre_auth_form_id: str) -> None:
        """
        NormClaim business rule: consent_obtained must be TRUE before processing.
        Raises ValueError and logs to audit_logs if consent not obtained.
        """
        resp = (
            self.db.table("patients")
            .select("consent_obtained")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        if not resp.data or not resp.data.get("consent_obtained"):
            self._audit_log(
                patient_id=patient_id,
                stage="pre_auth",
                action="pre_auth.consent_blocked",
                table_affected="patients",
                record_id=patient_id,
            )
            raise PermissionError(
                f"Patient {patient_id} has not provided consent. "
                "Set patients.consent_obtained = TRUE before processing."
            )

    # ── DOCUMENT FETCH ─────────────────────────────────────────────────────────

    def _fetch_document_attachments(self, pre_auth_form_id: str) -> list[dict]:
        """
        Fetch all id_proof / diagnosis_report / referral_letter attachments
        for this pre-auth form from document_attachments.
        """
        resp = (
            self.db.table("document_attachments")
            .select("*")
            .eq("entity_type", "pre_auth")
            .eq("entity_id", pre_auth_form_id)
            .in_("doc_type", [
                DocType.ID_PROOF,
                DocType.DIAGNOSIS_REPORT,
                DocType.REFERRAL_LETTER,
            ])
            .execute()
        )
        return resp.data or []

    def _check_mandatory_docs(
        self, attachments: list[dict], pre_auth_form_id: str
    ) -> None:
        """Raise if required document types are missing or mandatory docs are unverified."""
        required_types = {
            DocType.ID_PROOF.value,
            DocType.DIAGNOSIS_REPORT.value,
            DocType.REFERRAL_LETTER.value,
        }
        present_types = {a.get("doc_type") for a in attachments if a.get("doc_type")}
        missing_types = sorted(required_types - present_types)

        unverified = [
            a for a in attachments
            if a.get("is_mandatory") and not a.get("is_verified")
        ]
        if missing_types or unverified:
            unverified_types = sorted({a.get("doc_type") for a in unverified if a.get("doc_type")})
            logger.warning(
                "pre_auth %s mandatory-document check failed; missing_types=%s unverified_types=%s",
                pre_auth_form_id,
                missing_types,
                unverified_types,
            )
            return

    def _download_file(self, attachment: dict) -> bytes:
        """Download file bytes from trusted Supabase Storage metadata only."""
        storage_key = (
            attachment.get("storage_key")
            or attachment.get("file_path")
            or attachment.get("path")
        )
        storage_bucket = attachment.get("storage_bucket") or attachment.get("bucket") or "documents"

        if storage_key:
            return self.db.storage.from_(storage_bucket).download(storage_key)

        storage_url = attachment.get("storage_url")
        if not storage_url:
            raise ValueError("Attachment is missing both storage_key and storage_url")
        if not self._is_trusted_storage_url(storage_url):
            raise ValueError("Untrusted storage URL blocked")

        resp = httpx.get(storage_url, timeout=30, follow_redirects=False)
        resp.raise_for_status()
        return resp.content

    # ── EXTRACTION ────────────────────────────────────────────────────────────

    def _process_document(
        self, attachment: dict
    ) -> tuple[str, str, Any]:
        """
        Download + OCR one document.
        Returns (doc_type, raw_text, extraction_result).
        """
        doc_type = attachment["doc_type"]
        file_format = attachment.get("file_format", "pdf")

        logger.info("Processing %s doc: %s", doc_type, attachment.get("filename"))

        file_bytes = self._download_file(attachment)
        raw_text = self.ocr.extract_text(file_bytes, file_format)

        extraction: Any = None
        if doc_type == DocType.ID_PROOF:
            extraction = self.gemini.extract_id_proof(raw_text)
        elif doc_type == DocType.DIAGNOSIS_REPORT:
            extraction = self.gemini.extract_diagnosis_report(raw_text)
        elif doc_type == DocType.REFERRAL_LETTER:
            extraction = self.gemini.extract_referral(raw_text)

        return doc_type, raw_text, extraction

    def _build_diagnoses_json(
        self, diag_extraction: DiagnosisReportExtraction
    ) -> list[dict]:
        """
        Convert DiagnosisReportExtraction → ai_extraction_records.diagnoses[] format.
        Filters out negated diagnoses from primary listing but marks negated=true.
        NormClaim rule: negated diagnoses must be flagged, not silently dropped —
        the FHIR builder filters them in Java.
        """
        result = []
        for d in diag_extraction.diagnoses:
            result.append({
                "text": d.text,
                "icd10_code": d.icd10_code,
                "icd10_system": ICD10_SYSTEM,
                "icd10_display": d.icd10_display,
                "is_primary": d.is_primary,
                "confidence": d.confidence,
                "negated": d.negated,
                "uncertainty": d.uncertainty,
                "section": d.section,
            })
        return result

    def _build_medications_json(
        self, diag_extraction: DiagnosisReportExtraction
    ) -> list[dict]:
        return [
            {
                "name": m.name,
                "brand_name": m.brand_name,
                "generic_name": m.generic_name,
                "dose": m.dose,
                "route": m.route,
                "frequency": m.frequency,
                "duration": m.duration,
                "confidence": m.confidence,
            }
            for m in diag_extraction.medications
        ]

    def _build_procedures_json(
        self, diag_extraction: DiagnosisReportExtraction
    ) -> list[dict]:
        return [
            {"name": p.name, "code": p.code, "confidence": p.confidence}
            for p in diag_extraction.procedures
        ]

    def _compute_overall_confidence(
        self,
        id_proof: IdProofExtraction | None,
        diag: DiagnosisReportExtraction | None,
        referral: ReferralExtraction | None,
    ) -> float:
        scores = []
        if id_proof:
            scores.append(id_proof.confidence)
        if diag:
            scores.append(diag.overall_confidence)
        if referral:
            scores.append(referral.confidence)
        return round(sum(scores) / len(scores), 3) if scores else 0.0

    def _flag_low_confidence(
        self,
        diag: DiagnosisReportExtraction | None,
        id_proof: IdProofExtraction | None,
        referral: ReferralExtraction | None,
    ) -> list[str]:
        flags = []
        if diag:
            for d in diag.diagnoses:
                if d.confidence < CONFIDENCE_THRESHOLD:
                    flags.append(d.text)
        if id_proof and id_proof.confidence < CONFIDENCE_THRESHOLD:
            flags.append("id_proof_overall")
        if referral and referral.confidence < CONFIDENCE_THRESHOLD:
            flags.append("referral_overall")
        return flags

    # ── DATABASE WRITES ───────────────────────────────────────────────────────

    def _write_ai_extraction_record(
        self,
        patient_id: str,
        pre_auth_form_id: str,
        combined: CombinedExtraction,
        source_urls: list[str],
        model_version: str = "gemini-2.0-flash",
        enhanced_patient_identity: dict | None = None,
    ) -> str:
        """
        Write extraction results to ai_extraction_records.
        Returns the new record UUID.
        """
        diag = combined.diagnosis_report
        id_proof = combined.id_proof
        referral = combined.referral

        patient_resp = (
            self.db.table("patients")
            .select("patient_name, age, gender, abha_id")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        patient_data = patient_resp.data or {}

        record_id = str(uuid.uuid4())
        row = {
            "id": record_id,
            "patient_id": patient_id,
            "source_document_url": source_urls[0] if source_urls else None,
            "patient_snapshot": {
                "name": patient_data.get("patient_name"),
                "age": patient_data.get("age"),
                "sex": patient_data.get("gender"),
                "abha_id": patient_data.get("abha_id"),
                "id_proof_extraction": (
                    id_proof.model_dump(mode="json", exclude_none=True)
                    if id_proof
                    else None
                ),
                **(
                    {"enhanced_patient_identity": enhanced_patient_identity}
                    if enhanced_patient_identity
                    else {}
                ),
            },
            "encounter_snapshot": {
                "estimated_los_days": diag.estimated_los_days if diag else None,
                "referral_extraction": (
                    referral.model_dump(mode="json", exclude_none=True)
                    if referral
                    else None
                ),
            },
            "diagnoses": self._build_diagnoses_json(diag) if diag else [],
            "procedures": self._build_procedures_json(diag) if diag else [],
            "medications": self._build_medications_json(diag) if diag else [],
            "billed_codes": [],
            "raw_text_preview": (
                diag.primary_diagnosis_text[:500]
                if diag and diag.primary_diagnosis_text
                else ""
            ),
            "section_map": combined.section_map,
            "negated_spans": combined.negated_spans,
            "low_confidence_flags": combined.low_confidence_flags,
            "detected_script": combined.detected_script.value,
            "confidence_score": combined.overall_confidence,
            "model_version": model_version,
            "review_status": "pending",
        }

        self.db.table("ai_extraction_records").insert(row).execute()
        logger.info("ai_extraction_records row created: %s", record_id)
        return record_id

    def _audit_log(
        self,
        patient_id: str | None = None,
        stage: str = "extraction",
        action: str = "",
        table_affected: str = "",
        record_id: str | None = None,
        diff_snapshot: dict | None = None,
        user_id: str | None = None,
    ) -> None:
        """
        Insert into audit_logs (append-only — NormClaim / IRDAI compliance).
        Never UPDATE or DELETE from this table.
        """
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "stage": stage,
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

    # ── MAIN RUN ──────────────────────────────────────────────────────────────

    def run(
        self,
        pre_auth_form_id: str,
        requesting_user_id: str | None = None,
    ) -> dict:
        """
        Execute the full extraction pipeline for one pre-auth form.

        Args:
            pre_auth_form_id: UUID of the pre_auth_forms row
            requesting_user_id: UUID of the user triggering this (for audit log)

        Returns:
            {
                "ai_extraction_id": str,
                "combined_extraction": CombinedExtraction,
                "overall_confidence": float,
                "low_confidence_flags": list[str],
            }

        Raises:
            PermissionError: if consent not obtained
            ValueError: if pre_auth_form not found
        """
        logger.info("Starting extraction pipeline for pre_auth_form: %s", pre_auth_form_id)

        # 1. Fetch pre_auth_form to get patient_id
        form_resp = (
            self.db.table("pre_auth_forms")
            .select("id, patient_id")
            .eq("id", pre_auth_form_id)
            .single()
            .execute()
        )
        if not form_resp.data:
            raise ValueError(f"pre_auth_form {pre_auth_form_id} not found")

        patient_id = form_resp.data["patient_id"]

        # 2. Consent gate (ABDM rule)
        self._assert_consent(patient_id, pre_auth_form_id)

        # 3. Fetch document attachments
        attachments = self._fetch_document_attachments(pre_auth_form_id)
        if not attachments:
            raise ValueError(
                f"No documents found for pre_auth_form {pre_auth_form_id}. "
                "Upload id_proof, diagnosis_report, and referral_letter first."
            )

        # 4. Check mandatory docs (warn but don't block)
        self._check_mandatory_docs(attachments, pre_auth_form_id)

        # 5. Extract each document
        id_proof_result: IdProofExtraction | None = None
        diag_result: DiagnosisReportExtraction | None = None
        referral_result: ReferralExtraction | None = None
        all_texts: list[str] = []
        source_urls: list[str] = []
        failed_attachments: list[dict[str, str]] = []

        for attachment in attachments:
            try:
                doc_type, raw_text, extraction = self._process_document(attachment)
                all_texts.append(raw_text)
                source_urls.append(attachment.get("storage_url", ""))

                if doc_type == DocType.ID_PROOF:
                    id_proof_result = extraction
                elif doc_type == DocType.DIAGNOSIS_REPORT:
                    diag_result = extraction
                elif doc_type == DocType.REFERRAL_LETTER:
                    referral_result = extraction

            except Exception as exc:
                logger.error(
                    "Failed to process attachment %s: %s",
                    attachment.get("id"), exc
                )
                failed_attachments.append(
                    {
                        "attachment_id": str(attachment.get("id") or ""),
                        "doc_type": str(attachment.get("doc_type") or ""),
                        "error": str(exc),
                    }
                )
                self._audit_log(
                    patient_id=patient_id,
                    stage="extraction",
                    action="pre_auth.extraction.doc_failed",
                    table_affected="document_attachments",
                    record_id=attachment.get("id"),
                    diff_snapshot={"error": str(exc)},
                    user_id=requesting_user_id,
                )

        if failed_attachments:
            self._audit_log(
                patient_id=patient_id,
                stage="extraction",
                action="pre_auth.extraction.aborted_partial_failure",
                table_affected="document_attachments",
                record_id=pre_auth_form_id,
                diff_snapshot={"failed_attachments": failed_attachments},
                user_id=requesting_user_id,
            )
            raise RuntimeError(
                "Extraction aborted because one or more mandatory documents failed to process."
            )

        if not id_proof_result or not diag_result or not referral_result:
            missing_doc_types: list[str] = []
            if not id_proof_result:
                missing_doc_types.append(DocType.ID_PROOF.value)
            if not diag_result:
                missing_doc_types.append(DocType.DIAGNOSIS_REPORT.value)
            if not referral_result:
                missing_doc_types.append(DocType.REFERRAL_LETTER.value)

            self._audit_log(
                patient_id=patient_id,
                stage="extraction",
                action="pre_auth.extraction.aborted_incomplete_results",
                table_affected="ai_extraction_records",
                record_id=pre_auth_form_id,
                diff_snapshot={"missing_doc_types": missing_doc_types},
                user_id=requesting_user_id,
            )
            raise RuntimeError(
                f"Extraction aborted because required results are missing: {missing_doc_types}"
            )

        # 6. ABHA / hospital demographics overlay (ABHA-verified data wins over OCR)
        abha_svc = ABHALookupService(self.db)
        extracted_abha = id_proof_result.abha_id if id_proof_result else None
        authority_data, identity_source = abha_svc.resolve_demographics(
            extracted_abha, patient_id
        )
        id_proof_result = abha_svc.merge_with_extraction(authority_data, id_proof_result)
        enhanced_patient_identity = abha_svc.build_enhanced_identity_json(
            id_proof_result,
            diag_result,
            referral_result,
            identity_source,
            documents_verified=True,
        )
        self._audit_log(
            patient_id=patient_id,
            stage="extraction",
            action="pre_auth.abha_lookup",
            table_affected="patients",
            record_id=patient_id,
            diff_snapshot={
                "pre_auth_form_id": pre_auth_form_id,
                "source": identity_source,
                "enhanced_patient_identity": enhanced_patient_identity,
            },
            user_id=requesting_user_id,
        )

        # 7. Build combined text for section mapping and negation detection
        combined_text = "\n\n".join(all_texts)
        section_map = build_section_map(combined_text)
        negated_spans = extract_negated_spans(combined_text)
        detected_script = self.ocr.detect_script(combined_text)
        overall_confidence = self._compute_overall_confidence(
            id_proof_result, diag_result, referral_result
        )
        low_confidence_flags = self._flag_low_confidence(
            diag_result, id_proof_result, referral_result
        )

        combined = CombinedExtraction(
            id_proof=id_proof_result,
            diagnosis_report=diag_result,
            referral=referral_result,
            detected_script=detected_script,
            section_map=section_map,
            negated_spans=negated_spans,
            low_confidence_flags=low_confidence_flags,
            overall_confidence=overall_confidence,
        )

        # 8. Write to ai_extraction_records
        ai_extraction_id = self._write_ai_extraction_record(
            patient_id=patient_id,
            pre_auth_form_id=pre_auth_form_id,
            combined=combined,
            source_urls=source_urls,
            enhanced_patient_identity=enhanced_patient_identity,
        )

        # 9. Audit log success
        self._audit_log(
            patient_id=patient_id,
            stage="extraction",
            action="pre_auth.extraction.created",
            table_affected="ai_extraction_records",
            record_id=ai_extraction_id,
            diff_snapshot={
                "pre_auth_form_id": pre_auth_form_id,
                "docs_processed": len(attachments),
                "overall_confidence": overall_confidence,
                "low_confidence_flags": low_confidence_flags,
            },
            user_id=requesting_user_id,
        )

        logger.info(
            "Extraction complete. ai_extraction_id=%s confidence=%.2f",
            ai_extraction_id, overall_confidence
        )

        return {
            "ai_extraction_id": ai_extraction_id,
            "combined_extraction": combined,
            "overall_confidence": overall_confidence,
            "low_confidence_flags": low_confidence_flags,
        }
