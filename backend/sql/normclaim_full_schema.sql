-- ═══════════════════════════════════════════════════════════════════════════
-- NormClaim — full PostgreSQL schema (Supabase-compatible)
-- Run in: Supabase Dashboard → SQL Editor (or psql against DATABASE_URL)
--
-- Covers:
--   • Auth profiles (from web-dashboard/authentication/001_create_profiles.sql)
--   • SQLAlchemy tables: documents, extractions, reports, fhir_bundles, claims
--   • Supabase client tables: patients, pre_auth_forms, ai_extraction_records, …
--
-- Notes:
--   • Backend also calls Base.metadata.create_all() for ORM tables; this file
--     matches those models so you can bootstrap a fresh DB in one shot.
--   • Service role bypasses RLS; enable policies if you expose tables to anon.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Auth-linked profiles (signup trigger) ───────────────────────────────────

CREATE TABLE IF NOT EXISTS public.profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  email           TEXT NOT NULL,
  name            TEXT NOT NULL DEFAULT '',
  role            TEXT NOT NULL DEFAULT 'HOSPITAL'
                    CHECK (role IN ('HOSPITAL', 'TPA', 'FINANCE')),
  hospital_id     TEXT,
  tpa_officer_id  TEXT,
  finance_user_id TEXT,
  avatar_url      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles: own read" ON public.profiles;
CREATE POLICY "profiles: own read"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles: own update" ON public.profiles;
CREATE POLICY "profiles: own update"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles: service full access" ON public.profiles;
CREATE POLICY "profiles: service full access"
  ON public.profiles
  USING (auth.role() = 'service_role');

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'name', SPLIT_PART(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'role', 'HOSPITAL')
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS profiles_updated_at ON public.profiles;
CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

CREATE INDEX IF NOT EXISTS profiles_role_idx ON public.profiles (role);
CREATE INDEX IF NOT EXISTS profiles_hospital_id_idx ON public.profiles (hospital_id);

-- ── Core ORM tables (models/database.py) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.documents (
  id                TEXT PRIMARY KEY,
  filename          TEXT NOT NULL,
  upload_time       TIMESTAMPTZ DEFAULT NOW(),
  has_extraction    BOOLEAN DEFAULT FALSE,
  has_report        BOOLEAN DEFAULT FALSE,
  file_size_bytes   INTEGER,
  file_blob         BYTEA,
  storage_key       VARCHAR(1024),
  consent_obtained  BOOLEAN DEFAULT FALSE,
  status            VARCHAR(50) DEFAULT 'uploaded'
);

