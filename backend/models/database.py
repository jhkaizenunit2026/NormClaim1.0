"""
NormClaim — Database Setup
SQLAlchemy PostgreSQL setup backed by Supabase (primary database).
Includes consent tracking, status pipeline, and cascade deletion.
"""

import os
import logging
import json
from dotenv import load_dotenv

from sqlalchemy import (
    JSON,
    create_engine,
    Column,
    String,
    DateTime,
    Boolean,
    Float,
    Integer,
    Text,
    LargeBinary,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Ensure .env is loaded (no-op if already loaded in main.py)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

logger = logging.getLogger(__name__)

# ── Resolve database URL ──────────────────────────────────────────────────
_raw_url = os.environ.get("DATABASE_URL", "")

if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Add your Supabase PostgreSQL connection string to .env, e.g.:\n"
        "  DATABASE_URL=postgresql://postgres:PASSWORD@db.YOURREF.supabase.co:5432/postgres"
    )

# psycopg2 expects "postgresql://" — normalise the legacy "postgres://" URI scheme
DATABASE_URL = _raw_url.replace("postgres://", "postgresql://", 1)

logger.info("Database: using Supabase PostgreSQL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── ORM Models ────────────────────────────────────────────────────────────

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    has_extraction = Column(Boolean, default=False)
    has_report = Column(Boolean, default=False)
    file_size_bytes = Column(Integer, nullable=True)
    # Persisted PDF bytes (PostgreSQL BYTEA / SQLite BLOB)
    file_blob = Column(LargeBinary, nullable=True)
    # Object key within Supabase Storage bucket `documents`
    storage_key = Column(String(1024), nullable=True)
    # ABDM / DPDP consent tracking
    consent_obtained = Column(Boolean, default=False)
    # Pipeline status: uploaded → extracted → fhir_generated → reconciled
    status = Column(String(50), default="uploaded")


class ExtractionRecord(Base):
    __tablename__ = "extractions"

    document_id = Column(String, primary_key=True, index=True)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReportRecord(Base):
    __tablename__ = "reports"

    document_id = Column(String, primary_key=True, index=True)
    report_json = Column(Text, nullable=False)
    claim_delta_inr = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FhirBundleRecord(Base):
    __tablename__ = "fhir_bundles"

    document_id = Column(String, primary_key=True, index=True)
    bundle_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ClaimRecord(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, index=True)
    patient_name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)
    abha_id = Column(String, nullable=True)
    diagnosis = Column(String, nullable=False)
    icd10_code = Column(String, nullable=True)
    status = Column(String(64), default="PRE_AUTH_INITIATED", nullable=False)
    pre_auth_amount = Column(Float, default=0.0)
    admission_number = Column(String, nullable=True)
    enhancement_amount = Column(Float, default=0.0)
    copay = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    tpa_payable_amount = Column(Float, default=0.0)
    final_settlement_amount = Column(Float, default=0.0)
    tds_amount = Column(Float, default=0.0)
    utr_number = Column(String, nullable=True)
    discharge_approval_deadline = Column(String, nullable=True)
    timeline_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AdmissionRecord(Base):
    """Inpatient admission created after pre-auth approval (Stage 3)."""

    __tablename__ = "admissions"

    id = Column(String, primary_key=True, index=True)
    admission_number = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(String, nullable=False, index=True)
    pre_auth_id = Column(String, nullable=True, index=True)
    admitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    discharge_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="admitted", nullable=False)
    created_by = Column(String, nullable=True)


class EnhancementRequestRecord(Base):
    """AI-generated insurance enhancement request / TPA response (Stage 4)."""

    __tablename__ = "enhancement_requests"

    id = Column(String, primary_key=True, index=True)
    admission_id = Column(String, nullable=False, index=True)
    original_amount = Column(Float, nullable=True)
    suggested_amount = Column(Float, nullable=True)
    justification_text = Column(Text, nullable=True)
    severity_score = Column(Float, nullable=True)
    cost_breakdown = Column(JSON, nullable=True)
    status = Column(String(32), default="draft", nullable=False)
    tpa_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DispatchRecord(Base):
    """Hard-copy / email dispatch of final claim PDF (Stage 7)."""

    __tablename__ = "dispatch_records"

    id = Column(String, primary_key=True, index=True)
    admission_id = Column(String, nullable=False, index=True)
    recipient_email = Column(String(512), nullable=False)
    pdf_storage_key = Column(String(1024), nullable=True)
    dispatch_status = Column(String(32), default="pending", nullable=False)
    dispatched_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)


