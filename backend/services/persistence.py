"""
SQLite persistence for documents, extractions, reconciliation reports, and FHIR bundles.
Hydrates in-memory router caches on startup and on demand (Supabase re-download).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models.database import (
    SessionLocal,
    Base,
    DocumentRecord,
    ExtractionRecord,
    ReportRecord,
    FhirBundleRecord,
    engine,
)
from models.schemas import ExtractionResult, ReconciliationReport

logger = logging.getLogger(__name__)


def _migrate_schema() -> None:
    """Add columns / tables for existing SQLite files created before new fields."""
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    tables = insp.get_table_names()
    if "documents" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("documents")}
    with engine.begin() as conn:
        if "file_blob" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN file_blob BLOB"))
        if "storage_key" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN storage_key VARCHAR(1024)"))


_migrate_schema()


def save_document(
    db: Session,
    document_id: str,
    filename: str,
    file_bytes: bytes,
    storage_key: Optional[str],
) -> None:
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
        )
        db.add(row)
    else:
        row.filename = filename
        row.file_size_bytes = len(file_bytes)
        row.file_blob = file_bytes
        row.storage_key = storage_key
    db.commit()


def get_document_meta(db: Session, document_id: str) -> Optional[DocumentRecord]:
    return db.get(DocumentRecord, document_id)


def save_extraction_result(db: Session, result: ExtractionResult) -> None:
    payload = result.model_dump()
    # JSON-serializable: section_map keys may be int from upstream — normalize
    if "section_map" in payload and payload["section_map"]:
        payload["section_map"] = {str(k): v for k, v in payload["section_map"].items()}
    row = db.get(ExtractionRecord, result.document_id)
    if row is None:
        db.add(
            ExtractionRecord(
                document_id=result.document_id,
                result_json=json.dumps(payload, ensure_ascii=False),
            )
        )
    else:
        row.result_json = json.dumps(payload, ensure_ascii=False)
    doc = db.get(DocumentRecord, result.document_id)
    if doc:
        doc.has_extraction = True
    db.commit()


def load_extraction_result(document_id: str) -> Optional[ExtractionResult]:
    with SessionLocal() as db:
        row = db.get(ExtractionRecord, document_id)
        if not row:
            return None
        data = json.loads(row.result_json)
        return ExtractionResult(**data)


def save_reconciliation_report(db: Session, report: ReconciliationReport) -> None:
    payload = report.model_dump()
    row = db.get(ReportRecord, report.document_id)
    if row is None:
        db.add(
            ReportRecord(
                document_id=report.document_id,
                report_json=json.dumps(payload, ensure_ascii=False),
                claim_delta_inr=report.estimated_claim_delta_inr,
            )
        )
    else:
        row.report_json = json.dumps(payload, ensure_ascii=False)
        row.claim_delta_inr = report.estimated_claim_delta_inr
    doc = db.get(DocumentRecord, report.document_id)
    if doc:
        doc.has_report = True
    db.commit()


def load_reconciliation_report(document_id: str) -> Optional[ReconciliationReport]:
    with SessionLocal() as db:
        row = db.get(ReportRecord, document_id)
        if not row:
            return None
        data = json.loads(row.report_json)
        return ReconciliationReport(**data)


def save_fhir_bundle_db(document_id: str, bundle: Dict[str, Any]) -> None:
    with SessionLocal() as db:
        row = db.get(FhirBundleRecord, document_id)
        dumped = json.dumps(bundle, ensure_ascii=False)
        if row is None:
            db.add(FhirBundleRecord(document_id=document_id, bundle_json=dumped))
        else:
            row.bundle_json = dumped
        db.commit()


def row_has_extraction(document_id: str) -> bool:
    with SessionLocal() as db:
        return db.get(ExtractionRecord, document_id) is not None


def row_has_report(document_id: str) -> bool:
    with SessionLocal() as db:
        return db.get(ReportRecord, document_id) is not None


def load_fhir_bundle_db(document_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        row = db.get(FhirBundleRecord, document_id)
        if not row:
            return None
        return json.loads(row.bundle_json)


def fetch_bytes_from_supabase(document_id: str) -> Optional[bytes]:
    """Download PDF bytes from Supabase Storage using persisted storage_key."""
    try:
        from main import supabase
    except Exception:
        supabase = None
    if supabase is None:
        return None
    with SessionLocal() as db:
        row = db.get(DocumentRecord, document_id)
        if not row or not row.storage_key:
            return None
        key = row.storage_key
    try:
        return supabase.storage.from_("documents").download(key)
    except Exception as e:
        logger.warning("Supabase download failed for %s: %s", document_id, e)
        return None


def ensure_document_bytes(document_id: str) -> Optional[bytes]:
    """Resolve bytes from SQLite blob or Supabase."""
    with SessionLocal() as db:
        row = db.get(DocumentRecord, document_id)
        if row and row.file_blob:
            return row.file_blob
    return fetch_bytes_from_supabase(document_id)


def hydrate_document_for_extract(document_id: str) -> bool:
    """
    Ensure routers.documents.DOCUMENTS has bytes for document_id using SQLite + Supabase.
    Returns True if bytes are available.
    """
    from routers.documents import DOCUMENTS

    with SessionLocal() as db:
        row = db.get(DocumentRecord, document_id)
    if not row:
        return False
    if document_id not in DOCUMENTS:
        DOCUMENTS[document_id] = {
            "filename": row.filename,
            "size": row.file_size_bytes or 0,
            "bytes": row.file_blob,
        }
    elif DOCUMENTS[document_id].get("bytes") is None and row.file_blob:
        DOCUMENTS[document_id]["bytes"] = row.file_blob

    if DOCUMENTS[document_id].get("bytes"):
        return True

    raw = ensure_document_bytes(document_id)
    if raw:
        DOCUMENTS[document_id]["bytes"] = raw
        return True
    return False


def bootstrap_memory_caches() -> None:
    """Load SQLite state into router in-memory dicts after process restart."""
    from routers.documents import DOCUMENTS
    from routers.extract import EXTRACTIONS
    from routers.reconcile import REPORTS
    from routers.fhir import FHIR_BUNDLES

    with SessionLocal() as db:
        for doc in db.query(DocumentRecord).all():
            DOCUMENTS[doc.id] = {
                "filename": doc.filename,
                "size": doc.file_size_bytes or 0,
                "bytes": doc.file_blob,
            }
        for ex in db.query(ExtractionRecord).all():
            try:
                data = json.loads(ex.result_json)
                EXTRACTIONS[ex.document_id] = ExtractionResult(**data)
            except Exception as e:
                logger.warning("Skip bad extraction row %s: %s", ex.document_id, e)
        for rep in db.query(ReportRecord).all():
            try:
                data = json.loads(rep.report_json)
                REPORTS[rep.document_id] = ReconciliationReport(**data)
            except Exception as e:
                logger.warning("Skip bad report row %s: %s", rep.document_id, e)
        for fb in db.query(FhirBundleRecord).all():
            try:
                FHIR_BUNDLES[fb.document_id] = json.loads(fb.bundle_json)
            except Exception as e:
                logger.warning("Skip bad FHIR row %s: %s", fb.document_id, e)

    logger.info(
        "Persistence bootstrap: documents=%s extractions=%s reports=%s fhir=%s",
        len(DOCUMENTS),
        len(EXTRACTIONS),
        len(REPORTS),
        len(FHIR_BUNDLES),
    )