CREATE TABLE IF NOT EXISTS public.extractions (
  document_id   TEXT PRIMARY KEY REFERENCES public.documents (id) ON DELETE CASCADE,
  result_json   TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.reports (
  document_id      TEXT PRIMARY KEY REFERENCES public.documents (id) ON DELETE CASCADE,
  report_json      TEXT NOT NULL,
  claim_delta_inr  DOUBLE PRECISION DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.fhir_bundles (
  document_id   TEXT PRIMARY KEY REFERENCES public.documents (id) ON DELETE CASCADE,
  bundle_json   TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.claims (
  id                         TEXT PRIMARY KEY,
  patient_name               TEXT NOT NULL,
  age                        INTEGER,
  sex                        TEXT,
  abha_id                    TEXT,
  diagnosis                  TEXT NOT NULL,
  icd10_code                 TEXT,
  status                     VARCHAR(64) NOT NULL DEFAULT 'PRE_AUTH_INITIATED',
  pre_auth_amount            DOUBLE PRECISION DEFAULT 0,
  admission_number           TEXT,
  enhancement_amount         DOUBLE PRECISION DEFAULT 0,
  copay                      DOUBLE PRECISION DEFAULT 0,
  deductions                 DOUBLE PRECISION DEFAULT 0,
  tpa_payable_amount         DOUBLE PRECISION DEFAULT 0,
  final_settlement_amount    DOUBLE PRECISION DEFAULT 0,
  tds_amount                 DOUBLE PRECISION DEFAULT 0,
  utr_number                 TEXT,
  discharge_approval_deadline TEXT,
  timeline_json              TEXT,
  created_at                 TIMESTAMPTZ DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS claims_status_idx ON public.claims (status);
CREATE INDEX IF NOT EXISTS claims_updated_at_idx ON public.claims (updated_at DESC);

-- ── Patients & policies (pre-auth pipeline) ───────────────────────────────

CREATE TABLE IF NOT EXISTS public.patients (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_name       TEXT,
  age                INTEGER,
  gender             TEXT,
  abha_id            TEXT,
  abha_verified      BOOLEAN DEFAULT FALSE,
  consent_obtained   BOOLEAN DEFAULT FALSE,
  -- Ownership for API auth (see Extraction_pipeline/router.py OWNER_FIELD_CANDIDATES)
  user_id            UUID REFERENCES auth.users (id) ON DELETE SET NULL,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS patients_user_id_idx ON public.patients (user_id);

CREATE TABLE IF NOT EXISTS public.insurance_policies (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id         UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  policy_number      TEXT,
  insurer_name       TEXT,
  tpa_name           TEXT,
  sum_insured_inr    NUMERIC(14, 2),
  is_active          BOOLEAN DEFAULT TRUE,
  created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS insurance_policies_patient_idx ON public.insurance_policies (patient_id);

-- ── Pre-auth forms (pre_auth_filling.py) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.pre_auth_forms (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id                 UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  policy_id                  UUID REFERENCES public.insurance_policies (id) ON DELETE SET NULL,
  -- Optional owner (same candidates as router)
  user_id                    UUID REFERENCES auth.users (id) ON DELETE SET NULL,
  created_by                 UUID REFERENCES auth.users (id) ON DELETE SET NULL,

  id_proof_type              TEXT,
  id_proof_number            TEXT,
  primary_diagnosis_text     TEXT,
  primary_icd10_code         TEXT,
  referring_doctor_name      TEXT,
  referring_doctor_reg       TEXT,
  referral_notes             TEXT,
  planned_procedure          TEXT,
  estimated_los_days         INTEGER,
  secondary_diagnoses        JSONB DEFAULT '[]'::JSONB,
  requested_amount_inr       NUMERIC(14, 2),
  estimated_amount_inr       NUMERIC(14, 2),

  auto_filled                BOOLEAN DEFAULT FALSE,
  auto_fill_source           TEXT,
  auto_fill_snapshot_json    JSONB,
  auto_filled_fields         JSONB DEFAULT '[]'::JSONB,
  field_requirements_meta    JSONB DEFAULT '{}'::JSONB,
  form_status                TEXT DEFAULT 'draft',

  created_at                 TIMESTAMPTZ DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS pre_auth_forms_patient_idx ON public.pre_auth_forms (patient_id);
CREATE INDEX IF NOT EXISTS pre_auth_forms_status_idx ON public.pre_auth_forms (form_status);

-- ── AI extraction storage (extraction_pipeline.py) ───────────────────────────

CREATE TABLE IF NOT EXISTS public.ai_extraction_records (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id            UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  source_document_url   TEXT,
  patient_snapshot      JSONB DEFAULT '{}'::JSONB,
  encounter_snapshot    JSONB DEFAULT '{}'::JSONB,
  diagnoses             JSONB DEFAULT '[]'::JSONB,
  procedures            JSONB DEFAULT '[]'::JSONB,
  medications           JSONB DEFAULT '[]'::JSONB,
  billed_codes          JSONB DEFAULT '[]'::JSONB,
  raw_text_preview      TEXT,
  section_map           JSONB DEFAULT '{}'::JSONB,
  negated_spans         JSONB DEFAULT '[]'::JSONB,
  low_confidence_flags  JSONB DEFAULT '[]'::JSONB,
  detected_script       TEXT,
  confidence_score      DOUBLE PRECISION,
  model_version         TEXT,
  review_status         TEXT DEFAULT 'pending',
  created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ai_extraction_patient_idx ON public.ai_extraction_records (patient_id);

-- ── Document attachments (OCR inputs + confidence report files) ─────────────

CREATE TABLE IF NOT EXISTS public.document_attachments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type       TEXT NOT NULL,
  entity_id         UUID NOT NULL,
  doc_type          TEXT NOT NULL,
  storage_key       TEXT,
  storage_bucket    TEXT DEFAULT 'documents',
  storage_url       TEXT,
  file_path         TEXT,
  path              TEXT,
  bucket            TEXT,
  is_mandatory      BOOLEAN DEFAULT FALSE,
  is_verified       BOOLEAN DEFAULT FALSE,
  filename          TEXT,
  file_format       TEXT,
  file_size_bytes   INTEGER,
  uploaded_by       TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS document_attachments_entity_idx
  ON public.document_attachments (entity_type, entity_id);

-- ── Audit & corrections ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID,
  patient_id       UUID,
  stage            TEXT,
  action           TEXT,
  table_affected   TEXT,
  record_id        TEXT,
  diff_snapshot    JSONB DEFAULT '{}'::JSONB,
  logged_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_logs_patient_idx ON public.audit_logs (patient_id);
CREATE INDEX IF NOT EXISTS audit_logs_logged_at_idx ON public.audit_logs (logged_at DESC);

CREATE TABLE IF NOT EXISTS public.preauth_corrections (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pre_auth_form_id   UUID NOT NULL REFERENCES public.pre_auth_forms (id) ON DELETE CASCADE,
  field_name         TEXT NOT NULL,
  original_value     TEXT,
  corrected_value    TEXT NOT NULL,
  reviewer_user_id   UUID NOT NULL,
  corrected_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Reviews & feedback (review_service / feedback_service / analytics) ─────

CREATE TABLE IF NOT EXISTS public.human_reviews (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      TEXT NOT NULL,
  reviewer_notes   TEXT,
  corrections_json JSONB DEFAULT '[]'::JSONB,
  reviewed_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS human_reviews_document_idx ON public.human_reviews (document_id);

CREATE TABLE IF NOT EXISTS public.feedback (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      TEXT NOT NULL,
  was_correct      BOOLEAN,
  correction_type  TEXT,
  details          TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS feedback_document_idx ON public.feedback (document_id);

-- Legacy / analytics aggregate (services/analytics_service.py reads delta_inr)
CREATE TABLE IF NOT EXISTS public.reconciliations (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id TEXT,
  delta_inr   DOUBLE PRECISION DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Admissions & downstream stages ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.admissions (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id         UUID NOT NULL REFERENCES public.patients (id) ON DELETE CASCADE,
  admission_number   TEXT,
  status             TEXT DEFAULT 'active',
  admitted_at        TIMESTAMPTZ,
  pre_auth_form_id   UUID REFERENCES public.pre_auth_forms (id) ON DELETE SET NULL,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS admissions_patient_idx ON public.admissions (patient_id);

CREATE TABLE IF NOT EXISTS public.enhancement_requests (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id       UUID NOT NULL REFERENCES public.admissions (id) ON DELETE CASCADE,
  original_amount    DOUBLE PRECISION,
  suggested_amount   DOUBLE PRECISION,
  justification_text TEXT,
  severity_score     DOUBLE PRECISION,
  cost_breakdown     JSONB DEFAULT '{}'::JSONB,
  status             TEXT DEFAULT 'draft',
  tpa_response       JSONB,
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS enhancement_admission_idx ON public.enhancement_requests (admission_id);

CREATE TABLE IF NOT EXISTS public.settlement_records (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id       UUID REFERENCES public.admissions (id) ON DELETE SET NULL,
  utr_number         TEXT,
  settlement_amount  DOUBLE PRECISION,
  tds_amount         DOUBLE PRECISION,
  deductions         JSONB DEFAULT '[]'::JSONB,
  final_payable      DOUBLE PRECISION,
  settlement_date    TEXT,
  remarks            TEXT,
  confidence         DOUBLE PRECISION,
  parsed_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS settlement_admission_idx ON public.settlement_records (admission_id);

CREATE TABLE IF NOT EXISTS public.finance_reconciliations (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admission_id         UUID NOT NULL REFERENCES public.admissions (id) ON DELETE CASCADE,
  expected_amount      DOUBLE PRECISION,
  received_amount      DOUBLE PRECISION,
  delta                  DOUBLE PRECISION,
  mismatch_category    TEXT,
  deductions_analysis  JSONB DEFAULT '[]'::JSONB,
  recommendations      JSONB DEFAULT '[]'::JSONB,
  fraud_risk_score     DOUBLE PRECISION,
  confidence           DOUBLE PRECISION,
  status               TEXT DEFAULT 'pending',
  resolved_at          TIMESTAMPTZ,
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS finance_recon_admission_idx ON public.finance_reconciliations (admission_id);
