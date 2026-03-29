from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from .extraction_pipeline import (
        DiagnosisReportExtraction,
        IdProofExtraction,
        ReferralExtraction,
    )


class ABHALookupService:
    def __init__(self, db: Any):
        self.db = db

    def resolve_demographics(
        self, abha_id: Optional[str], patient_id: str
    ) -> Tuple[dict, str]:
        """
        Attempt to fetch authoritative demographics from the ABHA registry.
        Returns (authority_data, source) where source is 'abha' or 'hospital_db'.
        Stub: returns hospital DB row directly.
        """
        resp = (
            self.db.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        data = resp.data or {}
        source = "abha" if data.get("abha_verified") else "hospital_db"
        return data, source

    def merge_with_extraction(
        self, authority_data: dict, id_proof: IdProofExtraction
    ) -> IdProofExtraction:
        """Overlay verified authority fields onto the extraction result."""
        if not authority_data:
            return id_proof
        overrides: dict = {}
        if authority_data.get("patient_name"):
            overrides["patient_name"] = authority_data["patient_name"]
        if authority_data.get("abha_id"):
            overrides["abha_id"] = authority_data["abha_id"]
        if not overrides:
            return id_proof
        return id_proof.model_copy(update=overrides)

    def build_enhanced_identity_json(
        self,
        id_proof: IdProofExtraction,
        diag: DiagnosisReportExtraction,
        referral: ReferralExtraction,
        identity_source: str,
        documents_verified: bool = False,
    ) -> dict:
        return {
            "identity_source": identity_source,
            "documents_verified": documents_verified,
            "patient_name": id_proof.patient_name if id_proof else None,
            "abha_id": id_proof.abha_id if id_proof else None,
            "id_proof_type": id_proof.id_proof_type.value
                if id_proof and id_proof.id_proof_type else None,
        }
