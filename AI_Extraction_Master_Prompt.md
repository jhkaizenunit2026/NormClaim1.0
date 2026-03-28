# NormClaim — AI Extraction & Form-Filling Master Implementation Prompt

> Paste this entire prompt into any AI coding agent to implement the full 9-stage
> AI extraction, form auto-fill, and finance reconciliation architecture inside
> the existing NormClaim monorepo.

---

## 0. PROJECT CONTEXT & EXISTING CODEBASE

You are extending **NormClaim** — an AI-powered Clinical & Administrative Data
Normalization Engine for Indian SME hospitals. The monorepo already exists at:

```
NormClaim1.0/
├── backend/                     # FastAPI (Python 3.11) on :8000
│   ├── main.py                  # App entry + all router mounts
│   ├── Extraction_pipeline/     # ★ ALREADY BUILT — pre-auth extraction + form fill
│   │   ├── extraction_pipeline.py   # OCR + Gemini extraction engine
│   │   ├── pre_auth_filling.py      # Auto-fill + correction handler + orchestrator
│   │   ├── router.py                # /api/preauth/* endpoints
│   │   ├── database.py              # SQLAlchemy adapter mimicking Supabase API
│   │   └── text_features.py         # Section map, negation, script detection
│   ├── services/                # Generic NormClaim services
│   │   ├── extractor.py         # spaCy + Gemini discharge extraction
│   │   ├── nlp_preprocessor.py  # Abbreviation expansion, section detection
│   │   ├── reconciler.py        # ICD-10 diff + ₹ delta engine
│   │   ├── fhir_client.py       # HTTP proxy to Java FHIR service
│   │   ├── fhir_mapper.py       # Python-side FHIR mapping
│   │   ├── claim_structuring.py # DRG/package mapping
│   │   ├── review_service.py    # Human review logic
│   │   ├── feedback_service.py  # Feedback loop storage
│   │   ├── persistence.py       # SQLite + memory cache layer
│   │   └── analytics_service.py # Dashboard analytics
│   ├── routers/                 # All API route files
│   │   ├── documents.py, extract.py, fhir.py, reconcile.py
│   │   ├── review.py, feedback.py, claims.py, analytics.py
│   │   ├── auth.py, config.py, validate.py
│   ├── models/
│   │   ├── schemas.py           # Pydantic models
│   │   └── database.py          # SQLAlchemy setup
│   └── data/
│       ├── icd10_codes.json, abbrev_map.json, drug_map.json
├── fhir-service/                # HAPI FHIR R4 Java Spring Boot on :8001
├── web-dashboard/               # Static HTML/CSS/JS
├── android/                     # Android app (Java)
└── docker-compose.yml
```

**KEY RULE:** The `Extraction_pipeline/` module already handles Stages 1-2
(pre-auth extraction + form fill). DO NOT rewrite it. All new stages must
integrate with it or extend it.

**Tech stack already in use:**
- FastAPI + Pydantic + Supabase (via SQLAlchemy adapter)
- Gemini 2.0 Flash via `instructor` library (schema-enforced extraction)
- pytesseract + pdfplumber + OpenCV for OCR
- HAPI FHIR R4 v7.0.0 (Java Spring Boot)
- Append-only `audit_logs` table for IRDAI compliance

---

## 1. STAGE 1 — PRE-AUTH FORMS (INPUT)

**Status: ✅ ALREADY BUILT** in `Extraction_pipeline/extraction_pipeline.py`

### What exists:
- `OCRProcessor` — PDF (pdfplumber + pytesseract fallback), image, DOCX, TXT
- `GeminiExtractionEngine` — extracts `IdProofExtraction`, `DiagnosisReportExtraction`, `ReferralExtraction`
- `ExtractionPipeline.run()` — full orchestration with consent gate, document fetch, OCR, Gemini extraction, DB write

### What to ADD (extend, don't rewrite):

#### 1a. ABHA ID Lookup (FHIR API integration)
**File:** `backend/Extraction_pipeline/abha_lookup.py` [NEW]

