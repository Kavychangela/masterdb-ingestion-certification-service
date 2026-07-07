import shutil

import pytest

from models import PackageStatus
from services.package_registry_service import PackageRegistryService

STORE_DIR = "test_audit_store"


@pytest.fixture
def registry():
    shutil.rmtree(STORE_DIR, ignore_errors=True)
    reg = PackageRegistryService(store_dir=STORE_DIR)
    yield reg
    shutil.rmtree(STORE_DIR, ignore_errors=True)


def test_audit_completeness_on_healthy_package(registry):
    pkg = registry.register(
        dataset_id="ds-a",
        dataset_version="1.0",
        schema_version="1.0",
        board="maritime",
        medium="ais",
        language="en",
        owner="nupur",
    )
    registry.promote(pkg.package_id, PackageStatus.INGESTED, actor="tester", reason="ingest")

    report = registry.audit_completeness(pkg.package_id)
    assert report["complete"] is True
    assert report["issues"] == []
    assert report["replay_consistent"] is True
    assert report["transition_count"] == 2


def test_audit_completeness_flags_corrupted_history(registry):
    pkg = registry.register(
        dataset_id="ds-b",
        dataset_version="1.0",
        schema_version="1.0",
        board="maritime",
        medium="ais",
        language="en",
        owner="nupur",
    )
    # Simulate corruption: blank out actor/reason on the root transition.
    pkg.history[0].actor = ""
    pkg.history[0].reason = ""
    registry._save(pkg)

    report = registry.audit_completeness(pkg.package_id)
    assert report["complete"] is False
    assert any("actor" in issue for issue in report["issues"])
    assert any("reason" in issue for issue in report["issues"])


def test_replay_matches_stored_status_for_healthy_package(registry):
    pkg = registry.register(
        dataset_id="ds-c",
        dataset_version="1.0",
        schema_version="1.0",
        board="maritime",
        medium="ais",
        language="en",
        owner="nupur",
    )
    registry.promote(pkg.package_id, PackageStatus.INGESTED, actor="tester", reason="ingest")
    registry.promote(pkg.package_id, PackageStatus.VALIDATED, actor="tester", reason="validate")

    replayed = registry.replay(pkg.package_id)
    assert replayed == PackageStatus.VALIDATED
