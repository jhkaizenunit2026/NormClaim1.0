"""
Synthetic end-to-end chain for NormClaim pipeline stages 6–9 (no live Gemini / Supabase).

Run from `backend/`:
  pytest tests/test_e2e_synthetic_pipeline.py -q

These tests mock DB writes and the finance LLM. For full HTTP + DB verification,
use a configured .env and manual calls per AI_Extraction_Master_Prompt.md §10.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models.schemas import BillBreakdown, SettlementLetterExtraction
from services.discharge_optimizer import DischargeOptimizer
from services.finance_reconciler import FinanceReconciler, ReconcileLLMOutput


def _fake_supabase_adapter() -> MagicMock:
    """Minimal adapter: table(...).insert(...).execute() no-ops."""
    db = MagicMock()

    def _table(_name: str) -> MagicMock:
        t = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=None)
        t.insert.return_value = chain
        t.update.return_value = chain
        t.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.order.return_value = chain
        chain.single.return_value = chain
        return t

    db.table.side_effect = _table
    return db


def test_discharge_optimizer_synthetic_high_room_triggers_flag():
    db = _fake_supabase_adapter()
    opt = DischargeOptimizer(db=db)
    bill = BillBreakdown(
        room_charges=200_000,
        medicines=10_000,
        procedures=20_000,
        investigations=5_000,
        doctor_fees=5_000,
        nursing_charges=2_000,
        consumables=1_000,
        total=243_000,
        confidence=0.85,
    )
    policy = {"sum_insured_inr": 500_000}
    diagnoses: list[dict] = [{"text": "Community acquired pneumonia", "icd10_code": "J18.9"}]

    out = opt.optimize(
        "synthetic-adm-001",
        bill,
        policy,
        diagnoses,
        los_days=5,
        patient_id="synthetic-patient-001",
        requesting_user_id="synthetic-user",
    )

    assert out["admission_id"] == "synthetic-adm-001"
    assert "room_rent_exceeds_sublimit" in out["flags"]
    assert out["optimized_claim_amount"] < out["policy_snapshot"]["gross_bill_inr"]
    assert 0.35 <= out["approval_probability"] <= 0.97
    assert out["estimated_tpa_time_minutes"] >= 15
    db.table.assert_called()


def test_finance_reconciler_synthetic_negative_delta_mocked_llm():
    db = _fake_supabase_adapter()
    reconciler = FinanceReconciler(db=db)

    llm_out = ReconcileLLMOutput(
        mismatch_category="legitimate_deduction",
        recommendations=["Confirm TPA deduction schedule against policy copy"],
        fraud_risk_score=0.08,
        confidence=0.88,
    )
    reconciler._client.chat.completions.create = MagicMock(return_value=llm_out)

    settlement = SettlementLetterExtraction(
        utr_number="UTR123456789",
        settlement_amount=85_000,
        final_payable=72_000,
        tds_amount=1_000,
        deductions=[
            {"description": "Copay", "amount": 5000, "reason": "Policy copay"},
        ],
        confidence=0.9,
    )

    out = reconciler.reconcile(
        "synthetic-adm-002",
        85_000,
        settlement,
        {"room_charges": 40_000, "medicines": 15_000},
        [{"text": "Type 2 diabetes", "icd10_code": "E11.9"}],
        patient_id="synthetic-patient-002",
        requesting_user_id="synthetic-user",
    )

    assert out["expected_amount"] == 85_000
    assert out["received_amount"] == 72_000
    assert out["delta"] == pytest.approx(-13_000)
    assert out["raise_flag"] is True
    assert out["mismatch_category"] == "legitimate_deduction"
    assert out["reconciliation_id"]
    assert isinstance(out["deductions_analysis"], list)
    reconciler._client.chat.completions.create.assert_called_once()


def test_synthetic_chain_optimizer_then_finance_same_admission():
    """Lightweight 'stages 6 → 9' narrative on synthetic numbers (mocked LLM)."""
    db = _fake_supabase_adapter()
    opt = DischargeOptimizer(db=db)
    fr = FinanceReconciler(db=db)
    fr._client.chat.completions.create = MagicMock(
        return_value=ReconcileLLMOutput(
            mismatch_category="coding_error",
            recommendations=["Resubmit with primary ICD aligned to package"],
            fraud_risk_score=0.15,
            confidence=0.82,
        )
    )

    bill = BillBreakdown(
        room_charges=50_000,
        medicines=20_000,
        procedures=40_000,
        investigations=15_000,
        doctor_fees=10_000,
        nursing_charges=5_000,
        consumables=3_000,
        total=143_000,
        confidence=0.8,
    )
    policy = {"sum_insured_inr": 600_000}
    opt_out = opt.optimize(
        "synthetic-adm-chain",
        bill,
        policy,
        [],
        los_days=4,
        patient_id="p-chain",
        requesting_user_id="u-chain",
    )

    settlement = SettlementLetterExtraction(
        final_payable=opt_out["optimized_claim_amount"] - 10_000,
        confidence=0.75,
    )
    fin_out = fr.reconcile(
        "synthetic-adm-chain",
        opt_out["optimized_claim_amount"],
        settlement,
        bill.model_dump(),
        [{"text": "CKD", "icd10_code": "N18.3"}],
        patient_id="p-chain",
        requesting_user_id="u-chain",
    )

    assert fin_out["raise_flag"] is True
    assert fin_out["delta"] < 0
