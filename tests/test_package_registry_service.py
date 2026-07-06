import pytest

from models import PackageStatus
from services.package_registry_service import (
    InvalidTransitionError,
    PackageNotFoundError,
    PackageRegistryService,
)


def make_service(tmp_path):
    return PackageRegistryService(store_dir=str(tmp_path))


def register_sample(service, dataset_id="ds-1"):
    return service.register(
        dataset_id=dataset_id,
        dataset_version="1.0.0",
        schema_version="2",
        board="AI",
        medium="text",
        language="en",
        owner="kavy",
    )


def test_register_creates_registered_package(tmp_path):
    service = make_service(tmp_path)

    package = register_sample(service)

    assert package.status == PackageStatus.REGISTERED
    assert len(package.history) == 1
    assert package.history[0].to_status == PackageStatus.REGISTERED
    assert package.history[0].actor == "system"


def test_legal_transition_chain_succeeds(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)

    for to_status, reason in [
        (PackageStatus.INGESTED, "Ingestion pipeline completed."),
        (PackageStatus.VALIDATED, "Passed validation rules."),
        (PackageStatus.VERIFIED, "Passed verification gate."),
        (PackageStatus.CERTIFIED, "Certified by CertificationService."),
        (PackageStatus.RETRIEVAL_READY, "Retrieval readiness confirmed."),
    ]:
        package = service.promote(package.package_id, to_status, actor="pipeline", reason=reason)

    assert package.status == PackageStatus.RETRIEVAL_READY
    assert len(package.history) == 6


def test_illegal_transition_is_rejected(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)

    with pytest.raises(InvalidTransitionError):
        service.promote(
            package.package_id,
            PackageStatus.CERTIFIED,
            actor="pipeline",
            reason="Skipping ahead is not allowed.",
        )

    # Rejected transition must not be recorded or change status.
    reloaded = service.get(package.package_id)
    assert reloaded.status == PackageStatus.REGISTERED
    assert len(reloaded.history) == 1


def test_archived_is_terminal(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)
    package = service.deprecate(package.package_id, actor="owner", reason="Superseded.")
    package = service.promote(
        package.package_id, PackageStatus.ARCHIVED, actor="owner", reason="Retention expired."
    )

    with pytest.raises(InvalidTransitionError):
        service.promote(
            package.package_id, PackageStatus.INGESTED, actor="owner", reason="Reactivate."
        )


def test_deprecate_reachable_from_any_active_state(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)
    package = service.promote(package.package_id, PackageStatus.INGESTED, actor="a", reason="r")

    package = service.deprecate(package.package_id, actor="owner", reason="Data quality issue.")

    assert package.status == PackageStatus.DEPRECATED


def test_unknown_package_raises(tmp_path):
    service = make_service(tmp_path)

    with pytest.raises(PackageNotFoundError):
        service.get("does-not-exist")


def test_replay_matches_recorded_history(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)
    package = service.promote(package.package_id, PackageStatus.INGESTED, actor="a", reason="r")
    package = service.promote(package.package_id, PackageStatus.VALIDATED, actor="a", reason="r")

    replayed_status = service.replay(package.package_id)

    assert replayed_status == PackageStatus.VALIDATED


def test_replay_detects_stored_status_drift(tmp_path):
    service = make_service(tmp_path)
    package = register_sample(service)
    package = service.promote(package.package_id, PackageStatus.INGESTED, actor="a", reason="r")

    # Simulate corruption: overwrite stored status without a matching transition.
    corrupted = service.get(package.package_id)
    corrupted.status = PackageStatus.CERTIFIED
    service.store.save(corrupted.package_id, corrupted.model_dump(mode="json"))

    with pytest.raises(InvalidTransitionError):
        service.replay(package.package_id)
