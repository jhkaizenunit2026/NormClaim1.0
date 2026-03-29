"""
NormClaim — Stage 6: discharge approval optimization (rules + heuristics).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from Extraction_pipeline.database import get_supabase

logger = logging.getLogger(__name__)

_BILL_KEYS = (
    "room_charges",
    "medicines",
    "procedures",
    "investigations",
    "doctor_fees",
    "nursing_charges",
    "consumables",
)


class DischargeOptimizer:
    """
    Rule engine + light heuristics for copay, deductions, approval probability, and flags.
    """

    POLICY_RULES = {
        "room_rent_cap_percent": 1.0,
        "icu_multiplier": 2.0,
        "pre_existing_waiting_period_years": 2,
        "default_copay_percent": 5.0,
        "medicine_cap_percent_of_si": 0.15,
    }

    def __init__(self, db: Any | None = None):
        self.db = db or get_supabase()

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
            "stage": "discharge",
            "action": "discharge.optimized",
            "table_affected": "admissions",
            "record_id": record_id,
            "diff_snapshot": diff_snapshot or {},
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.db.table("audit_logs").insert(row).execute()
        except Exception as exc:
            logger.error("audit_log write failed: %s", exc)

    @staticmethod
    def _as_breakdown_dict(bill_breakdown: dict | Any) -> dict[str, float]:
        if hasattr(bill_breakdown, "model_dump"):
            raw = bill_breakdown.model_dump()
        else:
            raw = dict(bill_breakdown)
        out: dict[str, float] = {}
        for k in _BILL_KEYS:
            try:
                out[k] = float(raw.get(k) or 0)
            except (TypeError, ValueError):
                out[k] = 0.0
        try:
            out["total"] = float(raw.get("total") or 0)
        except (TypeError, ValueError):
            out["total"] = 0.0
        return out

    @staticmethod
    def _bill_total(bb: dict[str, float]) -> float:
        t = float(bb.get("total") or 0)
        if t > 0:
            return t
        return sum(bb.get(k, 0) for k in _BILL_KEYS)

    @staticmethod
    def _diagnosis_blob(diagnoses: list[dict]) -> str:
        parts: list[str] = []
        for d in diagnoses:
            if not isinstance(d, dict):
                continue
            parts.append(str(d.get("text") or d.get("diagnosis") or ""))
            parts.append(str(d.get("icd10_code") or ""))
        return " ".join(parts).lower()

    @staticmethod
    def _infer_los_days(admitted_at: Any) -> int:
        if admitted_at is None:
            return 3
        try:
            if isinstance(admitted_at, str):
                s = admitted_at.replace("Z", "+00:00")
                start = datetime.fromisoformat(s)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
            elif hasattr(admitted_at, "timestamp"):
                start = admitted_at
                if getattr(start, "tzinfo", None) is None:
                    start = start.replace(tzinfo=timezone.utc)
            else:
                return 3
            delta = datetime.now(timezone.utc) - start
            if delta.total_seconds() < 0:
                return 1
            days = max(1, int(delta.total_seconds() / 86400) or 1)
            return min(days, 365)
        except Exception:
            return 3

    def optimize(
        self,
        admission_id: str,
        bill_breakdown: dict | Any,
        policy: dict,
        diagnoses: list[dict],
        *,
        los_days: int | None = None,
        admitted_at: Any = None,
        patient_id: str | None = None,
        requesting_user_id: str | None = None,
    ) -> dict:
        bb = self._as_breakdown_dict(bill_breakdown)
        gross = self._bill_total(bb)

        sum_insured = policy.get("sum_insured_inr") or policy.get("sum_insured")
        try:
            si = float(sum_insured) if sum_insured is not None else 500_000.0
        except (TypeError, ValueError):
            si = 500_000.0

        los = int(los_days) if los_days is not None else self._infer_los_days(admitted_at)
        los = max(1, min(los, 365))

        room_cap_pct = float(self.POLICY_RULES["room_rent_cap_percent"])
        icu_mult = float(self.POLICY_RULES["icu_multiplier"])
        diag_text = self._diagnosis_blob(diagnoses)
        icu = any(x in diag_text for x in ("icu", "itu", "intensive care", "nicu", "hdu"))
        room_mult = icu_mult if icu else 1.0

        per_day_cap = si * (room_cap_pct / 100.0) * room_mult
        allowed_room = per_day_cap * los
        room_charges = float(bb.get("room_charges") or 0)

        flags: list[str] = []
        deductions: list[dict[str, Any]] = []

        if allowed_room > 0 and room_charges > allowed_room * 1.02:
            over = room_charges - allowed_room
            flags.append("room_rent_exceeds_sublimit")
            deductions.append(
                {
                    "description": "Room rent above policy sub-limit",
                    "amount": round(over, 2),
                    "reason": f"Cap ~₹{allowed_room:,.0f} for {los} day(s) at {room_cap_pct}% SI/day (icu_mult={room_mult})",
                }
            )

        med_cap = si * (float(self.POLICY_RULES["medicine_cap_percent_of_si"]))
        med = float(bb.get("medicines") or 0)
        if med_cap > 0 and med > med_cap * 1.05:
            over_m = med - med_cap
            flags.append("medicine_above_sublimit")
            deductions.append(
                {
                    "description": "Medicines above typical SI-linked sub-limit",
                    "amount": round(over_m, 2),
                    "reason": f"Reference cap ₹{med_cap:,.0f} ({self.POLICY_RULES['medicine_cap_percent_of_si']*100:.0f}% of SI)",
                }
            )

        if any(k in diag_text for k in ("pre-existing", "preexisting", "ped", "known case")):
            flags.append("possible_pre_existing_clause")

        total_deductions = sum(float(d["amount"]) for d in deductions)
        optimized_claim = max(0.0, gross - total_deductions)

        copay_pct = float(self.POLICY_RULES["default_copay_percent"])
        predicted_copay = round(optimized_claim * (copay_pct / 100.0), 2)

        approval_probability = 0.92 - 0.12 * len(flags)
        approval_probability = max(0.35, min(0.97, approval_probability))

        est_minutes = 15 + 18 * len(flags)
        est_minutes = min(est_minutes, 180)

        result = {
            "admission_id": admission_id,
            "predicted_copay": predicted_copay,
            "valid_deductions": deductions,
            "approval_probability": round(approval_probability, 3),
            "optimized_claim_amount": round(optimized_claim, 2),
            "flags": flags,
            "estimated_tpa_time_minutes": est_minutes,
            "policy_snapshot": {
                "sum_insured_inr_used": si,
                "los_days": los,
                "gross_bill_inr": round(gross, 2),
                "rules": dict(self.POLICY_RULES),
            },
        }

        self._audit_log(
            patient_id=patient_id,
            user_id=requesting_user_id,
            record_id=admission_id,
            diff_snapshot={
                "flags": flags,
                "optimized_claim_amount": result["optimized_claim_amount"],
                "approval_probability": result["approval_probability"],
            },
        )
        return result