class SettlementRecord(Base):
    """Parsed TPA settlement letter fields (Stage 8)."""

    __tablename__ = "settlement_records"

    id = Column(String, primary_key=True, index=True)
    admission_id = Column(String, nullable=True, index=True)
    utr_number = Column(String(128), nullable=True)
    settlement_amount = Column(Float, nullable=True)
    tds_amount = Column(Float, nullable=True)
    deductions = Column(JSON, nullable=True)
    final_payable = Column(Float, nullable=True)
    settlement_date = Column(String(64), nullable=True)
    remarks = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    parsed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FinanceReconciliationRecord(Base):
    """Settlement vs expected reconciliation (Stage 9)."""

    __tablename__ = "finance_reconciliations"

    id = Column(String, primary_key=True, index=True)
    admission_id = Column(String, nullable=False, index=True)
    expected_amount = Column(Float, nullable=True)
    received_amount = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    mismatch_category = Column(String(64), nullable=True)
    deductions_analysis = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    fraud_risk_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    status = Column(String(32), default="pending", nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create all tables (safe to run repeatedly — ignores existing tables)
Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Helper Functions ──────────────────────────────────────────────────────

def save_document_with_consent(
    db: Session,
    document_id: str,
    filename: str,
    file_bytes: bytes,
    consent_obtained: bool,
    storage_key: Optional[str] = None,
) -> None:
    """Store document + consent flag together."""
    row = db.get(DocumentRecord, document_id)
    if row is None:
        row = DocumentRecord(
            id=document_id,
            filename=filename,
            file_size_bytes=len(file_bytes),
            has_extraction=False,
            has_report=False,
            file_blob=file_bytes,
            storage_key=storage_key,
            consent_obtained=consent_obtained,
            status="uploaded",
        )
        db.add(row)
    else:
        row.filename = filename
        row.file_size_bytes = len(file_bytes)
        row.file_blob = file_bytes
        row.storage_key = storage_key
        row.consent_obtained = consent_obtained
    db.commit()


def get_document_meta(db: Session, document_id: str) -> Optional[Dict[str, Any]]:
    """Return metadata dict (id, filename, uploaded_at, status, consent_obtained) without file bytes."""
    row = db.get(DocumentRecord, document_id)
    if row is None:
        return None
    return {
        "document_id": row.id,
        "filename": row.filename,
        "uploaded_at": row.upload_time.isoformat() + "Z" if row.upload_time else None,
        "status": row.status or "uploaded",
        "consent_obtained": row.consent_obtained or False,
        "file_size_bytes": row.file_size_bytes,
    }


def list_documents(db: Session) -> List[Dict[str, Any]]:
    """Return list of all document metadata dicts (no file bytes)."""
    rows = db.query(DocumentRecord).order_by(DocumentRecord.upload_time.desc()).all()
    results = []
    for row in rows:
        results.append({
            "document_id": row.id,
            "filename": row.filename,
            "status": row.status or "uploaded",
            "uploaded_at": row.upload_time.isoformat() + "Z" if row.upload_time else None,
        })
    return results


def update_document_status(db: Session, document_id: str, status: str) -> bool:
    """Updates pipeline stage. Returns False if document not found."""
    row = db.get(DocumentRecord, document_id)
    if row is None:
        return False
    row.status = status
    db.commit()
    return True


def delete_document(db: Session, document_id: str) -> bool:
    """
    Delete document and all related records.
    Deletion order (FK-safe): reports → fhir_bundles → extractions → documents.
    Returns False if document not found.
    """
    row = db.get(DocumentRecord, document_id)
    if row is None:
        return False

    # Delete downstream records first
    report = db.get(ReportRecord, document_id)
    if report:
        db.delete(report)

    fhir = db.get(FhirBundleRecord, document_id)
    if fhir:
        db.delete(fhir)

    extraction = db.get(ExtractionRecord, document_id)
    if extraction:
        db.delete(extraction)

    # Delete the document itself
    db.delete(row)
    db.commit()
    return True


def _claim_to_dict(row: ClaimRecord) -> Dict[str, Any]:
    timeline = []
    if row.timeline_json:
        try:
            timeline = json.loads(row.timeline_json)
        except Exception:
            timeline = []
    return {
        "claimId": row.id,
        "patientName": row.patient_name,
        "age": row.age,
        "sex": row.sex,
        "abhaId": row.abha_id,
        "diagnosis": row.diagnosis,
        "icd10Code": row.icd10_code,
        "status": row.status,
        "preAuthAmount": float(row.pre_auth_amount or 0.0),
        "updatedAt": row.updated_at.isoformat() + "Z" if row.updated_at else None,
        "createdAt": row.created_at.isoformat() + "Z" if row.created_at else None,
        "admissionNumber": row.admission_number,
        "enhancementAmount": float(row.enhancement_amount or 0.0),
        "copay": float(row.copay or 0.0),
        "deductions": float(row.deductions or 0.0),
        "tpaPayableAmount": float(row.tpa_payable_amount or 0.0),
        "finalSettlementAmount": float(row.final_settlement_amount or 0.0),
        "tdsAmount": float(row.tds_amount or 0.0),
        "utrNumber": row.utr_number,
        "dischargeApprovalDeadline": row.discharge_approval_deadline,
        "timeline": timeline,
    }


def list_claims(db: Session, status: Optional[str] = None) -> List[Dict[str, Any]]:
    q = db.query(ClaimRecord)
    if status:
        q = q.filter(ClaimRecord.status == status)
    rows = q.order_by(ClaimRecord.updated_at.desc()).all()
    return [_claim_to_dict(row) for row in rows]


def get_claim(db: Session, claim_id: str) -> Optional[Dict[str, Any]]:
    row = db.get(ClaimRecord, claim_id)
    if row is None:
        return None
    return _claim_to_dict(row)


def create_claim(db: Session, claim_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    timeline = [
        {
            "stage": "PRE_AUTH_INITIATED",
            "action": "Pre-auth created",
            "actor": "Hospital",
            "timestamp": now.isoformat() + "Z",
        }
    ]
    row = ClaimRecord(
        id=claim_id,
        patient_name=payload["patientName"],
        age=payload.get("age"),
        sex=payload.get("sex"),
        abha_id=payload.get("abhaId"),
        diagnosis=payload["diagnosis"],
        icd10_code=payload.get("icd10Code"),
        status="PRE_AUTH_INITIATED",
        pre_auth_amount=float(payload.get("estimatedAmount") or 0.0),
        timeline_json=json.dumps(timeline),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _claim_to_dict(row)


def update_claim_status(db: Session, claim_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = db.get(ClaimRecord, claim_id)
    if row is None:
        return None

    row.status = payload.get("status", row.status)
    if payload.get("amount") is not None:
        row.pre_auth_amount = float(payload["amount"])
    if payload.get("enhancementAmount") is not None:
        row.enhancement_amount = float(payload["enhancementAmount"])
    if payload.get("copay") is not None:
        row.copay = float(payload["copay"])
    if payload.get("deductions") is not None:
        row.deductions = float(payload["deductions"])
    if payload.get("tpaPayableAmount") is not None:
        row.tpa_payable_amount = float(payload["tpaPayableAmount"])
    if payload.get("finalSettlementAmount") is not None:
        row.final_settlement_amount = float(payload["finalSettlementAmount"])
    if payload.get("tdsAmount") is not None:
        row.tds_amount = float(payload["tdsAmount"])
    if payload.get("utrNumber") is not None:
        row.utr_number = payload["utrNumber"]
    if payload.get("admissionNumber") is not None:
        row.admission_number = payload["admissionNumber"]
    if payload.get("dischargeApprovalDeadline") is not None:
        row.discharge_approval_deadline = payload["dischargeApprovalDeadline"]

    timeline = []
    if row.timeline_json:
        try:
            timeline = json.loads(row.timeline_json)
        except Exception:
            timeline = []

    timeline.append(
        {
            "stage": row.status,
            "action": f"Status updated to {row.status}",
            "actor": "System",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
    )
    row.timeline_json = json.dumps(timeline)
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return _claim_to_dict(row)
