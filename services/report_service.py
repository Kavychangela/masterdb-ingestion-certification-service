from typing import Any, Dict

from services.artifact_store import ArtifactStore


class ReportService:
    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def get_report(self, dataset_id: str) -> Dict[str, Any]:
        report = self.artifact_store.load(dataset_id)
        if not report:
            raise KeyError(f"No report found for dataset_id={dataset_id}")
        return report

    def get_status(self, dataset_id: str) -> Dict[str, Any]:
        report = self.get_report(dataset_id)
        return {
            "dataset_id": dataset_id,
            "state": report["state"],
            "classification": report["classification"],
            "integrity_score": report["integrity_score"],
            "eligible_for_masterdb": report.get("ingestion_decision", {}).get(
                "eligible_for_masterdb", False
            ),
        }

