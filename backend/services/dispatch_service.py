"""
NormClaim — Stage 7: claim PDF generation and dispatch (storage + optional SMTP).
"""

from __future__ import annotations

import logging
import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from Extraction_pipeline.database import get_supabase

logger = logging.getLogger(__name__)

_STORAGE_BUCKET = "documents"


class DispatchService:
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
            "stage": "dispatch",
            "action": action,
            "table_affected": "dispatch_records",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    @staticmethod
    def _pre_auth_ref(admission: dict) -> str | None:
        return admission.get("pre_auth_form_id") or admission.get("pre_auth_id")

    def _fetch_admission(self, admission_id: str) -> dict | None:
        resp = (
            self.db.table("admissions")
            .select("*")
            .eq("id", admission_id)
            .single()
            .execute()
        )
        return resp.data

    def _fetch_patient(self, patient_id: str) -> dict:
        resp = (
            self.db.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        return resp.data or {}

    def _fetch_pre_auth(self, admission: dict) -> dict:
        ref = self._pre_auth_ref(admission)
        if not ref:
            return {}
        resp = (
            self.db.table("pre_auth_forms")
            .select("*")
            .eq("id", str(ref))
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}

    def generate_claim_pdf(self, admission_id: str) -> bytes:
        """Build a simple formatted claim summary PDF (ReportLab)."""
        admission = self._fetch_admission(admission_id)
        if not admission:
            raise ValueError(f"admission {admission_id} not found")

        patient_id = str(admission.get("patient_id") or "")
        patient = self._fetch_patient(patient_id) if patient_id else {}
        pre_auth = self._fetch_pre_auth(admission)

        styles = getSampleStyleSheet()
        story: list[Any] = [
            Paragraph("NormClaim — insurance claim dispatch pack", styles["Title"]),
            Spacer(1, 12),
            Paragraph(
                f"<b>Admission number:</b> {admission.get('admission_number', '—')}",
                styles["Normal"],
            ),
            Paragraph(f"<b>Admission ID:</b> {admission_id}", styles["Normal"]),
            Paragraph(
                f"<b>Patient:</b> {patient.get('patient_name') or patient.get('name') or '—'}",
                styles["Normal"],
            ),
            Paragraph(f"<b>Patient ID:</b> {patient_id or '—'}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("<b>Pre-authorisation snapshot</b>", styles["Heading3"]),
            Paragraph(
                f"Primary diagnosis: {pre_auth.get('primary_diagnosis_text') or '—'}",
                styles["Normal"],
            ),
            Paragraph(
                f"Requested amount (INR): {pre_auth.get('requested_amount_inr') or '—'}",
                styles["Normal"],
            ),
            Spacer(1, 12),
            Paragraph(
                "<i>Attach supporting originals as per insurer checklist. "
                "This PDF is a system-generated summary only.</i>",
                styles["Normal"],
            ),
        ]

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, title="NormClaim claim")
        doc.build(story)
        return buf.getvalue()

    def dispatch_email(
        self,
        admission_id: str,
        recipient_email: str,
        pdf_bytes: bytes,
    ) -> dict:
        """Send PDF via SMTP when configured; otherwise return a simulated result."""
        host = (os.environ.get("SMTP_HOST") or "").strip()
        port = int(os.environ.get("SMTP_PORT") or "587")
        user = (os.environ.get("SMTP_USER") or "").strip()
        password = (os.environ.get("SMTP_PASSWORD") or "").strip()
        mail_from = (os.environ.get("SMTP_FROM") or user or "noreply@normclaim.local").strip()

        if not host:
            return {
                "status": "skipped",
                "reason": "SMTP_HOST not set — PDF generated only",
            }

        msg = EmailMessage()
        msg["Subject"] = f"Insurance claim documents — admission {admission_id}"
        msg["To"] = recipient_email
        msg["From"] = mail_from
        msg.set_content(
            "Please find the NormClaim-generated claim summary PDF attached.\n"
            "Submit with original hard copies as per your TPA checklist."
        )
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"normclaim-claim-{admission_id[:8]}.pdf",
        )

        try:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return {"status": "sent", "smtp_host": host}
        except Exception as exc:
            logger.exception("SMTP dispatch failed")
            return {"status": "failed", "error": str(exc)}

    def get_dispatch_status(self, dispatch_id: str) -> dict | None:
        resp = (
            self.db.table("dispatch_records")
            .select("*")
            .eq("id", dispatch_id)
            .single()
            .execute()
        )
        return resp.data

    def run_dispatch(
        self,
        admission_id: str,
        recipient_email: str,
        *,
        send_email: bool = True,
        requesting_user_id: str | None = None,
    ) -> dict:
        pdf = self.generate_claim_pdf(admission_id)
        admission = self._fetch_admission(admission_id)
        if not admission:
            raise ValueError(f"admission {admission_id} not found")

        patient_id = str(admission.get("patient_id") or "") or None
        dispatch_id = str(uuid.uuid4())
        storage_key = f"dispatch/{admission_id}/{dispatch_id}.pdf"

        try:
            self.db.storage.from_(_STORAGE_BUCKET).upload(storage_key, pdf)
        except Exception as exc:
            logger.warning("Dispatch PDF storage upload failed: %s", exc)
            storage_key = ""

        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": dispatch_id,
            "admission_id": admission_id,
            "recipient_email": recipient_email,
            "pdf_storage_key": storage_key or None,
            "dispatch_status": "pending",
            "dispatched_at": None,
            "delivered_at": None,
        }
        self.db.table("dispatch_records").insert(row).execute()

        email_detail: dict[str, Any] = {}
        final_status = "pdf_ready"
        dispatched_at: str | None = None

        if send_email:
            email_detail = self.dispatch_email(admission_id, recipient_email, pdf)
            if email_detail.get("status") == "sent":
                final_status = "dispatched"
                dispatched_at = now
            elif email_detail.get("status") == "skipped":
                final_status = "pending_smtp"
            else:
                final_status = "email_failed"
        else:
            email_detail = {"status": "skipped", "reason": "send_email=false"}
            final_status = "pdf_only"

        update_payload: dict[str, Any] = {"dispatch_status": final_status}
        if dispatched_at:
            update_payload["dispatched_at"] = dispatched_at

        self.db.table("dispatch_records").update(update_payload).eq(
            "id", dispatch_id
        ).execute()

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            action="dispatch.completed",
            record_id=dispatch_id,
            diff_snapshot={
                "admission_id": admission_id,
                "dispatch_status": final_status,
                "email_status": email_detail.get("status"),
            },
        )

        out_row = dict(
            self.get_dispatch_status(dispatch_id) or {**row, **update_payload}
        )
        out_row["email_detail"] = email_detail
        return out_row
