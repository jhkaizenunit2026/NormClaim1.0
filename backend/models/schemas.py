"""
NormClaim — Pydantic Data Models
All I/O schemas for the NormClaim API.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Any, List, Optional, Dict


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


class AdmissionCreatedResponse(BaseModel):
    admission_id: str
    admission_number: str
    pre_auth_form_id: str
    patient_id: str
    message: str
    already_existed: bool = False


class AdmissionDetailResponse(BaseModel):
    id: str
    admission_number: str
    patient_id: str
    pre_auth_form_id: Optional[str] = None
    admitted_at: Optional[str] = None
    discharge_at: Optional[str] = None
    status: str = "admitted"
    created_by: Optional[str] = None


class EnhancementGenerateRequest(BaseModel):
    diagnosis_data: List[Dict[str, Any]] = Field(default_factory=list)
    procedures: List[Dict[str, Any]] = Field(default_factory=list)
    requested_amount: float = Field(..., gt=0, description="Current / original approved amount in INR")


class EnhancementGeneratedPayload(BaseModel):
    justification_text: str
    suggested_amount: float
    severity_score: float
    historical_approval_rate: float
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)
    supporting_codes: List[str] = Field(default_factory=list)
    confidence: float


class EnhancementCreateResponse(BaseModel):
    enhancement_id: str
    admission_id: str
    status: str = "draft"
    original_amount: float
    payload: EnhancementGeneratedPayload


class EnhancementDetailResponse(BaseModel):
    id: str
    admission_id: str
    original_amount: Optional[float] = None
    suggested_amount: Optional[float] = None
    justification_text: Optional[str] = None
    severity_score: Optional[float] = None
    cost_breakdown: Dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    tpa_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class EnhancementTPAUpdateRequest(BaseModel):
    tpa_response: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = Field(
        default=None,
        description="draft | submitted | approved | rejected",
    )


class BillBreakdown(BaseModel):
    """Structured hospital bill split at discharge (Stage 5)."""

    room_charges: float = 0
    medicines: float = 0
    procedures: float = 0
    investigations: float = 0
    doctor_fees: float = 0
    nursing_charges: float = 0
    consumables: float = 0
    total: float = 0
    confidence: float = Field(ge=0.0, le=1.0)


class DischargeProcessRequest(BaseModel):
    document_id: Optional[str] = Field(
        default=None,
        description="Discharge document id if POST /api/extract was run for a PDF summary",
    )
    bill_notes: Optional[str] = Field(
        default=None,
        description="Optional bill / charge notes for Gemini breakdown",
    )


class DischargeProcessResponse(BaseModel):
    admission_id: str
    discharge_summary: Dict[str, Any]
    fhir_bundle: Dict[str, Any]
    bill_breakdown: BillBreakdown
    icp_generated: bool
    fhir_source: str


class DischargeOptimizeRequest(BaseModel):
    bill_breakdown: Optional[BillBreakdown] = None
    diagnoses: List[Dict[str, Any]] = Field(default_factory=list)
    los_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Length of stay in days; inferred from admission when omitted",
    )


class ValidDeductionItem(BaseModel):
    description: str
    amount: float
    reason: str


class DischargeOptimizeResponse(BaseModel):
    admission_id: str
    predicted_copay: float
    valid_deductions: List[ValidDeductionItem]
    approval_probability: float
    optimized_claim_amount: float
    flags: List[str]
    estimated_tpa_time_minutes: int
    policy_snapshot: Dict[str, Any] = Field(default_factory=dict)


class DispatchRequest(BaseModel):
    recipient_email: EmailStr
    send_email: bool = Field(
        default=True,
        description="If false, only generate PDF and store metadata (no SMTP)",
    )


class DispatchResponse(BaseModel):
    dispatch_id: str
    admission_id: str
    recipient_email: str
    pdf_storage_key: Optional[str] = None
    dispatch_status: str
    dispatched_at: Optional[str] = None
    delivered_at: Optional[str] = None
    email_detail: Dict[str, Any] = Field(default_factory=dict)


class SettlementDeductionItem(BaseModel):
    description: str
    amount: float
    reason: Optional[str] = None


class SettlementLetterExtraction(BaseModel):
    """Structured fields extracted from a TPA settlement letter."""

    utr_number: Optional[str] = None
    settlement_amount: Optional[float] = None
    tds_amount: Optional[float] = None
    deductions: List[SettlementDeductionItem] = Field(default_factory=list)
    final_payable: Optional[float] = None
    settlement_date: Optional[str] = None
    remarks: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class SettlementParseResponse(BaseModel):
    settlement_id: Optional[str] = None
    admission_id: Optional[str] = None
    persisted: bool
    extraction: SettlementLetterExtraction


class SettlementRecordResponse(BaseModel):
    id: str
    admission_id: Optional[str] = None
    utr_number: Optional[str] = None
    settlement_amount: Optional[float] = None
    tds_amount: Optional[float] = None
    deductions: List[SettlementDeductionItem] = Field(default_factory=list)
    final_payable: Optional[float] = None
    settlement_date: Optional[str] = None
    remarks: Optional[str] = None
    confidence: Optional[float] = None
    parsed_at: Optional[str] = None


class FinanceReconcileRequest(BaseModel):
    expected_amount: float = Field(..., gt=0, description="Hospital expected / claimed amount in INR")
    bill_breakdown: Dict[str, Any] = Field(default_factory=dict)
    diagnoses: List[Dict[str, Any]] = Field(default_factory=list)
    settlement_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional raw settlement fields if no settlement_records row exists",
    )


class FinanceReconcileResponse(BaseModel):
    reconciliation_id: str
    admission_id: str
    expected_amount: float
    received_amount: float
    delta: float
    raise_flag: bool
    mismatch_category: str
    deductions_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    fraud_risk_score: float
    confidence: float
    status: str = "pending"


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
