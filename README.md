# NormClaim

> **Every diagnosis. Every rupee.**

AI-Powered Clinical & Administrative Data Normalization Engine for Indian SME hospitals.

Built by **Team Kaizen Unit** for the [Jilo Health Hackathon × NJACK IIT Patna](https://hackathon.jilohealth.com) — Problem Statement PS-2.

---

## The Problem

Indian SME hospitals lose ₹12,000–40,000 per patient discharge in unclaimed diagnoses — not because the doctor didn't treat the conditions, but because billing clerks manually transcribe ICD-10 codes from discharge summaries and routinely miss comorbidities and secondary diagnoses. There is no intelligent normalization layer between clinical documents and payer claim fields.

**68%** of SME hospitals under-code claims due to manual entry. From 2026, all AB-PMJAY empanelled hospitals must also be ABDM-FHIR R4 compliant — a mandate that makes this problem simultaneously a revenue and compliance crisis.

---

## What NormClaim Does

```
PDF (discharge summary / lab report / bill)
        ↓
  AI Extraction  →  FHIR R4 Bundle  →  Claim Gap Report + ₹ Delta
```

1. **Ingest** — Upload any hospital document (PDF or scanned image); consent is captured at upload time
2. **Extract** — Gemini AI reads the document and returns structured JSON: patient, diagnoses with ICD-10 codes, procedures, medications, billed codes
3. **Map** — HAPI FHIR Java service builds a valid ABDM-compliant FHIR R4 Bundle
4. **Reconcile** — ICD-10 diff engine compares extracted diagnoses against billed codes, surfaces missed diagnoses and estimates the ₹ claim delta
5. **Manage** — Full claim lifecycle management: pre-auth, discharge processing, settlement, and finance reconciliation — all behind role-based access control

---

## Team Kaizen Unit

| Name | Role | College |
|------|------|---------|
| **Naitik Kanha** | Team Leader | Madhav Institute of Technology and Science, Gwalior |
| Sambhav Raj Onkar | Member | Madhav Institute of Technology and Science, Gwalior |
| Pratik Harsude | Member | Madhav Institute of Technology and Science, Gwalior |
| Pralakshy Kaushik | Member | Madhav Institute of Technology and Science, Gwalior |

---

## Repository Structure

```
NormClaim1.0/
├── backend/                        # FastAPI orchestration service (Python 3.11)
│   ├── main.py                     # App entry point + router registration
│   ├── routers/                    # One file per API domain
│   │   ├── documents.py            # POST /api/documents  (upload with consent)
│   │   ├── extract.py              # POST /api/extract/{id}
│   │   ├── fhir.py                 # POST /api/fhir/{id}
│   │   ├── reconcile.py            # POST /api/reconcile/{id}
│   │   ├── claims.py               # GET/POST/PATCH /api/claims (lifecycle)
│   │   ├── auth.py                 # GET /api/auth/session
│   │   ├── notifications.py        # WebSocket + REST notifications
│   │   ├── discharge.py            # Discharge processing endpoints
│   │   ├── enhancement.py          # AI-powered claim enhancement
│   │   ├── settlement.py           # Settlement processing
│   │   ├── finance.py              # Finance reconciliation
│   │   ├── analytics.py            # Dashboard analytics
│   │   ├── review.py               # Human-in-the-loop review
│   │   ├── feedback.py             # Extraction feedback loop
│   │   ├── validate.py             # Pre-submission validation
│   │   └── config.py               # Public runtime config
│   ├── Extraction_pipeline/        # Pre-auth + ABHA extraction module
│   │   ├── extraction_pipeline.py  # Gemini-powered clinical entity extraction
│   │   ├── abha_lookup.py          # ABHA ID lookup helpers
│   │   ├── pre_auth_filling.py     # Pre-authorization form auto-fill
│   │   ├── text_features.py        # NLP feature engineering
│   │   └── router.py               # POST /api/preauth/…
│   ├── services/                   # Business logic layer
│   │   ├── extractor.py            # Gemini API + pdfplumber pipeline
│   │   ├── fhir_client.py          # HTTP client → Java FHIR service
│   │   ├── fhir_mapper.py          # FHIR resource builder helpers
│   │   ├── reconciler.py           # ICD-10 diff + ₹ delta engine
│   │   ├── pdf_parser.py           # Text + image extraction from PDFs
│   │   ├── nlp_preprocessor.py     # spaCy / medspaCy pre-processing
│   │   ├── claim_structuring.py    # Claim structuring & normalization
│   │   ├── validation_service.py   # Claim validation rules
│   │   ├── discharge_service.py    # Discharge document processing
│   │   ├── enhancement_service.py  # AI claim enhancement
│   │   ├── settlement_parser.py    # Settlement document parsing
│   │   ├── finance_reconciler.py   # Finance reconciliation logic
│   │   ├── analytics_service.py    # KPI + trend calculations
│   │   ├── review_service.py       # Review workflow helpers
│   │   ├── feedback_service.py     # Feedback storage & retrieval
│   │   ├── persistence.py          # In-memory cache bootstrap
│   │   └── auth.py                 # Supabase JWT verification
│   ├── models/
│   │   ├── schemas.py              # Pydantic models (all I/O types)
│   │   └── database.py             # SQLAlchemy ORM + Supabase setup
│   ├── data/
│   │   ├── icd10_codes.json        # Local ICD-10 lookup (offline)
│   │   ├── drug_map.json           # Drug name → code mapping
│   │   └── abbrev_map.json         # Clinical abbreviation expansion
│   ├── sql/
│   │   ├── normclaim_full_schema.sql   # Full Supabase PostgreSQL schema
│   │   └── seed_auth_users_dummy.sql   # Seed data for local dev
│   ├── Dockerfile
│   └── requirements.txt
│
├── fhir-service/                   # HAPI FHIR Java Spring Boot microservice
│   ├── pom.xml
│   └── Dockerfile
│
├── android/                        # Android app (Java)
│   └── app/
│
├── web-dashboard/                  # React + TypeScript + Vite SPA
│   ├── index.html                  # App shell
│   ├── app.html                    # Alternative static entry
│   ├── src/                        # Vite-compiled React components
│   ├── authentication/             # Auth components & Supabase hooks
│   │   ├── AuthDialog.tsx          # Login / sign-up modal
│   │   ├── RoleGuard.tsx           # Role-based route guard
│   │   ├── NotificationBell.tsx    # Real-time notification bell
│   │   ├── StageProgressBar.tsx    # Claim stage visualisation
│   │   └── authStore.ts            # Zustand auth state
│   ├── js/                         # Vanilla-JS modules (legacy dashboard)
│   │   ├── api.js                  # Backend API client
│   │   ├── auth.js                 # Supabase auth helpers
│   │   └── notifications.js        # WebSocket notification client
│   └── assets/                     # CSS + component bundles
│
├── test-data/                      # Synthetic test documents
│   ├── generate.py                 # Script to generate all PDFs
│   ├── discharge_complex.pdf       # 4 diagnoses, 1 billed — main demo doc
│   ├── discharge_simple.pdf        # Correctly coded — delta = ₹0
│   ├── lab_report.pdf              # 8 lab values → FHIR Observations
│   └── bill_undercoded.pdf         # Bill showing only J18.9
│
├── scripts/
│   └── smoke_api.sh                # End-to-end API smoke test
│
├── docker-compose.yml
└── README.md
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                           Frontend                               │
│  Android App (Java)        Web Dashboard (React / Vite / TS)     │
│  Retrofit2 API client      Supabase Auth + WebSocket notifs      │
└──────────┬─────────────────────────────────┬─────────────────────┘
           │ HTTP (Bearer JWT)                │ HTTP / WS
           ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                  FastAPI Backend  :8000  (Python 3.11)           │
│                                                                  │
│  /api/documents   upload (consent flag, multipart PDF)          │
│  /api/extract     Gemini AI → structured clinical JSON           │
│  /api/fhir        proxy → HAPI FHIR Java service                │
│  /api/reconcile   ICD-10 diff + ₹ claim delta                   │
│  /api/claims      claim lifecycle (create/read/status)           │
│  /api/preauth     pre-auth form auto-fill (ABHA lookup)           │
│  /api/discharge   discharge processing pipeline                  │
│  /api/enhancement AI claim enhancement                           │
│  /api/settlement  settlement parsing & confirmation              │
│  /api/finance     finance reconciliation & reporting             │
│  /api/analytics   KPIs, trends, dashboard metrics               │
│  /api/auth        Supabase session validation                    │
│  /ws/notifications  WebSocket real-time notifications            │
└────┬──────────────────────┬─────────────────────┬───────────────┘
     │ google-genai          │ httpx                │ supabase-py
     ▼                       ▼                      ▼
┌──────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│ Gemini AI    │   │ HAPI FHIR  :8001     │   │ Supabase         │
│ (multimodal) │   │ (Java Spring Boot)   │   │ (PostgreSQL +    │
│              │   │ POST /fhir/bundle    │   │  Auth + RLS)     │
└──────────────┘   └──────────────────────┘   └──────────────────┘
```

### User Roles

| Role | Description | Key Permissions |
|------|-------------|----------------|
| `HOSPITAL` | Hospital billing clerk / RCM team | Upload documents, trigger extraction, review claims |
| `TPA` | Third-party administrator officer | Review & approve/reject pre-auth requests |
| `FINANCE` | Finance / settlement team | Access settlement and finance reconciliation reports |

### FHIR Resources Generated

| Resource | Source | ABDM Profile |
|----------|--------|--------------|
| `Patient` | Discharge summary header | AbdmPatient |
| `Encounter` | Admission / discharge dates | AbdmEncounter |
| `Condition` | Diagnoses → ICD-10 coded | AbdmCondition |
| `Observation` | Lab report values → LOINC | AbdmObservation |
| `MedicationRequest` | Discharge medications | AbdmMedicationRequest |
| `Procedure` | Surgical / diagnostic procedures | AbdmProcedure |
| `Claim` | Bill / claim document | AbdmClaim |
| `Bundle` | Wraps all resources | AbdmDocumentBundle |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | FastAPI · Python 3.11 | Async REST, auto OpenAPI docs |
| AI Extraction | Gemini AI + pdfplumber + PyMuPDF | Multimodal (text + scanned images) |
| NLP | spaCy 3.7 · medspaCy · rapidfuzz | Clinical NER, fuzzy ICD-10 correction |
| FHIR Mapping | HAPI FHIR R4 · Spring Boot (Java 17) | ABDM-compliant R4 Bundle validation |
| Auth & Database | Supabase (PostgreSQL + Auth + RLS) | JWT auth, row-level security per role |
| Web Frontend | React 19 · TypeScript · Vite · Tailwind CSS | Role-aware SPA with real-time notifications |
| Android App | Java · Retrofit2 | Mobile upload & claim review |
| Real-time | WebSocket (FastAPI) | Live claim status & notification push |
| Storage | Supabase PostgreSQL (dev & prod) | SQLAlchemy ORM + direct Supabase client |
| Containerization | Docker · Docker Compose | One-command local stack |

---

## Quickstart

### Prerequisites

- Python 3.11+
- Java 17+ and Maven 3.8+
- Node.js 18+ (for the web dashboard)
- Android Studio (optional, for the Android app)
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier: 1,500 req/day)
- A [Supabase](https://supabase.com) project (free tier available)

### 1. Clone & configure

```bash
git clone https://github.com/jhkaizenunit2026/NormClaim1.0.git
cd NormClaim1.0
```

Create a `.env` file in the project root with the following variables:

```bash
# Gemini AI — https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Supabase — https://app.supabase.com/project/_/settings/api
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Service URLs (defaults work with Docker Compose)
FHIR_SERVICE_URL=http://localhost:8001/fhir/bundle
BACKEND_URL=http://localhost:8000

# Optional: comma-separated extra CORS origins
# CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Apply the database schema to your Supabase project:

```bash
# In Supabase Dashboard → SQL Editor, run:
backend/sql/normclaim_full_schema.sql
```

### 2. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

Services will be available at:
- Backend API: `http://localhost:8000`
- FHIR Service: `http://localhost:8001`
- API Docs (Swagger): `http://localhost:8000/docs`

### 3. Run manually

**Backend (Python):**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**FHIR Service (Java):**
```bash
cd fhir-service
mvn spring-boot:run
# Starts on port 8001
```

**Web Dashboard (React/Vite):**
```bash
cd web-dashboard
cp authentication/.env.example .env.local
# Fill in Supabase values in .env.local
npm install
npm run dev
# Opens at http://localhost:5173
```

**Android App:**
```
Open android/ in Android Studio
Set BASE_URL in app/build.gradle to your machine's IP (or http://10.0.2.2:8000 for emulator)
Run on emulator or physical device
```

### 4. Generate test data

```bash
pip install reportlab
python test-data/generate.py
# Creates 4 synthetic PDFs in test-data/
```

### 5. Smoke test the API

```bash
# Requires a valid Supabase access token
ACCESS_TOKEN=your_jwt_token ./scripts/smoke_api.sh test-data/discharge_simple.pdf
```

---

## API Reference

All endpoints require a Supabase JWT in the `Authorization: Bearer <token>` header unless noted otherwise.
Full interactive documentation is available at `http://localhost:8000/docs` (Swagger UI).

### Health check (no auth required)
```http
GET /health

→ { "status": "ok", "service": "normclaim-backend", "version": "1.0.0", ... }
```

### Upload a document
```http
POST /api/documents
Content-Type: multipart/form-data

file: <PDF file>
consent_obtained: true

→ { "document_id": "uuid", "filename": "...", "status": "uploaded" }
```

### Run AI extraction
```http
POST /api/extract/{document_id}

→ {
    "document_id": "uuid",
    "patient": { "name": "Rajesh Kumar", "age": 58, "sex": "M", "abha_id": null },
    "encounter": { "admit_date": "2026-03-10", "discharge_date": "2026-03-14" },
    "diagnoses": [
      { "text": "Pneumonia", "icd10_code": "J18.9", "is_primary": true, "confidence": 0.95 },
      { "text": "Type 2 Diabetes", "icd10_code": "E11.9", "is_primary": false, "confidence": 0.91 }
    ],
    "billed_codes": ["J18.9"],
    ...
  }
```

### Generate FHIR bundle
```http
POST /api/fhir/{document_id}

→ {
    "resourceType": "Bundle",
    "type": "document",
    "meta": { "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"] },
    "entry": [ ... Patient, Encounter, Condition, Claim resources ... ]
  }
```

### Run reconciliation
```http
POST /api/reconcile/{document_id}

→ {
    "matched": [{ "icd10_code": "J18.9", "description": "Pneumonia", "status": "matched" }],
    "missed":  [
      { "icd10_code": "E11.9", "description": "Type 2 diabetes mellitus", "status": "missed", "estimated_value_inr": 6950 },
      { "icd10_code": "I10",   "description": "Essential hypertension",   "status": "missed", "estimated_value_inr": 4150 },
      { "icd10_code": "N18.3", "description": "Chronic kidney disease",   "status": "missed", "estimated_value_inr": 6400 }
    ],
    "estimated_claim_delta_inr": 17500,
    "confidence": 0.92
  }
```

### Pre-auth pipeline
```http
POST /api/preauth/extract        # Extract clinical entities for pre-auth
POST /api/preauth/fill           # Auto-fill pre-auth form fields
GET  /api/preauth/forms          # List submitted pre-auth forms
```

### Claim lifecycle
```http
GET    /api/claims               # List claims (filter by ?status= or ?stage=)
GET    /api/claims/{id}          # Get single claim
POST   /api/claims               # Create claim
PATCH  /api/claims/{id}/status   # Update claim status
```

### Notifications (WebSocket)
```
ws://localhost:8000/ws/notifications?token=<jwt>
```
Clients receive JSON push events when claim status changes.

---

## Demo Walkthrough

The prototype ships with a synthetic discharge summary (`test-data/discharge_complex.pdf`) designed to demonstrate the full pipeline:

**Patient:** Rajesh Kumar, 58M  
**Admitted for:** Pneumonia  
**Comorbidities documented:** Type 2 Diabetes (E11.9), Essential Hypertension (I10), Chronic Kidney Disease Stage 3 (N18.3)  
**Original bill codes:** J18.9 only

**After NormClaim:**
- 4 diagnoses extracted, all ICD-10 validated
- FHIR R4 Bundle with 8 resource types generated
- 3 missed diagnoses surfaced in reconciliation report
- Estimated claim delta: **₹14,200 – ₹17,500**

---

## Supported Document Types

| Type | What's extracted | FHIR output |
|------|-----------------|-------------|
| Discharge summary | Patient, diagnoses, procedures, medications, dates | Patient + Encounter + Condition + MedicationRequest + Claim |
| Lab report | Test names, values, units, reference ranges | Observation resources |
| Bill / claim | Billed codes, amounts, procedure codes | Claim resource (used as baseline for reconciliation) |
| Scanned image PDF | All of the above via Gemini Vision multimodal | Same as above |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Gemini AI API key — [get free key](https://aistudio.google.com/app/apikey) |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon (public) key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase service role key (backend only, never expose to client) |
| `FHIR_SERVICE_URL` | — | HAPI FHIR service URL (default: `http://localhost:8001/fhir/bundle`) |
| `BACKEND_URL` | — | Backend base URL (default: `http://localhost:8000`) |
| `CORS_ORIGINS` | — | Comma-separated allowed CORS origins |

Never commit `.env` or `.env.local` to version control.

---

## Roadmap

### Phase 1 — Hackathon MVP ✅
- [x] 4-layer pipeline (ingest → extract → FHIR map → reconcile)
- [x] ABDM-aligned FHIR R4 Bundle generation
- [x] ICD-10 gap analysis with ₹ delta
- [x] Android app (Java) + React web dashboard
- [x] Role-based access control (HOSPITAL / TPA / FINANCE)
- [x] Supabase authentication with row-level security
- [x] Pre-auth form auto-fill pipeline (ABHA lookup)
- [x] Real-time WebSocket notifications
- [x] Full claim lifecycle management
- [x] Finance reconciliation and settlement processing

### Phase 2 — Pilot (3 months)
- [ ] Deploy at 2–3 SME hospitals in Tier 2 cities
- [ ] Test with real discharge summaries
- [ ] Measure actual ₹ recovered per hospital per month
- [ ] Add Hindi document support via Gemini multimodal

### Phase 3 — Product (6–12 months)
- [ ] ABDM sandbox API certification
- [ ] SaaS pricing: ₹5,000–15,000 per hospital per month
- [ ] TPA and insurer API direct integrations
- [ ] Batch processing for historical document backfill
- [ ] S3 / object storage for PDF archiving

---

## Hackathon

**Event:** Jilo Health Hackathon on AI/ML in Healthcare  
**Organizers:** Jilo Health × NJACK IIT Patna  
**Venue:** IIT Patna, Bihar, India  
**Problem Statement:** PS-2 — AI-Powered Clinical & Administrative Data Normalization Engine  
**Contact:** jilohackathon@gmail.com

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*NormClaim — Every diagnosis. Every rupee.*  
*Team Kaizen Unit · Madhav Institute of Technology and Science, Gwalior*
