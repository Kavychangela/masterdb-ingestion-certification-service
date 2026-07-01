from pathlib import Path

from services.artifact_store import ArtifactStore
from services.certification_service import CertificationService
from services.validation_service import ValidationService


ROOT = Path(__file__).resolve().parents[1]


def make_service(tmp_path):
    store = ArtifactStore(str(tmp_path))
    validator = ValidationService(artifact_store=store)
    return CertificationService(validation_service=validator, artifact_store=store)


def test_certifiable_dataset_reaches_certified_state(tmp_path):
    service = make_service(tmp_path)

    report = service.certify(
        dataset_id="certifiable",
        dataset_path=str(ROOT / "datasets" / "certifiable_sample.csv"),
        metadata_path=str(ROOT / "datasets" / "metadata.json"),
    )

    decision = report["ingestion_decision"]
    assert report["state"] == "CERTIFIED"
    assert decision["eligible_for_masterdb"] is True
    assert [item["to_state"] for item in report["audit_trail"]] == [
        "VALIDATED",
        "VERIFIED",
        "CERTIFIED",
    ]


def test_failing_dataset_is_rejected_with_audit_reason(tmp_path):
    service = make_service(tmp_path)

    report = service.certify(
        dataset_id="failing",
        dataset_path=str(ROOT / "datasets" / "sample.csv"),
        metadata_path=str(ROOT / "datasets" / "incomplete_metadata.json"),
    )

    decision = report["ingestion_decision"]
    assert report["state"] == "REJECTED"
    assert decision["eligible_for_masterdb"] is False
    assert decision["rejection_reasons"]
    assert report["audit_trail"][-1]["passed"] is False

