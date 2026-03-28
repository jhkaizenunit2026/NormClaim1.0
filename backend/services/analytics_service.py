"""
NormClaim — Analytics aggregation
Combines in-memory session state with optional Supabase document / feedback counts.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

from models.schemas import AnalyticsSnapshot, ExtractionResult, FeedbackItem, ReconciliationReport


def _flatten_feedback(feedback_by_doc: Dict[str, List[FeedbackItem]]) -> List[FeedbackItem]:
    out: List[FeedbackItem] = []
    for items in feedback_by_doc.values():
        out.extend(items)
    return out


def build_snapshot(
    documents_count: int,
    extractions: Dict[str, ExtractionResult],
    reports: Dict[str, ReconciliationReport],
    feedback_by_doc: Dict[str, List[FeedbackItem]],
    supabase_client: Optional[Any] = None,
) -> AnalyticsSnapshot:
    """Build analytics from live in-memory stores, optionally enriched from Supabase."""
    ex_list = list(extractions.values())
    rep_list = list(reports.values())
    fb_list = _flatten_feedback(feedback_by_doc)

    avg_conf = 0.0
    if ex_list:
        total = 0.0
        n = 0
        for e in ex_list:
            for d in e.diagnoses:
                total += float(d.confidence)
                n += 1
        avg_conf = total / n if n else 0.0

    deltas = [float(r.estimated_claim_delta_inr) for r in rep_list]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
    total_recovered = sum(deltas)
    total_missed = sum(len(r.missed) for r in rep_list)

    correct = sum(1 for f in fb_list if f.was_extraction_correct)
    accuracy = correct / len(fb_list) if fb_list else 0.0

    type_counts: Counter = Counter(
        f.correction_type for f in fb_list if f.correction_type and str(f.correction_type).strip()
    )

    source = "memory"

    if supabase_client is not None:
        try:
            rows = supabase_client.table("documents").select("id").execute().data or []
            if rows:
                documents_count = max(documents_count, len(rows))
                source = "hybrid"
        except Exception:
            pass
        try:
            fb_rows = supabase_client.table("feedback").select("was_correct, correction_type").execute().data or []
            for r in fb_rows:
                ct = (r.get("correction_type") or "").strip()
                if ct:
                    type_counts[ct] += 1
            if fb_rows and not fb_list:
                c = sum(1 for r in fb_rows if r.get("was_correct"))
                accuracy = c / len(fb_rows)
                source = "supabase"
            elif fb_rows:
                source = "hybrid"
        except Exception:
            pass
        try:
            rec_rows = supabase_client.table("reconciliations").select("delta_inr").execute().data or []
            if rec_rows and not rep_list:
                db_deltas = [float(r.get("delta_inr") or 0) for r in rec_rows]
                total_recovered = sum(db_deltas)
                avg_delta = sum(db_deltas) / len(db_deltas) if db_deltas else 0.0
                source = "supabase" if source == "memory" else "hybrid"
        except Exception:
            pass

    return AnalyticsSnapshot(
        total_documents=documents_count,
        total_extractions=len(extractions),
        total_reconciliations=len(reports),
        total_feedback_events=len(fb_list),
        total_missed_diagnoses=total_missed,
        avg_extraction_confidence=round(avg_conf, 4),
        avg_claim_delta_inr=round(avg_delta, 2),
        total_inr_recovered=round(total_recovered, 2),
        extraction_accuracy_rate=round(accuracy, 4),
        correction_type_counts=dict(type_counts),
        data_source=source,
    )
