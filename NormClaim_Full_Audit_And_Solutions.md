# NormClaim 1.0 — Full Technical Audit & Solutions Guide

> **Every diagnosis. Every rupee.**
> Team Kaizen Unit · Madhav Institute of Technology and Science, Gwalior
> Jilo Health Hackathon × NJACK IIT Patna · PS-2

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [PS-2 Deliverable Coverage Map](#4-ps-2-deliverable-coverage-map)
5. [Overall Readiness Scorecard](#5-overall-readiness-scorecard)
6. [Critical Bugs — App Cannot Run](#6-critical-bugs--app-cannot-run)
7. [High Severity Issues](#7-high-severity-issues)
8. [Medium Severity Issues](#8-medium-severity-issues)
9. [What Is Missing (Not Built)](#9-what-is-missing-not-built)
10. [What Is Strong](#10-what-is-strong)
11. [Solutions — Complete Code Fixes](#11-solutions--complete-code-fixes)
12. [Pre-Hackathon Fix Priority Order](#12-pre-hackathon-fix-priority-order)
13. [Post-Hackathon Roadmap](#13-post-hackathon-roadmap)

---

## 1. Project Overview

NormClaim is an AI pipeline that solves two simultaneous problems for Indian SME hospitals:

**Problem 1 — Revenue leakage:**
Billing clerks manually transcribe discharge summaries into ICD-10 codes. They miss comorbidities and secondary diagnoses. Hospitals lose ₹12,000–40,000 per discharge in unclaimed diagnoses. 68% of SME hospitals under-code claims due to manual entry.

**Problem 2 — ABDM compliance:**
From 2026, all AB-PMJAY empanelled hospitals must produce ABDM-compliant FHIR R4 records for digital claim submission. Most have no infrastructure.

**Solution Pipeline:**
```
PDF (discharge summary / lab report / bill)
        ↓
  Multi-Format Ingestion
        ↓
  Document Digitization (OCR / pdfplumber)
        ↓
  spaCy Pre-Processing (abbrev expansion, section detection, negation)
        ↓
  Gemini 1.5 Flash (entity extraction, ICD-10 mapping, Hinglish)
        ↓
  Post-Processing Override (spaCy wins on negation)
        ↓
  FHIR R4 Bundle (ABDM-compliant)
        ↓
  Claim Structuring (payer-aware)
        ↓
  Validation & Error Detection
        ↓
  Human Review Layer (confidence-flagged)
        ↓
  Feedback Loop
        ↓
  ₹ Claim Gap Report + Revenue Delta
```

**Demo scenario (Rajesh Kumar, 58M, Pneumonia):**
- Original bill: `J18.9` only
- NormClaim extracts: `J18.9`, `E11.9`, `I10`, `N18.3` + excludes "No h/o TB" (negated)
- Estimated claim delta: **₹14,200 – ₹17,500**

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│   Android App (Java)          Web Dashboard (HTML/JS)       │
│   MainActivity                index.html                    │
│   UploadActivity              review.html                   │
│   ResultActivity              reconcile.html                │
└──────────────┬──────────────────────────┬───────────────────┘
               │ Retrofit2                │ fetch()
               ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend  :8000  (Python)              │
│                                                             │
│  POST /api/documents     → store uploaded PDF               │
│  POST /api/extract/{id}  → run AI extraction pipeline       │
│  POST /api/fhir/{id}     → build FHIR R4 Bundle             │
│  POST /api/reconcile/{id}→ run ICD-10 diff + ₹ delta        │
│  GET  /api/documents     → list all documents + status      │
└──────┬─────────────────────────────────┬────────────────────┘
       │                                 │
       ▼                                 ▼
┌──────────────────┐          ┌──────────────────────────────┐
│  Two-Layer NLP   │          │  FHIR R4 Bundle              │
│                  │          │  (fhir.resources Python lib) │
│  Layer 1: spaCy  │          │                              │
│  - Abbrev expand │          │  Patient, Encounter,         │
│  - Section detect│          │  Condition, Observation,     │
│  - ConText negat.│          │  MedicationRequest,          │
│                  │          │  Procedure, Claim, Bundle    │
│  Layer 2: Gemini │          └──────────────────────────────┘
│  - Entity extract│
│  - ICD-10 mapping│          ┌──────────────────────────────┐
│  - Hinglish→EN   │          │  Supabase (Storage + DB)     │
│  - Brand→INN     │          │                              │
│                  │          │  documents                   │
│  Layer 3 (post): │          │  extractions                 │
│  - spaCy wins on │          │  fhir_bundles                │
│    negation      │          │  reconciliations              │
└──────────────────┘          │  human_reviews               │
                              │  feedback                    │
                              └──────────────────────────────┘
```

### FHIR Resources Generated

| Resource | Source | ABDM Profile |
|---|---|---|
| `Patient` | Discharge summary header | AbdmPatient |
| `Encounter` | Admission/discharge dates | AbdmEncounter |
| `Condition` | Diagnoses → ICD-10 coded (non-negated only) | AbdmCondition |
| `Observation` | Lab report values → LOINC | AbdmObservation |
| `MedicationRequest` | Discharge medications (INN names) | AbdmMedicationRequest |
| `Procedure` | Surgical/diagnostic procedures | AbdmProcedure |
| `Claim` | Bill/claim document (non-negated diagnoses only) | AbdmClaim |
| `Bundle` | Wraps all resources | AbdmDocumentBundle |

---

## 3. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend API | FastAPI · Python 3.11 · uvicorn | Async REST, auto OpenAPI docs |
| NLP Layer 1 | spaCy 3.x · medspaCy · en_core_web_sm | Deterministic negation (ConText algorithm) |
| NLP Layer 2 | Gemini 1.5 Flash (google-genai SDK) | Multimodal, Hinglish, ICD-10 semantic mapping |
| PDF Parsing | pdfplumber (digital) · Gemini Vision (scanned fallback) | Handles both digital and scanned PDFs |
| FHIR Mapping | `fhir.resources` Python library (R4) | No Java dependency, ABDM-compliant |
| ICD-10 Validation | rapidfuzz · local icd10_codes.json | Offline fuzzy correction of LLM code outputs |
| Storage/DB | Supabase (optional) · SQLite (default) | Supabase for production, SQLite for local demo |
| Frontend | Static HTML/CSS/JS + Supabase JS client | Works without a build step |
| Android | Java · Retrofit2 · Material Design | Clerk on mobile |
| Containerization | Docker + docker-compose.yml | One-command startup |

### Python dependencies (`requirements.txt`)

```
fastapi
uvicorn[standard]
pdfplumber
Pillow
pdf2image
google-genai
spacy
medspacy
rapidfuzz
supabase==2.4.0
python-dotenv==1.0.1
httpx
sqlalchemy
fhir.resources
python-multipart
```

> **Note:** Use `google-genai` (new SDK, `from google import genai`), NOT `google-generativeai` (old SDK). These are two different PyPI packages with incompatible APIs.

---

## 4. PS-2 Deliverable Coverage Map

| PS-2 Deliverable | Status | Gap |
|---|---|---|
| Data Ingestion Module | ⚠️ Partial | Upload works; PDF→bytes pipeline broken in extract router |
| AI Extraction Layer | ⚠️ Built, not wired | Code in extractor.py never called from router |
| FHIR Mapping Engine | ❌ Not working | Java service absent; Python proxy always 503s |
| Revenue Reconciliation Logic | ⚠️ Partial | ICD-10 diff correct; INR values are demo placeholders |
| Human Review UI | ❌ Not built | Schemas exist, no frontend, no endpoint |
| Feedback Loop | ❌ Not built | FeedbackItem schema only; no storage or endpoint |
| Web Dashboard | ❌ Not built | Directory doesn't exist |
| Android App | ❌ Not built | Directory doesn't exist |
| Docker Compose | ❌ Not built | Referenced in README, absent from repo |
| Test Data (PDFs) | ⚠️ Partial | generate.py exists; PDFs not committed |

---

## 5. Overall Readiness Scorecard

| Component | Completeness | Notes |
|---|---|---|
| Architecture & design docs | 95% | NORMCLAIM_CONTEXT.md is outstanding |
| FastAPI backend skeleton | 80% | All 4 routes registered; routing logic broken |
| Pydantic schemas / data models | 90% | Complete and correct |
| NLP pipeline (spaCy + Gemini) | 50% | Built but import errors and wrong wiring |
| Reconciliation engine (₹ delta) | 65% | Logic correct; INR rates are placeholder |
| Document storage (working) | 15% | Supabase ↔ in-memory dict completely disconnected |
| Web dashboard | 0% | Not started |
| FHIR layer (working) | 10% | Proxy exists; backend service absent |
| Android app | 0% | Not started |

> **Overall functional completeness: ~38%**
> The architecture is excellent. The critical extraction pipeline has structural bugs preventing end-to-end functionality. The frontend and FHIR service layers are entirely absent.

---

## 6. Critical Bugs — App Cannot Run

### 🔴 BUG-001: Gemini Is Never Called — Core AI Extraction Missing

**File:** `routers/extract.py`

**Problem:**
The extract router calls `process_text()` from `nlp_pipe/extraction_pipeline.py`, which only performs spaCy preprocessing and returns a raw dict. The real two-layer pipeline lives in `services/extractor.py → extract_from_document()` and is **never called from any router**.

Additionally, the router decodes PDF bytes as UTF-8:
```python
# WRONG — PDFs are binary files
raw_text = file_bytes.decode("utf-8")
```
This crashes or produces garbage on any real PDF.

**Impact:** Zero AI extraction. The app's entire purpose fails silently.

---

### 🔴 BUG-002: Two Incompatible Extractors Concatenated in One File

**File:** `services/extractor.py`

**Problem:**
The file contains two full, conflicting implementations concatenated without a separator:

- **First half** — uses `from google import genai` (new SDK, correct). Model: `gemini-2.5-flash-lite`.
- **Second half** — uses `import google.generativeai as palm` and calls `palm.chat()`, a method that **does not exist** in any version of `google-generativeai`. Also contains `from backend.services.nlp_preprocessor import preprocess` — an absolute import that crashes when running from `backend/`.

Python silently overwrites the first set of functions with the second half, then crashes at import time due to the broken absolute import.

**Impact:** App crashes at import. No extraction runs.

---

### 🔴 BUG-003: Supabase ↔ In-Memory Dict — Every Extraction Returns 404

**Files:** `routers/documents.py` ↔ `routers/extract.py`

**Problem:**
- `POST /api/documents` stores the file to Supabase Storage but **never populates** the in-memory `DOCUMENTS` dict.
- `POST /api/extract/{id}` checks `if document_id not in DOCUMENTS` and returns HTTP 404.
- Since `DOCUMENTS` is always empty (files go to Supabase, not the dict), **every extraction attempt returns 404**.
- `GET /api/documents` reads from the in-memory dict, returning an empty list even when documents exist in Supabase.

The two storage systems are completely disconnected.

**Impact:** No document can ever be extracted. The full pipeline is blocked.

---

### 🔴 BUG-004: App Crashes at Startup Without Supabase Credentials

**File:** `main.py` (lines 65–67)

**Problem:**
```python
if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Supabase credentials missing.")
```
The app throws at startup without `.env` configured. No `.env.example` is in the repo, so a fresh clone has no reference. For a hackathon demo, this is a hard blocker.

**Impact:** App cannot start on any machine without pre-configured Supabase credentials.

---

## 7. High Severity Issues

### 🟠 BUG-005: JSON Files Imported as Python Modules

**File:** `services/nlp_preprocessor.py`

**Problem:**
```python
from backend.data.abbrev_map import abbrev_map  # WRONG
from backend.data.drug_map import drug_map       # WRONG
```
`abbrev_map.json` and `drug_map.json` are JSON files, not Python modules. These raise `ModuleNotFoundError` at startup.

---

### 🟠 BUG-006: Broken Regex — Double-Escaped Backslashes

**File:** `services/nlp_preprocessor.py`

**Problem:**
```python
# WRONG — \\b is a literal backslash + b, not a word boundary
pattern = re.compile(r"\\b" + re.escape(abbr) + r"\\b", re.IGNORECASE)
```
In a raw string, `\\b` is a literal two-character sequence `\b`, not the regex word boundary metacharacter. Every abbreviation expansion silently produces zero matches.

Also broken: Devanagari detection uses `"[\\u0900-\\u097F]"` which won't match any Hindi character (should be `r"[\u0900-\u097F]"`).

---

### 🟠 BUG-007: requirements.txt Missing 5 Critical Packages

**File:** `backend/requirements.txt`

| Package | Status | Used In |
|---|---|---|
| `supabase` | ❌ Missing | main.py, routers/documents.py |
| `spacy` | ❌ Missing | nlp_pipe/extraction_pipeline.py, nlp_preprocessor.py |
| `medspacy` | ❌ Missing | Both NLP files |
| `pdf2image` | ❌ Missing | services/pdf_parser.py (scanned fallback) |
| `google-genai` | ❌ Wrong name | Listed as `google-generativeai==0.5.4` — different SDK |
| `fhir.resources` | ❌ Missing | Needed for Python FHIR bundle building |
| `python-multipart` | ❌ Missing | Required for FastAPI file uploads |

---

### 🟠 BUG-008: FHIR Router Always Returns 503

**Files:** `routers/fhir.py` + `fhir-service/` (absent from repo)

**Problem:**
The Python FHIR router calls `check_fhir_health()` before generating bundles. The Java HAPI FHIR microservice it expects on `:8001` does not exist in the repository. Every FHIR request returns HTTP 503.

---

## 8. Medium Severity Issues

### 🟡 BUG-009: SQLAlchemy Models Defined But Never Used

**File:** `models/database.py`

Three ORM models (`DocumentRecord`, `ExtractionRecord`, `ReportRecord`) are defined and tables are created at module load. However, no router uses `get_db()`. All state is stored in in-memory dicts — lost on every server restart.

---

### 🟡 BUG-010: Gemini SDK Version Mismatch

`requirements.txt` lists `google-generativeai==0.5.4` but `services/extractor.py` uses `from google import genai` which belongs to the **separate** `google-genai` PyPI package. These are two different packages with incompatible APIs. Installing `google-generativeai` will not provide `google.genai`.

---

### 🟡 BUG-011: Test Data PDFs Not Generated or Committed

`test-data/` contains only `generate.py`. The actual PDF files referenced in the README (`discharge_complex.pdf`, `discharge_simple.pdf`, `lab_report.pdf`, `bill_undercoded.pdf`) are not in the repo. The demo cannot run without running `generate.py` first — and that step is not documented clearly.

---

### 🟡 BUG-012: ICD-10 Lookup Is Demo-Only (~90 Codes)

`data/icd10_codes.json` contains only ~90 entries. The full ICD-10 CM catalog has ~70,000 codes. The `rapidfuzz` validator can only correct Gemini outputs to codes within this tiny subset, meaning most extracted diagnoses will be matched to wrong or approximate descriptions.

---

### 🟡 BUG-013: `@app.on_event("startup")` Deprecated

FastAPI deprecated `@app.on_event("startup")` in favour of `lifespan` context managers. Non-breaking now but generates deprecation warnings in FastAPI ≥ 0.93.

---

### 🟡 BUG-014: CORS Wildcard

`allow_origins=["*"]` is acceptable for hackathon but must be locked to specific origins before any production or pilot deployment.

---

## 9. What Is Missing (Not Built)

### ❌ Web Dashboard (`web-dashboard/`)

Described in README and build prompt. Directory does not exist.

Required files:
- `index.html` — document list + upload dropzone
- `review.html` — 3-column view: original PDF | extracted entities | FHIR bundle
- `reconcile.html` — claim gap report with ₹ delta table and confidence colours
- `analytics.html` — pipeline stats and accuracy metrics
- `assets/style.css` and `assets/app.js`

---

### ❌ Android App (`android/`)

Described in README. Directory does not exist.

Required files:
- `MainActivity.java` — document list + upload trigger
- `UploadActivity.java` — file pick → upload → extract flow
- `ResultActivity.java` — entities tab + claim report tab
- `network/ApiService.java` — Retrofit2 interface

---

### ❌ FHIR Java Microservice (`fhir-service/`)

Described in README. Directory does not exist. Recommend replacing with Python `fhir.resources` to eliminate the Java dependency entirely for the hackathon.

---

### ❌ Docker Compose (`docker-compose.yml`)

Referenced in README quickstart. Not present.

---

### ❌ `.env.example`

Referenced in README. Not present. New team members and judges have no reference for required environment variables.

---

### ❌ Human Review Workflow

`HumanReview` and `CorrectionItem` schemas are defined in `schemas.py` but no endpoint (`POST /api/review/{id}`), service, or UI exists.

---

### ❌ Feedback Loop

`FeedbackItem` schema defined. No `POST /api/feedback/{id}` endpoint, no Supabase write, no analytics on correction types.

---

### ❌ Supabase Storage Download / Retrieval

`POST /api/documents` uploads to Supabase Storage but no endpoint or service method retrieves the file back for extraction.

---

### ❌ AB-PMJAY Real Claim Rate Table

`DRG_CLAIM_TABLE` in `reconciler.py` uses placeholder INR values. Real AB-PMJAY HBP 3.0 package rates by procedure/diagnosis code are not integrated.

---

## 10. What Is Strong

### ✅ Two-Layer NLP Pipeline Design

The spaCy (deterministic) → Gemini (semantic) → post-processing override architecture is sophisticated and correct. The rule that "spaCy always wins on negation" is the right safety guarantee for clinical NLP — `ConText` is a proven clinical algorithm; Gemini is probabilistic. The hard override ensures "No h/o TB" can never produce a Condition resource regardless of Gemini's interpretation.

### ✅ India-Specific Clinical Awareness

- Hinglish term mapping (Ghabrahat, ulti, bukhar, chakkar, kamzori, sans phoolna)
- Indian drug brand→INN table with 60+ entries (Voveran, Crocin, Dolo, Glycomet, Amlokind, Augmentin...)
- Indian clinical abbreviation map (c/o, h/o, k/c/o, TDS, BD, OD, Inj., T., NAD...)
- ABDM/PMJAY compliance, ABHA ID field, DPDP Act consent flag
- Rationale for not fine-tuning BioBERT on US data (MIMIC-III gives ~55% on Indian notes)

None of this comes from global templates. This domain knowledge is what will differentiate NormClaim from generic solutions.

### ✅ Reconciliation Engine Logic

Set-based ICD-10 diff (matched / missed / extra), DRG category table for ₹ estimation, specificity bonus on code length, confidence averaging, negation exclusion from delta calculation. The logic is sound and directly addresses the PS-2 revenue leakage problem.

### ✅ NORMCLAIM_CONTEXT.md

The 900-line technical context document is better than most hackathon project wikis. Division-of-labour table, concrete trace of "Pt c/o Ghabrahat ++" through both NLP layers, 6-point pre-hackathon prompt validation checklist, 19 known gotchas. Judges who read this will know this team understands the problem deeply.

### ✅ AUDIT.md (Self-Awareness)

The team wrote their own honest audit. This level of engineering maturity — knowing exactly what is broken and why — is rare in hackathon submissions and adds credibility to the project.

### ✅ Pydantic Schema Design

`ExtractionResult`, `ReconciliationReport`, `HumanReview`, `FeedbackItem`, `CorrectionItem` are all modelled correctly with `negated`, `uncertainty`, `section`, `low_confidence_flags` fields that most teams would miss or flatten.

---

## 11. Solutions — Complete Code Fixes

### FIX-001: Fix `services/extractor.py` — Remove Duplicate, Fix Imports

Delete the entire second half of the file (the `google.generativeai` / `palm.chat()` implementation). The canonical version is below.

**`backend/services/extractor.py`** — complete corrected file:

```python
import json
import os
import time
import base64
from pathlib import Path
from google import genai
from google.genai import types
from rapidfuzz import process as fuzz_process

# ── Load reference data ──────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent.parent / "data"

with open(_DATA_DIR / "icd10_codes.json") as f:
    ICD10_LOOKUP: dict[str, str] = json.load(f)

with open(_DATA_DIR / "drug_map.json") as f:
    DRUG_MAP: dict[str, str] = json.load(f)

with open(_DATA_DIR / "abbrev_map.json") as f:
    ABBREV_MAP: dict[str, str] = json.load(f)

# ── Gemini client ─────────────────────────────────────────────────────────────
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
GEMINI_MODEL = "gemini-1.5-flash"

GEMINI_SYSTEM_PROMPT = """
You are a clinical NLP engine specialised in Indian hospital documents.
The text you receive has already been pre-processed:
- Abbreviations are expanded (c/o = complaining of, etc.)
- Each sentence has a section label (complaint / history / diagnosis / medications / investigations)
- Known negated spans are listed in negated_spans[]

Your job: extract entities, map to ICD-10/LOINC/SNOMED, handle Hinglish, map
drug brand names to INN generics, and assign confidence scores.

HINGLISH TERMS (always translate):
Ghabrahat=palpitations/anxiety | ulti=vomiting | dard=pain | bukhar=fever
khasi=cough | sans phoolna=breathlessness | chakkar=dizziness
kamzori=weakness | neend na aana=insomnia

NEGATION RULES:
- Spans in negated_spans[] are CONFIRMED negated — set negated:true for any
  matching diagnosis.
- Also catch: "patient denies X", "X excluded", "X not consistent with findings"

UNCERTAINTY:
- "? X" / "possible X" / "query X" → uncertainty: "query"
- "probable X" / "likely X" → uncertainty: "possible"
- Default → uncertainty: "confirmed"

SECTION RULES:
- "history" section → past history (include, mark section:"history")
- "diagnosis" section → current active diagnosis
- "complaint" section → presenting symptoms
- "family h/o X" → DO NOT include as patient diagnosis

DRUG NAME MAPPING: Map Indian brand names to generic INN equivalents.
Examples: Voveran→Diclofenac, Crocin/Dolo→Paracetamol, Augmentin→Amoxicillin+Clavulanate,
Pantop→Pantoprazole, Rantac→Ranitidine, Zifi→Cefixime, Taxim→Cefotaxime,
Metpure→Metoprolol, Telma→Telmisartan, Glycomet→Metformin, Amlokind→Amlodipine,
Mox/Novamox→Amoxicillin

STRICT RULES:
1. Return ONLY valid JSON. No preamble, no markdown, no explanation.
2. Extract EVERY diagnosis including secondary and comorbidities.
3. Negated diagnoses must NOT appear in billed_codes.
4. icd10_code: best ICD-10 match. Include icd10_system and icd10_display.
5. confidence = certainty the ICD-10 code is correct (0.0–1.0).
6. Flag confidence < 0.6 in low_confidence_flags.

OUTPUT SCHEMA (return exactly this JSON structure):
{
  "patient": {"name":null,"age":null,"sex":null,"abha_id":null},
  "encounter": {"admit_date":null,"discharge_date":null,"ward":null,"los_days":null},
  "diagnoses": [{
    "text":"","icd10_code":"","icd10_system":"http://hl7.org/fhir/sid/icd-10",
    "icd10_display":"","is_primary":false,"confidence":0.0,
    "negated":false,"uncertainty":"confirmed","section":"diagnosis"
  }],
  "procedures": [{"text":"","date":null}],
  "medications": [{
    "brand_name":"","generic_name":"","dose":null,
    "route":null,"frequency":null,"duration":null
  }],
  "billed_codes": [],
  "detected_script": "roman",
  "low_confidence_flags": []
}
"""


def _fuzzy_validate_icd10(code: str) -> str:
    """Correct Gemini-hallucinated ICD-10 codes using local lookup."""
    code = code.upper().strip()
    if code in ICD10_LOOKUP:
        return code
    match, score, _ = fuzz_process.extractOne(code, ICD10_LOOKUP.keys())
    return match if score > 80 else code


def _parse_gemini_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON from Gemini response."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    if raw.startswith("json"):
        raw = raw[4:]
    return json.loads(raw.strip())


def _apply_negation_override(result: dict, negated_spans: list[str]) -> dict:
    """Layer 3: spaCy always wins on negation."""
    for diagnosis in result.get("diagnoses", []):
        for neg in negated_spans:
            if neg.lower() in diagnosis["text"].lower():
                diagnosis["negated"] = True
    return result


def _call_gemini_text(spacy_output: dict) -> dict:
    """Call Gemini with structured spaCy output. Retries with exponential backoff."""
    prompt = f"{GEMINI_SYSTEM_PROMPT}\n\nInput:\n{json.dumps(spacy_output, ensure_ascii=False)}"
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1),
            )
            result = _parse_gemini_json(response.text)
            # Validate and fuzzy-correct ICD-10 codes
            for dx in result.get("diagnoses", []):
                dx["icd10_code"] = _fuzzy_validate_icd10(dx.get("icd10_code", ""))
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Gemini failed after 3 retries: {e}")
            time.sleep(2 ** attempt)


def _call_gemini_image(image_b64: str, spacy_output: dict) -> dict:
    """Fallback for scanned PDFs: send page image to Gemini Vision."""
    prompt = (
        f"{GEMINI_SYSTEM_PROMPT}\n\n"
        f"Additional context from pre-processing:\n{json.dumps(spacy_output, ensure_ascii=False)}\n\n"
        "Extract all clinical information from the image."
    )
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=base64.b64decode(image_b64),
                        mime_type="image/png",
                    ),
                    prompt,
                ],
                config=types.GenerateContentConfig(temperature=0.1),
            )
            return _parse_gemini_json(response.text)
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Gemini Vision failed after 3 retries: {e}")
            time.sleep(2 ** attempt)


async def extract_from_document(
    document_id: str,
    file_bytes: bytes,
    spacy_output: dict,
    use_cache: bool = False,
) -> dict:
    """
    Full extraction pipeline:
      1. Use spaCy pre-processed output (already done by nlp_preprocessor)
      2. Call Gemini (text or vision depending on PDF type)
      3. Apply negation override
      4. Return complete ExtractionResult-compatible dict
    """
    cache_path = Path("test-data/cached_extraction.json")
    if use_cache and cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    raw_text = spacy_output.get("expanded_text", "")

    # Choose text vs vision path
    if len(raw_text.strip()) < 100:
        # Scanned PDF — use Gemini Vision
        from .pdf_parser import pdf_to_base64_image
        image_b64 = pdf_to_base64_image(file_bytes)
        result = _call_gemini_image(image_b64, spacy_output)
    else:
        result = _call_gemini_text(spacy_output)

    # Apply negation override (spaCy wins)
    result = _apply_negation_override(result, spacy_output.get("negated_spans", []))

    # Attach spaCy metadata
    result["document_id"] = document_id
    result["section_map"] = spacy_output.get("section_map", {})
    result["negated_spans"] = spacy_output.get("negated_spans", [])

    return result
```

---

### FIX-002: Fix `routers/extract.py` — Wire the Real Pipeline

**`backend/routers/extract.py`** — complete corrected file:

```python
import io
from fastapi import APIRouter, HTTPException
from ..models.schemas import ExtractionResult
from ..models.database import get_document_bytes, save_extraction
from ..services.nlp_preprocessor import preprocess
from ..services.extractor import extract_from_document
import os

router = APIRouter()


@router.post("/api/extract/{document_id}", response_model=ExtractionResult)
async def run_extraction(document_id: str):
    # 1. Retrieve PDF bytes from storage
    file_bytes = get_document_bytes(document_id)
    if file_bytes is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    # 2. Extract text from PDF (pdfplumber)
    from ..services.pdf_parser import extract_text_from_pdf
    raw_text = extract_text_from_pdf(file_bytes)

    # 3. Layer 1: spaCy pre-processing
    spacy_output = preprocess(raw_text)

    # 4. Layer 2 + 3: Gemini extraction + negation override
    use_cache = os.getenv("USE_DEMO_CACHE", "false").lower() == "true"
    result = await extract_from_document(
        document_id=document_id,
        file_bytes=file_bytes,
        spacy_output=spacy_output,
        use_cache=use_cache,
    )

    # 5. Persist extraction result
    save_extraction(document_id, result)

    return ExtractionResult(**result)


@router.get("/api/extract/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    from ..models.database import get_extraction
    result = get_extraction(document_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Extraction not found. Run POST first.")
    return ExtractionResult(**result)
```

---

### FIX-003: Fix Document Storage — Unified SQLite Backend

Replace the broken in-memory dict + Supabase split with a single SQLite source of truth for local/demo use. Supabase remains as an optional production layer.

**`backend/models/database.py`** — complete corrected file:

```python
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

DB_PATH = Path("normclaim.db")


def _init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_bytes BLOB NOT NULL,
                uploaded_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'uploaded',
                consent_obtained INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS extractions (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT REFERENCES documents(id),
                result_json TEXT,
                extracted_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS fhir_bundles (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT REFERENCES documents(id),
                bundle_json TEXT,
                generated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS reconciliations (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT REFERENCES documents(id),
                report_json TEXT,
                delta_inr REAL,
                reconciled_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS human_reviews (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT REFERENCES documents(id),
                reviewer_notes TEXT,
                corrections_json TEXT,
                reviewed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                document_id TEXT REFERENCES documents(id),
                was_correct INTEGER,
                correction_type TEXT,
                details TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)

@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

_init_db()


# ── Documents ──────────────────────────────────────────────────────────────────

def save_document(document_id: str, filename: str, file_bytes: bytes) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO documents (id, filename, file_bytes) VALUES (?, ?, ?)",
            (document_id, filename, file_bytes),
        )


def get_document_bytes(document_id: str) -> Optional[bytes]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT file_bytes FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    return bytes(row["file_bytes"]) if row else None


def list_documents() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, uploaded_at, status FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_document_status(document_id: str, status: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE documents SET status=? WHERE id=?", (status, document_id))


# ── Extractions ────────────────────────────────────────────────────────────────

def save_extraction(document_id: str, result: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO extractions (document_id, result_json) VALUES (?, ?)",
            (document_id, json.dumps(result)),
        )
    update_document_status(document_id, "extracted")


def get_extraction(document_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT result_json FROM extractions WHERE document_id=? ORDER BY extracted_at DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    return json.loads(row["result_json"]) if row else None


# ── FHIR Bundles ───────────────────────────────────────────────────────────────

def save_fhir_bundle(document_id: str, bundle: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO fhir_bundles (document_id, bundle_json) VALUES (?, ?)",
            (document_id, json.dumps(bundle)),
        )
    update_document_status(document_id, "fhir_generated")


def get_fhir_bundle(document_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT bundle_json FROM fhir_bundles WHERE document_id=? ORDER BY generated_at DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    return json.loads(row["bundle_json"]) if row else None


# ── Reconciliations ────────────────────────────────────────────────────────────

def save_reconciliation(document_id: str, report: dict, delta_inr: float) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO reconciliations (document_id, report_json, delta_inr) VALUES (?, ?, ?)",
            (document_id, json.dumps(report), delta_inr),
        )
    update_document_status(document_id, "reconciled")


def get_reconciliation(document_id: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT report_json FROM reconciliations WHERE document_id=? ORDER BY reconciled_at DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    return json.loads(row["report_json"]) if row else None
```

---

### FIX-004: Fix `services/nlp_preprocessor.py` — JSON Loads + Regex

**`backend/services/nlp_preprocessor.py`** — critical fixes:

```python
import re
import json
import spacy
import medspacy
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"

# FIX: Load JSON files correctly — NOT as Python module imports
with open(_DATA_DIR / "abbrev_map.json") as f:
    ABBREV_MAP: dict[str, str] = json.load(f)

with open(_DATA_DIR / "drug_map.json") as f:
    DRUG_MAP: dict[str, str] = json.load(f)

# Load spaCy + medspaCy ConText
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe("medspacy_context")

SECTION_KEYWORDS = {
    "complaint":      ["c/o", "complaining of", "presenting complaint", "chief complaint"],
    "history":        ["h/o", "history of", "k/c/o", "known case of", "past history", "past h/o"],
    "diagnosis":      ["diagnosis", "d/c dx", "discharge diagnosis", "impression", "final diagnosis"],
    "medications":    ["rx", "medications", "prescription", "drugs", "treatment"],
    "investigations": ["investigations", "lab", "laboratory", "reports", "test results", "usgs"],
    "examination":    ["o/e", "on examination", "general examination", "vitals"],
    "advice":         ["adv", "advice", "follow up", "review"],
}


def expand_abbreviations(text: str) -> str:
    """
    FIX: Correct regex — use r"\b" not r"\\b" for word boundaries.
    Process longest abbreviations first to avoid partial matches.
    """
    sorted_abbrevs = sorted(ABBREV_MAP.keys(), key=len, reverse=True)
    for abbr in sorted_abbrevs:
        # FIX: r"\b" is the correct word boundary; r"\\b" is a literal backslash+b
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        text = pattern.sub(ABBREV_MAP[abbr], text)
    return text


def detect_sections(doc) -> dict:
    """Classify each sentence into a section based on keyword matching."""
    section_map = {}
    for i, sent in enumerate(doc.sents):
        sent_lower = sent.text.lower()
        assigned = "unknown"
        for section, keywords in SECTION_KEYWORDS.items():
            if any(kw in sent_lower for kw in keywords):
                assigned = section
                break
        section_map[str(i)] = assigned
    return section_map


def detect_script(text: str) -> str:
    """
    FIX: Correct Unicode range pattern — r"[\u0900-\u097F]" not r"[\\u0900-\\u097F]"
    """
    # FIX: Direct Unicode character class — no escaping needed in character class
    devanagari_pattern = re.compile("[\u0900-\u097F]")
    has_devanagari = bool(devanagari_pattern.search(text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    if has_devanagari and has_latin:
        return "mixed"
    elif has_devanagari:
        return "devanagari"
    return "roman"


def preprocess(raw_text: str) -> dict:
    """
    Full spaCy pre-processing pipeline.
    Returns structured dict for Gemini Layer 2.
    """
    # Step 1: Abbreviation expansion
    expanded = expand_abbreviations(raw_text)

    # Step 2: Parse with spaCy + medspaCy
    doc = nlp(expanded)

    # Step 3: Section detection
    section_map = detect_sections(doc)

    # Step 4: Negation detection via medspaCy ConText
    negated_spans = []
    for ent in doc.ents:
        if hasattr(ent._, "is_negated") and ent._.is_negated:
            negated_spans.append(ent.text)

    # Supplement with regex patterns for Indian clinical shorthand
    negation_patterns = [
        r"no\s+(?:h/o|history\s+of|h\.o\.)\s+(\w[\w\s]*?)(?:\.|,|;|$)",
        r"not\s+a\s+(?:k/c/o|known\s+case\s+of)\s+(\w[\w\s]*?)(?:\.|,|;|$)",
        r"ruled\s+out\s+(\w[\w\s]*?)(?:\.|,|;|$)",
        r"no\s+evidence\s+of\s+(\w[\w\s]*?)(?:\.|,|;|$)",
        r"(\w[\w\s]*?)\s+not\s+present",
    ]
    for pattern in negation_patterns:
        for match in re.finditer(pattern, expanded, re.IGNORECASE):
            span = match.group(1).strip()
            if span and span not in negated_spans:
                negated_spans.append(span)

    # Step 5: Script detection
    detected_script = detect_script(raw_text)

    return {
        "expanded_text": expanded,
        "section_map": section_map,
        "negated_spans": negated_spans,
        "detected_script": detected_script,
    }
```

---

### FIX-005: Fix `main.py` — Make Supabase Optional

```python
# backend/main.py — Supabase startup fix

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import documents, extract, fhir, reconcile

logger = logging.getLogger("normclaim")

app = FastAPI(
    title="NormClaim API",
    description="AI-Powered Clinical & Administrative Data Normalization Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # FIX: Lock down origins in production — wildcard acceptable for hackathon only
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(extract.router)
app.include_router(fhir.router)
app.include_router(reconcile.router)


@app.on_event("startup")
async def startup():
    logger.info("NormClaim backend starting up...")

    # FIX: Supabase is OPTIONAL — warn, don't crash
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.warning(
            "SUPABASE_URL / SUPABASE_KEY not set. "
            "Running in local SQLite mode. Set these for production Supabase storage."
        )
    else:
        logger.info("Supabase credentials found — production storage enabled.")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.error(
            "GEMINI_API_KEY not set. AI extraction will fail. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    else:
        logger.info("Gemini API key found.")

    logger.info("NormClaim ready. Docs at http://localhost:8000/docs")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
```

---

### FIX-006: Replace Java FHIR Service with Python (`fhir.resources`)

Eliminate the Java dependency entirely. Build the FHIR R4 Bundle directly in Python.

**`backend/services/fhir_builder.py`** — new file:

```python
"""
Build ABDM-compliant FHIR R4 Bundles from ExtractionResult using fhir.resources.
Replaces the Java HAPI FHIR microservice entirely.
pip install fhir.resources
"""
import uuid
from datetime import datetime
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.claim import Claim, ClaimDiagnosis
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.humanname import HumanName
from fhir.resources.period import Period


ABDM_BUNDLE_PROFILE = (
    "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"
)


def _coding(system: str, code: str, display: str) -> Coding:
    return Coding(system=system, code=code, display=display)


def _codeable(system: str, code: str, display: str, text: str) -> CodeableConcept:
    """Always include code, system, display, and text per ABDM requirement."""
    return CodeableConcept(
        coding=[_coding(system, code, display)],
        text=text,
    )


def build_fhir_bundle(extraction: dict) -> dict:
    """
    Build a full ABDM-compliant FHIR R4 Bundle from extraction result.
    Only NON-NEGATED diagnoses become Condition resources or appear in Claim.
    """
    patient_id = str(uuid.uuid4())
    encounter_id = str(uuid.uuid4())
    entries = []

    # ── Patient ───────────────────────────────────────────────────────────────
    pt_info = extraction.get("patient", {})
    patient = Patient(
        id=patient_id,
        meta={"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"]},
        name=[HumanName(text=pt_info.get("name") or "Unknown")],
        gender=pt_info.get("sex", "unknown").lower() if pt_info.get("sex") else "unknown",
    )
    if pt_info.get("abha_id"):
        patient.identifier = [{"system": "https://healthid.ndhm.gov.in", "value": pt_info["abha_id"]}]
    entries.append(BundleEntry(resource=patient, fullUrl=f"urn:uuid:{patient_id}"))

    # ── Encounter ─────────────────────────────────────────────────────────────
    enc_info = extraction.get("encounter", {})
    encounter = Encounter(
        id=encounter_id,
        meta={"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Encounter"]},
        status="finished",
        class_fhir=_coding("http://terminology.hl7.org/CodeSystem/v3-ActCode", "IMP", "inpatient encounter"),
        subject=Reference(reference=f"urn:uuid:{patient_id}"),
    )
    if enc_info.get("admit_date") or enc_info.get("discharge_date"):
        encounter.period = Period(
            start=enc_info.get("admit_date"),
            end=enc_info.get("discharge_date"),
        )
    entries.append(BundleEntry(resource=encounter, fullUrl=f"urn:uuid:{encounter_id}"))

    # ── Conditions (non-negated diagnoses only) ───────────────────────────────
    condition_refs = []
    diagnoses = [d for d in extraction.get("diagnoses", []) if not d.get("negated", False)]

    for dx in diagnoses:
        cond_id = str(uuid.uuid4())
        condition = Condition(
            id=cond_id,
            meta={"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Condition"]},
            subject=Reference(reference=f"urn:uuid:{patient_id}"),
            encounter=Reference(reference=f"urn:uuid:{encounter_id}"),
            code=_codeable(
                system=dx.get("icd10_system", "http://hl7.org/fhir/sid/icd-10"),
                code=dx.get("icd10_code", ""),
                display=dx.get("icd10_display", dx.get("text", "")),
                text=dx.get("text", ""),
            ),
            clinicalStatus=_codeable(
                system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                code="active",
                display="Active",
                text="Active",
            ),
            verificationStatus=_codeable(
                system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                code="confirmed" if dx.get("uncertainty") == "confirmed" else "provisional",
                display="Confirmed" if dx.get("uncertainty") == "confirmed" else "Provisional",
                text=dx.get("uncertainty", "confirmed").capitalize(),
            ),
        )
        entries.append(BundleEntry(resource=condition, fullUrl=f"urn:uuid:{cond_id}"))
        condition_refs.append(Reference(reference=f"urn:uuid:{cond_id}"))

    # ── MedicationRequests ────────────────────────────────────────────────────
    for med in extraction.get("medications", []):
        med_id = str(uuid.uuid4())
        med_name = med.get("generic_name") or med.get("brand_name") or "Unknown medication"
        mr = MedicationRequest(
            id=med_id,
            meta={"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/MedicationRequest"]},
            status="active",
            intent="order",
            subject=Reference(reference=f"urn:uuid:{patient_id}"),
            encounter=Reference(reference=f"urn:uuid:{encounter_id}"),
            medicationCodeableConcept=CodeableConcept(text=med_name),
        )
        entries.append(BundleEntry(resource=mr, fullUrl=f"urn:uuid:{med_id}"))

    # ── Claim (non-negated diagnoses only) ────────────────────────────────────
    claim_id = str(uuid.uuid4())
    claim_diagnoses = [
        ClaimDiagnosis(
            sequence=i + 1,
            diagnosisCodeableConcept=_codeable(
                system=dx.get("icd10_system", "http://hl7.org/fhir/sid/icd-10"),
                code=dx.get("icd10_code", ""),
                display=dx.get("icd10_display", dx.get("text", "")),
                text=dx.get("text", ""),
            ),
        )
        for i, dx in enumerate(diagnoses)
    ]
    claim = Claim(
        id=claim_id,
        meta={"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim"]},
        status="active",
        use="claim",
        patient=Reference(reference=f"urn:uuid:{patient_id}"),
        created=datetime.utcnow().strftime("%Y-%m-%d"),
        insurer={"display": "AB-PMJAY / TPA"},
        provider={"display": "Hospital"},
        priority=_codeable("http://terminology.hl7.org/CodeSystem/processpriority", "normal", "Normal", "Normal"),
        diagnosis=claim_diagnoses if claim_diagnoses else None,
    )
    entries.append(BundleEntry(resource=claim, fullUrl=f"urn:uuid:{claim_id}"))

    # ── Bundle ────────────────────────────────────────────────────────────────
    bundle = Bundle(
        id=str(uuid.uuid4()),
        meta={"profile": [ABDM_BUNDLE_PROFILE]},
        type="document",
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        entry=entries,
    )

    return bundle.dict()
```

**Update `routers/fhir.py`** to use the Python builder:

```python
# backend/routers/fhir.py
from fastapi import APIRouter, HTTPException
from ..models.database import get_extraction, save_fhir_bundle, get_fhir_bundle
from ..services.fhir_builder import build_fhir_bundle

router = APIRouter()


@router.post("/api/fhir/{document_id}")
async def generate_fhir(document_id: str):
    extraction = get_extraction(document_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Run extraction first.")
    bundle = build_fhir_bundle(extraction)
    save_fhir_bundle(document_id, bundle)
    return bundle


@router.get("/api/fhir/{document_id}")
async def get_fhir(document_id: str):
    bundle = get_fhir_bundle(document_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="FHIR bundle not found. Run POST first.")
    return bundle
```

---

### FIX-007: Correct `requirements.txt`

```
# backend/requirements.txt — corrected

fastapi
uvicorn[standard]
pdfplumber
Pillow
pdf2image

# FIX: Use google-genai (new SDK), NOT google-generativeai (old SDK)
google-genai

# FIX: Add all missing packages
spacy
medspacy
supabase==2.4.0

rapidfuzz
python-dotenv==1.0.1
httpx
sqlalchemy

# FIX: Python FHIR library — replaces Java HAPI FHIR microservice
fhir.resources

# FIX: Required for FastAPI file upload endpoints
python-multipart
```

---

### FIX-008: Add `.env.example`

```bash
# .env.example — copy to .env and fill in your values

# Required — get free key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — Supabase for production storage (SQLite used if not set)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Backend URL (for web dashboard fetch() calls)
BACKEND_URL=http://localhost:8000

# Set to true on demo day if Gemini API is unreachable
USE_DEMO_CACHE=false
```

---

### FIX-009: Generate and Commit Test PDFs

Run this before the hackathon and commit the generated PDFs:

```bash
cd test-data
pip install reportlab
python generate.py
# Commits: discharge_complex.pdf, discharge_simple.pdf, lab_report.pdf, bill_undercoded.pdf
git add *.pdf
git commit -m "chore: add synthetic test PDFs for demo"
```

Also pre-generate and commit the demo cache:

```bash
cd backend
GEMINI_API_KEY=your_key python -c "
import asyncio, json
from services.nlp_preprocessor import preprocess
from services.extractor import extract_from_document
from services.pdf_parser import extract_text_from_pdf

with open('../test-data/discharge_complex.pdf', 'rb') as f:
    file_bytes = f.read()

raw_text = extract_text_from_pdf(file_bytes)
spacy_output = preprocess(raw_text)
result = asyncio.run(extract_from_document('demo', file_bytes, spacy_output))

with open('../test-data/cached_extraction.json', 'w') as f:
    json.dump(result, f, indent=2)
print('Cache written.')
"
```

---

### FIX-010: Add `docker-compose.yml`

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL:-}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY:-}
      - USE_DEMO_CACHE=${USE_DEMO_CACHE:-false}
      - BACKEND_URL=http://localhost:8000
    volumes:
      - ./backend:/app
      - ./test-data:/app/test-data
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  dashboard:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./web-dashboard:/app
    ports:
      - "3000:3000"
    command: python -m http.server 3000
```

**`backend/Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 12. Pre-Hackathon Fix Priority Order

Execute these in order. After each step, verify the fix works before moving on.

| # | Fix | File(s) | Time Est. | Unblocks |
|---|---|---|---|---|
| 1 | Delete second half of extractor.py; fix absolute import | `services/extractor.py` | 15 min | App starts |
| 2 | Fix routers/extract.py — call real extractor, fix PDF decode | `routers/extract.py` | 30 min | AI extraction |
| 3 | Replace in-memory dict with SQLite (database.py rewrite) | `models/database.py` | 45 min | 404 on extract |
| 4 | Make Supabase optional in main.py | `main.py` | 10 min | App starts locally |
| 5 | Fix nlp_preprocessor.py — json.load, regex backslash, Unicode | `services/nlp_preprocessor.py` | 20 min | spaCy pipeline |
| 6 | Fix requirements.txt — google-genai, missing packages | `requirements.txt` | 5 min | pip install |
| 7 | Add .env.example | `.env.example` | 5 min | Fresh clone works |
| 8 | Add fhir_builder.py; update fhir router | `services/fhir_builder.py`, `routers/fhir.py` | 60 min | FHIR layer |
| 9 | Generate + commit test PDFs + demo cache | `test-data/` | 20 min | Offline demo |
| 10 | Add docker-compose.yml + Dockerfile | Root + `backend/` | 20 min | One-command start |
| 11 | Build web-dashboard/ (3 HTML pages) | `web-dashboard/` | 3–4 hrs | Demo face |
| 12 | Run pre-hackathon checklist (6 checks in NORMCLAIM_CONTEXT.md) | All | 30 min | Confidence |

---

## 13. Post-Hackathon Roadmap

### Phase 2 — Pilot (3 months)
- Deploy at 2–3 SME hospitals in Tier 2 cities
- Test with real discharge summaries from partner hospitals
- Measure actual ₹ recovered per hospital per month
- Add Hindi document support via Gemini multimodal
- Integrate real AB-PMJAY HBP 3.0 package rates for accurate ₹ delta
- Expand ICD-10 lookup to full CMS.gov dataset (~70,000 codes)

### Phase 3 — Product (6–12 months)
- ABDM sandbox API certification
- SaaS pricing: ₹5,000–15,000 per hospital per month
- TPA and insurer API direct integrations (Medi Assist, Paramount, Star Health)
- Batch processing for historical document backfill
- PostgreSQL + S3 for production storage
- Fine-tune BioBERT/PubMedBERT on annotated Indian clinical notes (5,000+ documents from pilot hospitals)
- ABHA ID validation via ABDM sandbox API
- Android app for billing clerk workflow
- Human review + correction workflow with full audit trail
- Active learning feedback loop: correction type tracking → prompt engineering improvements

---

*NormClaim — Every diagnosis. Every rupee.*
*Team Kaizen Unit · Madhav Institute of Technology and Science, Gwalior*
*Jilo Health Hackathon × NJACK IIT Patna · PS-2*