```python
# Logic:
# 1. If IdProofExtraction.abha_id is present → call ABDM FHIR API
# 2. Use NDHM Health ID API: GET /v1/ha/hip/fetchPatient/{abhaId}
# 3. If API returns patient data → merge into patient record (ABHA wins)
# 4. If no ABHA ID or API fails → fallback to hospital DB (patients table)
# 5. Always log to audit_logs

class ABHALookupService:
    FHIR_BASE = "https://healthidsbx.abdm.gov.in/api"  # sandbox
    
    def fetch_patient(self, abha_id: str) -> dict | None:
        """Fetch patient demographics from ABDM via FHIR API."""
        # For hackathon: simulate with patients table lookup
        # Post-hackathon: real ABDM API integration
        
    def merge_with_extraction(
        self, abha_data: dict | None, extraction: IdProofExtraction
    ) -> dict:
        """ABHA data takes precedence over OCR extraction."""
```

#### 1b. Enhanced output JSON target:
```json
{
  "patient_name": "from ABHA or extraction",
  "abha_id": "91-XXXX-XXXX-XXXX",
  "diagnosis": "from diagnosis_report extraction",
  "doctor_name": "from referral extraction",
  "documents_verified": true,
  "source": "abha | hospital_db | extraction"
}
```

Wire into `ExtractionPipeline.run()` after step 5 (extraction), before step 7 (DB write).

---

## 2. STAGE 2 — PRE-AUTH FORM AUTO-FILL + APPROVAL

**Status: ✅ ALREADY BUILT** in `Extraction_pipeline/pre_auth_filling.py`

### What exists:
- `PreAuthFieldMapper` — maps extraction → form fields with confidence scores
- `PreAuthFiller.fill()` — writes to `pre_auth_forms`, builds `field_requirements_meta`
- `CorrectionHandler` — human reviewer corrections with audit trail
- `PreAuthOrchestrator` — ties extraction + filling in one call
- Confidence-gated writing: `confidence < 0.70 → send to human`

### What to ADD:

#### 2a. Enhanced field_requirements_meta format  
**File:** Modify `pre_auth_filling.py` — update `FieldMapping` output to include:
```json
{
  "field_name": {
    "value": "extracted_value",
    "mandatory": true,
    "confidence": 0.92,
    "source": "diagnosis_report",
    "needs_human_review": false
  }
}
```
This is already close to what exists. Ensure the `auto_fill_snapshot_json` captures this exact structure.

#### 2b. Approval workflow endpoint
**File:** `backend/Extraction_pipeline/router.py` — ADD:
```
POST /api/preauth/approve/{pre_auth_form_id}  → transitions form_status to "approved"
POST /api/preauth/reject/{pre_auth_form_id}   → transitions to "rejected" with reason
```

---

## 3. STAGE 3 — PATIENT ADMISSION

**Status: 🔨 NEW — build this**

**File:** `backend/services/admission_service.py` [NEW]

```python
class AdmissionService:
    """
    Generates admission number after pre-auth approval.
    Writes to admissions table in Supabase.
    """
    ADMISSION_PREFIX = "ADM"  # ADM-2026-00001
    
    def generate_admission_number(self) -> str:
        """Sequential ID: ADM-{YYYY}-{5-digit counter}"""
        
    def admit_patient(
        self, pre_auth_form_id: str, patient_id: str, user_id: str
    ) -> dict:
        """
        1. Validate pre_auth_form.form_status == 'approved'
        2. Generate admission number
        3. Insert into admissions table
        4. Update pre_auth_forms.admission_id
        5. Log to audit_logs
        Returns: {"admission_id": str, "admission_number": str}
        """
```

**SQL table:**
```sql
CREATE TABLE admissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_number TEXT UNIQUE NOT NULL,
    patient_id UUID REFERENCES patients(id),
    pre_auth_form_id UUID REFERENCES pre_auth_forms(id),
    admitted_at TIMESTAMPTZ DEFAULT now(),
    discharge_at TIMESTAMPTZ,
    status TEXT DEFAULT 'admitted',  -- admitted | discharged | cancelled
    created_by UUID
);
```

**Router:** `backend/routers/admissions.py` [NEW]
```
POST /api/admissions/{pre_auth_form_id}  → create admission
GET  /api/admissions/{admission_id}      → get admission details
```

---

## 4. STAGE 4 — ENHANCEMENT RAISE (CRITICAL AI)

**Status: 🔨 NEW — build this**

**Goal:** Increase insurance approval probability + amount using AI-generated justifications.

**File:** `backend/services/enhancement_service.py` [NEW]

