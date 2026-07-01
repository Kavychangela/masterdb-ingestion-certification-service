from pathlib import Path

from services.artifact_store import ArtifactStore
from services.validation_service import ValidationService


ROOT = Path(__file__).resolve().parents[1]


def test_validation_report_contains_replayable_artifacts(tmp_path):
    service = ValidationService(artifact_store=ArtifactStore(str(tmp_path)))

    report = service.validate(
        dataset_path=str(ROOT / "datasets" / "certifiable_sample.csv"),
        metadata_path=str(ROOT / "datasets" / "metadata.json"),
        dataset_id="certifiable",
    )

    assert report["dataset_id"] == "certifiable"
    assert report["state"] == "VALIDATED"
    assert report["integrity_score"] == 100
    assert report["classification"] == "Trusted"
    assert report["risk_flags"] == []
    assert report["audit_trail"][0]["to_state"] == "VALIDATED"


def test_validation_flags_metadata_and_integrity_failures(tmp_path):
    service = ValidationService(artifact_store=ArtifactStore(str(tmp_path)))

    report = service.validate(
        dataset_path=str(ROOT / "datasets" / "sample.csv"),
        metadata_path=str(ROOT / "datasets" / "incomplete_metadata.json"),
        dataset_id="failing",
    )

    assert "METADATA_GAP" in report["risk_flags"]
    assert "PROVENANCE_GAP" in report["risk_flags"]
    assert "INTEGRITY_BOUNDARY_VIOLATION" in report["risk_flags"]
    assert report["validation_results"]["metadata"]["missing_fields"]

