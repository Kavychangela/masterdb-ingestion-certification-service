from typing import Any, Dict, List, Optional

from models import CertificationState, IngestionDecision, TransitionRecord
from services.artifact_store import ArtifactStore
from services.validation_service import ValidationService


class CertificationService:
    def __init__(
        self,
        validation_service: Optional[ValidationService] = None,
        artifact_store: Optional[ArtifactStore] = None,
        rules_path: str = "config/validation_rules.json",
    ) -> None:
        self.artifact_store = artifact_store or ArtifactStore()
        self.validation_service = validation_service or ValidationService(
            artifact_store=self.artifact_store
        )
        self.rules_path = rules_path

    def certify(
        self,
        dataset_id: Optional[str] = None,
        dataset_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        report = self._resolve_report(dataset_id, dataset_path, metadata_path)
        audit = [
            TransitionRecord(**record)
            for record in report.get("audit_trail", [])
        ]
        current_state = CertificationState(report.get("state", CertificationState.NEW))
        rejection_reasons: List[str] = []

        current_state = self._transition(
            audit,
            current_state,
            CertificationState.VERIFIED,
            "VALIDATION_SCORE_AND_RISK_GATE",
            self._passes_verification(report),
            "Dataset meets minimum verification score and risk gates.",
            rejection_reasons,
        )

        current_state = self._transition(
            audit,
            current_state,
            CertificationState.CERTIFIED,
            "MASTERDB_CERTIFICATION_GATE",
            current_state == CertificationState.VERIFIED
            and report["classification"] == "Trusted"
            and report["integrity_score"] >= 90
            and not report["risk_flags"]
            and not report["recommendations"],
            "Dataset is trusted, clean, and eligible for MASTERDB ingestion.",
            rejection_reasons,
        )

        decision = IngestionDecision(
            dataset_id=report["dataset_id"],
            eligible_for_masterdb=current_state == CertificationState.CERTIFIED,
            state=current_state,
            classification=report["classification"],
            integrity_score=report["integrity_score"],
            rejection_reasons=rejection_reasons,
            audit_trail=audit,
        )
        report["state"] = decision.state.value
        report["ingestion_decision"] = decision.model_dump(mode="json")
        report["audit_trail"] = [record.model_dump(mode="json") for record in audit]
        return self.artifact_store.save(report["dataset_id"], report)

    def _resolve_report(
        self,
        dataset_id: Optional[str],
        dataset_path: Optional[str],
        metadata_path: Optional[str],
    ) -> Dict[str, Any]:
        if dataset_id:
            report = self.artifact_store.load(dataset_id)
            if report:
                return report
        if not dataset_path:
            raise ValueError("dataset_id was not found; provide dataset_path to certify.")
        return self.validation_service.validate(dataset_path, metadata_path, dataset_id)

    @staticmethod
    def _passes_verification(report: Dict[str, Any]) -> bool:
        results = report["validation_results"]
        return (
            report["integrity_score"] >= 75
            and not report["risk_flags"]
            and results["metadata"]["score"] >= 80
            and results["provenance"]["score"] >= 80
            and results["integrity"]["score"] >= 80
        )

    @staticmethod
    def _transition(
        audit: List[TransitionRecord],
        from_state: CertificationState,
        success_state: CertificationState,
        rule: str,
        passed: bool,
        success_reason: str,
        rejection_reasons: List[str],
    ) -> CertificationState:
        if from_state == CertificationState.REJECTED:
            return from_state
        to_state = success_state if passed else CertificationState.REJECTED
        reason = success_reason if passed else f"{rule} failed."
        if not passed:
            rejection_reasons.append(reason)
        audit.append(
            TransitionRecord(
                from_state=from_state,
                to_state=to_state,
                rule=rule,
                passed=passed,
                reason=reason,
            )
        )
        return to_state
