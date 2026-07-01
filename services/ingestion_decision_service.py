from typing import Any, Dict

from models import CertificationState, IngestionDecision, TransitionRecord


class IngestionDecisionService:
    @staticmethod
    def from_report(report: Dict[str, Any]) -> IngestionDecision:
        if "ingestion_decision" in report:
            return IngestionDecision(**report["ingestion_decision"])
        return IngestionDecision(
            dataset_id=report["dataset_id"],
            eligible_for_masterdb=report.get("state") == CertificationState.CERTIFIED,
            state=CertificationState(report.get("state", CertificationState.VALIDATED)),
            classification=report["classification"],
            integrity_score=report["integrity_score"],
            rejection_reasons=[],
            audit_trail=[
                TransitionRecord(**record)
                for record in report.get("audit_trail", [])
            ],
        )

