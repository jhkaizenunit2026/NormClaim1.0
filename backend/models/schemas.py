"""
NormClaim — Pydantic Data Models
All I/O schemas for the NormClaim API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class PatientInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    abha_id: Optional[str] = None


class EncounterInfo(BaseModel):
    admit_date: Optional[str] = None
    discharge_date: Optional[str] = None
    ward: Optional[str] = None
    los_days: Optional[int] = None


class Diagnosis(BaseModel):
    text: str
    icd10_code: str
    icd10_system: str = "http://hl7.org/fhir/sid/icd-10"
    icd10_display: Optional[str] = None
    is_primary: bool = False
    confidence: float  # 0.0 – 1.0
    negated: bool = False
    uncertainty: str = "confirmed"
    section: str = "diagnosis"


class Procedure(BaseModel):
    text: str
    date: Optional[str] = None


class Medication(BaseModel):
    name: Optional[str] = None
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class ExtractionResult(BaseModel):
    document_id: str
    patient: PatientInfo
    encounter: EncounterInfo
    diagnoses: List[Diagnosis]
    procedures: List[Procedure]
    medications: List[Medication]
    billed_codes: List[str]  # ICD-10 codes found on the original bill
    raw_text_preview: str    # first 500 chars of extracted text
    detected_script: Optional[str] = None
    section_map: Dict[str, str] = Field(default_factory=dict)
    negated_spans: List[str] = Field(default_factory=list)
    low_confidence_flags: List[str] = Field(default_factory=list)


class ReconciliationItem(BaseModel):
    icd10_code: str
    description: str
    status: str        # "matched" | "missed" | "extra"
    estimated_value_inr: Optional[float] = None


class ReconciliationReport(BaseModel):
    document_id: str
    matched: List[ReconciliationItem]
    missed: List[ReconciliationItem]
    extra: List[ReconciliationItem]
    total_billed_codes: int
    total_extracted_codes: int
    estimated_claim_delta_inr: float
    confidence: float


class SpacyPreprocessResult(BaseModel):
    expanded_text: str
    section_map: Dict[str, str]  # sentence_index → section_label
    negated_spans: List[str]  # confirmed negated entity texts


class CorrectionItem(BaseModel):
    field: str  # e.g., "diagnoses[0].icd10_code"
    original_value: str
    corrected_value: str
    correction_reason: str


class HumanReview(BaseModel):
    document_id: str
    reviewer_notes: str
    corrections: List[CorrectionItem]
    reviewed_at: str


class FeedbackItem(BaseModel):
    document_id: str
    was_extraction_correct: bool
    correction_type: str  # "wrong_code" | "missed_diagnosis" | "false_positive" | "negation_error" | "hinglish_error" | "brand_name_error"
    details: str


class AnalyticsSnapshot(BaseModel):
    """Aggregated metrics for dashboard / pitch (in-memory + optional Supabase)."""

    total_documents: int
    total_extractions: int
    total_reconciliations: int
    total_feedback_events: int
    total_missed_diagnoses: int = 0
    avg_extraction_confidence: float
    avg_claim_delta_inr: float
    total_inr_recovered: float
    extraction_accuracy_rate: float  # share of feedback marked correct
    correction_type_counts: Dict[str, int] = Field(default_factory=dict)
    data_source: str = "memory"  # "memory" | "supabase" | "hybrid"


# ── Upload System Response Models ────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response returned after successful PDF upload."""
    document_id: str
    filename: str
    status: str = "uploaded"
    consent_obtained: bool
    uploaded_at: str
    message: str = "Document uploaded successfully. Ready for extraction."


class DocumentMeta(BaseModel):
    """Metadata for a single document (no file bytes)."""
    document_id: str
    filename: str
    status: str = "uploaded"
    uploaded_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response for list-all-documents endpoint."""
    documents: List[DocumentMeta]
    total: int


class ClaimCreateRequest(BaseModel):
    patientName: str
    age: Optional[int] = None
    sex: Optional[str] = None
    abhaId: Optional[str] = None
    diagnosis: str
    icd10Code: Optional[str] = None
    estimatedAmount: float
    doctor: Optional[str] = None


class ClaimStatusUpdateRequest(BaseModel):
    status: str
    amount: Optional[float] = None
    enhancementAmount: Optional[float] = None
    copay: Optional[float] = None
    deductions: Optional[float] = None
    tpaPayableAmount: Optional[float] = None
    finalSettlementAmount: Optional[float] = None
    tdsAmount: Optional[float] = None
    utrNumber: Optional[str] = None
    admissionNumber: Optional[str] = None
    dischargeApprovalDeadline: Optional[str] = None


class ClaimResponse(BaseModel):
    claimId: str
    patientName: str
    age: Optional[int] = None
    sex: Optional[str] = None
    abhaId: Optional[str] = None
    diagnosis: str
    icd10Code: Optional[str] = None
    status: str
    preAuthAmount: float = 0.0
    updatedAt: Optional[str] = None
    createdAt: Optional[str] = None
    admissionNumber: Optional[str] = None
    enhancementAmount: float = 0.0
    copay: float = 0.0
    deductions: float = 0.0
    tpaPayableAmount: float = 0.0
    finalSettlementAmount: float = 0.0
    tdsAmount: float = 0.0
    utrNumber: Optional[str] = None
    dischargeApprovalDeadline: Optional[str] = None
    timeline: List[Dict[str, str]] = Field(default_factory=list)
