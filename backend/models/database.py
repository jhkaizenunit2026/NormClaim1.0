"""
NormClaim — Database Setup
SQLAlchemy PostgreSQL setup backed by Supabase (primary database).
"""

import os
import logging
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Float, Integer, Text, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

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


# Create all tables (safe to run repeatedly — ignores existing tables)
Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