```python
class EnhancementService:
    """
    Uses Gemini to generate medically-justified enhancement requests.
    Pulls historical approval data for RAG-style context.
    """
    
    SYSTEM_PROMPT = """You are a medical insurance enhancement specialist.
    Given a diagnosis, procedures, and historical approval patterns,
    generate a compelling medical justification for the requested amount.
    
    Rules:
    1. Cite diagnosis severity using ICD-10 classification
    2. Reference standard treatment protocols
    3. Include cost breakdown justification
    4. Be factual — never fabricate medical information
    5. Return structured JSON only
    """
    
    def generate_enhancement(
        self, admission_id: str, diagnosis_data: list[dict],
        procedures: list[dict], requested_amount: float
    ) -> dict:
        """
        1. Extract diagnosis severity from ICD-10 codes
        2. Pull historical approvals for similar diagnoses (RAG)
        3. Generate justification text via Gemini
        4. Return structured enhancement request
        """
        # Output:
        return {
            "justification_text": "Medically necessary due to...",
            "suggested_amount": 85000,
            "severity_score": 0.82,
            "historical_approval_rate": 0.78,
            "cost_breakdown": {
                "room_charges": 20000,
                "procedures": 35000,
                "medicines": 15000,
                "investigations": 15000
            },
            "supporting_codes": ["E11.4", "N18.3"],
            "confidence": 0.85
        }
```

**SQL table:**
```sql
CREATE TABLE enhancement_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID REFERENCES admissions(id),
    original_amount FLOAT,
    suggested_amount FLOAT,
    justification_text TEXT,
    severity_score FLOAT,
    cost_breakdown JSONB,
    status TEXT DEFAULT 'draft',  -- draft | submitted | approved | rejected
    tpa_response JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Router:** `backend/routers/enhancements.py` [NEW]
```
POST /api/enhancements/{admission_id}     → generate enhancement
GET  /api/enhancements/{enhancement_id}   → get enhancement details
PUT  /api/enhancements/{enhancement_id}   → update with TPA response
```

---

## 5. STAGE 5 — DISCHARGE INTIMATION + FHIR

**Status: ✅ PARTIALLY BUILT** — FHIR bundle generation exists in `fhir-service/`

### What exists:
- `services/extractor.py` — spaCy + Gemini discharge summary extraction
- `services/fhir_client.py` — HTTP proxy to Java FHIR service
- `services/fhir_mapper.py` — Python-side FHIR mapping
- `fhir-service/` — HAPI FHIR R4 Java Spring Boot

### What to ADD:

#### 5a. Discharge Summary Service
**File:** `backend/services/discharge_service.py` [NEW]

```python
class DischargeService:
    """
    Orchestrates discharge intimation:
    1. Generate discharge summary from clinical data
    2. Extract bill breakdown via Gemini
    3. Convert to FHIR R4 Bundle (ABDM compliant)
    4. Generate ICP (Individual Care Plan) if applicable
    """
    
    def process_discharge(self, admission_id: str) -> dict:
        """
        Returns:
        {
            "discharge_summary": {...},
            "fhir_bundle": {...},  # from existing fhir-service
            "bill_breakdown": {
                "room_charges": 20000,
                "medicines": 15000,
                "procedures": 30000,
                "investigations": 10000,
                "total": 75000
            },
            "icp_generated": true
        }
        """
```

#### 5b. Bill Breakdown Extraction
Use existing `GeminiExtractionEngine` pattern with a new Pydantic schema:

```python
class BillBreakdown(BaseModel):
    room_charges: float = 0
    medicines: float = 0
    procedures: float = 0
    investigations: float = 0
    doctor_fees: float = 0
    nursing_charges: float = 0
    consumables: float = 0
    total: float = 0
    confidence: float = Field(ge=0.0, le=1.0)
```

---

## 6. STAGE 6 — DISCHARGE APPROVAL OPTIMIZATION

**Status: 🔨 NEW — build this**

**File:** `backend/services/discharge_optimizer.py` [NEW]

```python
class DischargeOptimizer:
    """
    AI + Rule engine hybrid to:
    1. Predict copay amount
    2. Calculate valid deductions
    3. Estimate approval probability
    4. Flag policy violations
    
    Goal: Reduce TPA approval time from 3 hours → minutes
    """
    
    # Rule engine: policy limits, sub-limits, exclusions
    POLICY_RULES = {
        "room_rent_cap_percent": 1.0,  # 1% of sum insured per day
        "icu_multiplier": 2.0,
        "pre_existing_waiting_period_years": 2,
    }
    
    def optimize(
        self, admission_id: str, bill_breakdown: dict,
        policy: dict, diagnoses: list[dict]
    ) -> dict:
        """
        Returns:
        {
            "predicted_copay": 5000,
            "valid_deductions": [...],
            "approval_probability": 0.89,
            "optimized_claim_amount": 70000,
            "flags": ["room_rent_exceeds_sublimit"],
            "estimated_tpa_time_minutes": 15
        }
        """
