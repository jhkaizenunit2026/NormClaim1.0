"""
NormClaim — Stage 3: Patient admission after pre-auth approval.
Creates `admissions` rows and links `pre_auth_forms.admission_id` when that column exists.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from Extraction_pipeline.database import get_supabase
from models.database import SessionLocal

logger = logging.getLogger(__name__)


class AdmissionService:
    """Generates admission numbers and persists admissions (PostgreSQL via SQLAlchemy)."""

    ADMISSION_PREFIX = "ADM"

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()

    def _audit_log(
        self,
        *,
        patient_id: str | None,
        user_id: str | None,
        action: str,
        record_id: str | None,
        diff_snapshot: dict | None = None,
    ) -> None:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "stage": "admission",
            "action": action,
            "table_affected": "admissions",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    def generate_admission_number(self) -> str:
        """Sequential display id: ADM-{YYYY}-{5-digit counter}."""
        year = datetime.now(timezone.utc).year
        prefix = f"{self.ADMISSION_PREFIX}-{year}-"
        with SessionLocal() as session:
            row = session.execute(
                text(
                    "SELECT admission_number FROM admissions "
                    "WHERE admission_number LIKE :pfx "
                    "ORDER BY admission_number DESC LIMIT 1"
                ),
                {"pfx": f"{prefix}%"},
            ).mappings().first()
        next_n = 1
        if row and row.get("admission_number"):
            last = str(row["admission_number"])
            try:
                next_n = int(last.rsplit("-", 1)[-1]) + 1
            except ValueError:
                next_n = 1
        return f"{prefix}{next_n:05d}"

    def admit_patient(
        self,
        pre_auth_form_id: str,
        user_id: str | None,
    ) -> dict:
        """
        1. Validate pre_auth_form.form_status == 'approved'
        2. Generate admission number (retry on unique collision)
        3. Insert into admissions
        4. Update pre_auth_forms.admission_id (if column exists)
        5. Log to audit_logs

        Returns:
            {"admission_id", "admission_number", "pre_auth_form_id", "patient_id",
             "already_existed": bool}
        """
        form_resp = (
            self.db.table("pre_auth_forms")
            .select("*")
            .eq("id", pre_auth_form_id)
            .single()
            .execute()
        )
        form = form_resp.data
        if not form:
            raise ValueError(f"pre_auth_form {pre_auth_form_id} not found")

        patient_id = str(form.get("patient_id") or "")
        if not patient_id:
            raise ValueError("pre_auth_form has no patient_id")

        if str(form.get("form_status") or "") != "approved":
            raise PermissionError(
                "Pre-auth form must be approved before admission "
                f"(current status: {form.get('form_status')!r})."
            )

        existing_admission_id = form.get("admission_id")
        if existing_admission_id:
            adm_resp = (
                self.db.table("admissions")
                .select("*")
                .eq("id", str(existing_admission_id))
                .single()
                .execute()
            )
            adm = adm_resp.data
            if adm:
                return {
                    "admission_id": str(adm["id"]),
                    "admission_number": str(adm["admission_number"]),
                    "pre_auth_form_id": pre_auth_form_id,
                    "patient_id": patient_id,
                    "already_existed": True,
                }

        admitted_at = datetime.now(timezone.utc)
        last_error: Exception | None = None
        for _attempt in range(5):
            admission_id = str(uuid.uuid4())
            admission_number = self.generate_admission_number()
            row = {
                "id": admission_id,
                "admission_number": admission_number,
                "patient_id": patient_id,
                "pre_auth_form_id": pre_auth_form_id,
                "admitted_at": admitted_at.isoformat(),
                "discharge_at": None,
                "status": "admitted",
                "created_by": user_id,
            }
            try:
                self.db.table("admissions").insert(row).execute()
            except IntegrityError as exc:
                last_error = exc
                logger.warning(
                    "admission insert collision for %s, retrying: %s",
                    admission_number,
                    exc,
                )
                continue
            except Exception as exc:
                if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                    last_error = exc
                    continue
                raise

            try:
                self.db.table("pre_auth_forms").update(
                    {"admission_id": admission_id}
                ).eq("id", pre_auth_form_id).execute()
            except Exception as exc:
                logger.warning(
                    "pre_auth_forms.admission_id update failed (add column if missing): %s",
                    exc,
                )

            self._audit_log(
                patient_id=patient_id,
                user_id=user_id,
                action="admission.created",
                record_id=admission_id,
                diff_snapshot={
                    "pre_auth_form_id": pre_auth_form_id,
                    "admission_number": admission_number,
                },
            )
            return {
                "admission_id": admission_id,
                "admission_number": admission_number,
                "pre_auth_form_id": pre_auth_form_id,
                "patient_id": patient_id,
                "already_existed": False,
            }

        raise RuntimeError(
            "Could not allocate a unique admission number after retries"
        ) from last_error

    def get_admission(self, admission_id: str) -> dict | None:
        resp = (
            self.db.table("admissions")
            .select("*")
            .eq("id", admission_id)
            .single()
            .execute()
        )
        return resp.data
