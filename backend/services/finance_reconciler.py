"""
NormClaim — Stage 9: finance reconciliation (expected vs TPA settlement).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import google.genai as gen
import instructor
from pydantic import BaseModel, Field

from Extraction_pipeline.database import get_google_api_key, get_supabase
from models.schemas import SettlementDeductionItem, SettlementLetterExtraction
from services.extractor import resolved_gemini_model

logger = logging.getLogger(__name__)


class ReconcileLLMOutput(BaseModel):
    mismatch_category: str = Field(
        description="One of: legitimate_deduction, processing_delay, coding_error, documentation_gap, potential_fraud"
    )
    recommendations: list[str] = Field(default_factory=list)
    fraud_risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class FinanceReconciler:
    MISMATCH_CATEGORIES = [
        "legitimate_deduction",
        "processing_delay",
        "coding_error",
        "documentation_gap",
        "potential_fraud",
    ]

    SYSTEM_PROMPT = f"""You are a hospital finance and health-claims analyst for India.
Given expected claim amount, amounts from the TPA settlement, bill breakdown hints, diagnoses, and deduction lines,
choose the single best mismatch_category from this closed set only:
{", ".join(MISMATCH_CATEGORIES)}

Explain briefly in recommendations (bullet strings) what the hospital should do next.
fraud_risk_score: low when mismatch is explained by standard deductions; higher only for inconsistent or suspicious patterns.
confidence: your confidence in the category and advice (0.0–1.0).
"""

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()
        raw_client = gen.Client(api_key=get_google_api_key())
        self._client = instructor.from_genai(
            client=raw_client,
            mode=instructor.Mode.GENAI_TOOLS,
        )

    def _audit_log(
        self,
        *,
        patient_id: str | None,
        user_id: str | None,
        record_id: str | None,
        diff_snapshot: dict | None = None,
    ) -> None:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "patient_id": patient_id,
            "stage": "finance",
            "action": "finance.reconciled",
            "table_affected": "finance_reconciliations",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.exception("audit_log write failed")

    @staticmethod
    def _coerce_settlement(row: dict) -> SettlementLetterExtraction:
        raw_ded = row.get("deductions") or []
        deductions: list[SettlementDeductionItem] = []
        if isinstance(raw_ded, list):
            for item in raw_ded:
                if not isinstance(item, dict):
                    continue
                try:
                    deductions.append(
                        SettlementDeductionItem(
                            description=str(item.get("description", "")),
                            amount=float(item.get("amount") or 0),
                            reason=item.get("reason"),
                        )
                    )
                except (TypeError, ValueError):
                    continue
        conf = row.get("confidence")
        try:
            c = float(conf) if conf is not None else 0.5
        except (TypeError, ValueError):
            c = 0.5
        c = max(0.0, min(1.0, c))
        return SettlementLetterExtraction(
            utr_number=row.get("utr_number"),
            settlement_amount=row.get("settlement_amount"),
            tds_amount=row.get("tds_amount"),
            deductions=deductions,
            final_payable=row.get("final_payable"),
            settlement_date=row.get("settlement_date"),
            remarks=row.get("remarks"),
            confidence=c,
        )

    def _latest_settlement_row(self, admission_id: str) -> dict | None:
        resp = (
            self.db.table("settlement_records")
            .select("*")
            .eq("admission_id", admission_id)
            .order("parsed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None

    @staticmethod
    def _received_amount(settlement: SettlementLetterExtraction) -> float:
        if settlement.final_payable is not None:
            return float(settlement.final_payable)
        if settlement.settlement_amount is not None:
            return float(settlement.settlement_amount)
        return 0.0

    @staticmethod
    def _deductions_triage(
        settlement: SettlementLetterExtraction,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for d in settlement.deductions:
            blob = f"{d.description} {d.reason or ''}".lower()
            if any(
                k in blob
                for k in ("copay", "co-pay", "deductible", "sub limit", "sublimit", "tariff")
            ):
                triage = "likely_legitimate"
            elif any(k in blob for k in ("documentation", "query", "pending")):
                triage = "documentation_gap"
            elif any(k in blob for k in ("icd", "coding", "package")):
                triage = "possible_coding"
            else:
                triage = "review"
            out.append(
                {
                    "description": d.description,
                    "amount": d.amount,
                    "reason": d.reason,
                    "triage": triage,
                }
            )
        return out

    @staticmethod
    def _normalize_category(raw: str) -> str:
        s = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
        for cat in FinanceReconciler.MISMATCH_CATEGORIES:
            if s == cat or cat in s or s in cat:
                return cat
        if "fraud" in s or "suspicious" in s:
            return "potential_fraud"
        if "code" in s or "icd" in s or "package" in s:
            return "coding_error"
        if "document" in s or "query" in s:
            return "documentation_gap"
        if "delay" in s or "pending" in s:
            return "processing_delay"
        return "legitimate_deduction"

    def reconcile(
        self,
        admission_id: str,
        expected_amount: float,
        settlement: SettlementLetterExtraction,
        bill_breakdown: dict,
        diagnoses: list[dict],
        *,
        patient_id: str | None = None,
        requesting_user_id: str | None = None,
    ) -> dict:
        received = self._received_amount(settlement)
        if received <= 0 and expected_amount > 0:
            raise ValueError(
                "Settlement has no final_payable or settlement_amount; cannot reconcile"
            )

        delta = round(received - float(expected_amount), 2)
        raise_flag = delta < 0
        deductions_analysis = self._deductions_triage(settlement)

        payload = {
            "expected_amount_inr": expected_amount,
            "received_amount_inr": received,
            "delta_inr": delta,
            "utr_number": settlement.utr_number,
            "tds_amount": settlement.tds_amount,
            "settlement_remarks": settlement.remarks,
            "deduction_lines": [d.model_dump() for d in settlement.deductions],
            "bill_breakdown": bill_breakdown,
            "diagnoses": diagnoses[:50],
        }
        user_prompt = f"DATA (JSON):\n{json.dumps(payload, ensure_ascii=False, default=str)[:14000]}"

        llm = self._client.chat.completions.create(
            model=resolved_gemini_model(),
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_model=ReconcileLLMOutput,
        )

        category = self._normalize_category(llm.mismatch_category)
        recs = [str(r).strip() for r in (llm.recommendations or []) if str(r).strip()][:12]

        rid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": rid,
            "admission_id": admission_id,
            "expected_amount": float(expected_amount),
            "received_amount": float(received),
            "delta": float(delta),
            "mismatch_category": category,
            "deductions_analysis": deductions_analysis,
            "recommendations": recs,
            "fraud_risk_score": float(llm.fraud_risk_score),
            "confidence": float(llm.confidence),
            "status": "pending",
            "resolved_at": None,
            "created_at": now,
        }
        self.db.table("finance_reconciliations").insert(row).execute()

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            record_id=rid,
            diff_snapshot={
                "admission_id": admission_id,
                "delta": delta,
                "mismatch_category": category,
                "raise_flag": raise_flag,
            },
        )

        return {
            "reconciliation_id": rid,
            "admission_id": admission_id,
            "expected_amount": float(expected_amount),
            "received_amount": float(received),
            "delta": float(delta),
            "raise_flag": raise_flag,
            "mismatch_category": category,
            "deductions_analysis": deductions_analysis,
            "recommendations": recs,
            "fraud_risk_score": float(llm.fraud_risk_score),
            "confidence": float(llm.confidence),
            "status": "pending",
        }

    def run_for_admission(
        self,
        admission_id: str,
        expected_amount: float,
        bill_breakdown: dict,
        diagnoses: list[dict],
        settlement_override: dict | None,
        *,
        patient_id: str | None = None,
        requesting_user_id: str | None = None,
    ) -> dict:
        if settlement_override:
            settlement = self._coerce_settlement(settlement_override)
        else:
            srow = self._latest_settlement_row(admission_id)
            if not srow:
                raise ValueError(
                    "No settlement_records row for this admission; pass settlement_override or parse a settlement letter first"
                )
            settlement = self._coerce_settlement(srow)

        return self.reconcile(
            admission_id,
            expected_amount,
            settlement,
            bill_breakdown,
            diagnoses,
            patient_id=patient_id,
            requesting_user_id=requesting_user_id,
        )