```

---

## 7. STAGE 7 — HARD COPY DISPATCH

**Status: 🔨 NEW — build this**

**File:** `backend/services/dispatch_service.py` [NEW]

```python
class DispatchService:
    """
    Generate and dispatch final claim documents:
    1. Generate PDF from structured data (use reportlab)
    2. Auto-email to TPA/insurer
    3. Track dispatch status
    """
    
    def generate_claim_pdf(self, admission_id: str) -> bytes:
        """Generate formatted PDF claim document."""
        
    def dispatch_email(
        self, admission_id: str, recipient_email: str, pdf_bytes: bytes
    ) -> dict:
        """Send claim PDF via email. Returns dispatch tracking info."""
        
    def get_dispatch_status(self, dispatch_id: str) -> dict:
        """Track email delivery status."""
```

---

## 8. STAGE 8 — SETTLEMENT LETTER PARSING

**Status: 🔨 NEW — build this**

**File:** `backend/services/settlement_parser.py` [NEW]

Use the same `instructor + Gemini` pattern from `Extraction_pipeline/extraction_pipeline.py`:

```python
class SettlementExtraction(BaseModel):
    """Structured extraction from TPA settlement letters."""
    utr_number: str | None = None
    settlement_amount: float | None = None
    tds_amount: float | None = None
    deductions: list[DeductionItem] = Field(default_factory=list)
    final_payable: float | None = None
    settlement_date: str | None = None
    remarks: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

class DeductionItem(BaseModel):
    description: str
    amount: float
    reason: str | None = None

class SettlementParser:
    """
    Parse TPA settlement letters using OCR + Gemini.
    Reuses OCRProcessor from Extraction_pipeline.
    """
    def parse(self, file_bytes: bytes, file_format: str) -> SettlementExtraction:
        """OCR → Gemini structured extraction → SettlementExtraction"""
```

**Router:** `backend/routers/settlements.py` [NEW]
```
POST /api/settlements/parse          → upload + parse settlement letter
GET  /api/settlements/{admission_id} → get parsed settlement data
```

---

## 9. STAGE 9 — FINANCE RECONCILIATION

**Status: ✅ PARTIALLY BUILT** — `services/reconciler.py` handles ICD-10 diff

### What exists:
- `reconciler.py` — ICD-10 code diff + ₹ delta calculation
- DRG claim value estimation table

### What to ADD:

**File:** `backend/services/finance_reconciler.py` [NEW]

```python
class FinanceReconciler:
    """
    Compares settlement amount vs expected amount.
    Categorizes mismatches and flags anomalies.
    
    This is the MOST IMPORTANT feature for hospital finance teams.
    """
    
    MISMATCH_CATEGORIES = [
        "legitimate_deduction",   # Policy sub-limit, copay
        "processing_delay",       # Payment pending
        "coding_error",           # Wrong ICD-10 → lower package rate
        "documentation_gap",      # Missing supporting documents
        "potential_fraud",        # Unusual pattern
    ]
    
    def reconcile(
        self, admission_id: str,
        expected_amount: float,
        settlement: SettlementExtraction,
        bill_breakdown: dict,
        diagnoses: list[dict]
    ) -> dict:
        """
        Returns:
        {
            "expected_amount": 85000,
            "received_amount": 72000,
            "delta": -13000,
            "raise_flag": true,
            "mismatch_category": "coding_error",
            "deductions_analysis": [...],
            "recommendations": [
                "Resubmit with corrected ICD-10 code E11.4 instead of E11.9",
                "Attach supporting lab report for CKD diagnosis"
            ],
            "fraud_risk_score": 0.12,
            "confidence": 0.88
        }
        """
        # Core logic:
        delta = settlement.final_payable - expected_amount
        raise_flag = delta < 0
        
        # Categorize each deduction
        # Use Gemini to analyze deduction reasons vs policy terms
        # Flag suspicious patterns using historical data
```

**SQL table:**
```sql
CREATE TABLE finance_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID REFERENCES admissions(id),
    expected_amount FLOAT,
    received_amount FLOAT,
    delta FLOAT,
    mismatch_category TEXT,
    deductions_analysis JSONB,
    recommendations JSONB,
    fraud_risk_score FLOAT,
    status TEXT DEFAULT 'pending',  -- pending | resolved | escalated
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 10. FULL PIPELINE FLOW — WIRING IT ALL TOGETHER

### main.py — Add new routers:
```python
from routers.admissions import router as admissions_router
from routers.enhancements import router as enhancements_router
from routers.settlements import router as settlements_router
from routers.finance_recon import router as finance_recon_router

app.include_router(admissions_router)
app.include_router(enhancements_router)
app.include_router(settlements_router)
app.include_router(finance_recon_router)
```

### End-to-end API flow:
```
1. POST /api/preauth/auto-fill/{form_id}        → Stage 1+2 (EXISTING)
2. POST /api/preauth/approve/{form_id}           → Stage 2 approval
3. POST /api/admissions/{form_id}                → Stage 3 admission
4. POST /api/enhancements/{admission_id}         → Stage 4 enhancement
5. POST /api/extract/{document_id}               → Stage 5 discharge extract (EXISTING)
6. POST /api/fhir/{document_id}                  → Stage 5 FHIR bundle (EXISTING)
7. POST /api/discharge/optimize/{admission_id}   → Stage 6 optimization
8. POST /api/dispatch/{admission_id}             → Stage 7 PDF + email
9. POST /api/settlements/parse                   → Stage 8 settlement parsing
10. POST /api/finance/reconcile/{admission_id}   → Stage 9 reconciliation
```

---

## 11. DATABASE SCHEMA ADDITIONS

Add these tables via Supabase SQL or SQLAlchemy models:

```sql
-- Stage 3
CREATE TABLE admissions (...);  -- see Stage 3 above

-- Stage 4
CREATE TABLE enhancement_requests (...);  -- see Stage 4 above

-- Stage 7
CREATE TABLE dispatch_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID REFERENCES admissions(id),
    recipient_email TEXT,
    pdf_storage_key TEXT,
    dispatch_status TEXT DEFAULT 'pending',
    dispatched_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ
);

-- Stage 8
CREATE TABLE settlement_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admission_id UUID REFERENCES admissions(id),
    utr_number TEXT,
    settlement_amount FLOAT,
    tds_amount FLOAT,
    deductions JSONB,
    final_payable FLOAT,
    parsed_at TIMESTAMPTZ DEFAULT now()
);

-- Stage 9
CREATE TABLE finance_reconciliations (...);  -- see Stage 9 above
```

---

## 12. BUILD ORDER

**Follow exactly. Do not skip ahead.**

1. ✅ Verify existing Stages 1-2 work (`/api/preauth/auto-fill`)
2. Add ABHA lookup to Stage 1 (`abha_lookup.py`)
3. Add approval/reject endpoints to Stage 2 (`router.py`)
4. Build Stage 3: `admission_service.py` + `routers/admissions.py` + SQL
5. Build Stage 4: `enhancement_service.py` + `routers/enhancements.py` + SQL
6. Build Stage 5 additions: `discharge_service.py` + bill breakdown schema
7. Build Stage 6: `discharge_optimizer.py`
8. Build Stage 7: `dispatch_service.py` + `routers/dispatch.py` + SQL
9. Build Stage 8: `settlement_parser.py` + `routers/settlements.py` + SQL
10. Build Stage 9: `finance_reconciler.py` + `routers/finance_recon.py` + SQL
11. Wire all new routers into `main.py`
12. End-to-end test: full 9-stage flow with synthetic data

---

## 13. CRITICAL RULES

1. **Every DB write → audit_logs.** Use the existing `_audit_log()` pattern.
2. **Confidence gating.** Fields with `confidence < 0.70` → flag for human review.
3. **Negation handling.** Negated diagnoses from `text_features.extract_negated_spans()` must NEVER enter claims or FHIR bundles.
4. **ABHA priority.** ABHA-verified data always wins over OCR extraction.
5. **Gemini calls.** Use `instructor` library with Pydantic response models (existing pattern in `extraction_pipeline.py`). Temperature = 0.1.
6. **ICD-10 system URI.** Always `http://hl7.org/fhir/sid/icd-10`.
7. **ABHA format.** Always `91-XXXX-XXXX-XXXX`.
8. **Supabase adapter.** Use `Extraction_pipeline/database.py` `SQLDatabaseAdapter` for DB access in new modules.

---

*NormClaim — Extract → Normalize → Optimize → Comply → Reconcile*
