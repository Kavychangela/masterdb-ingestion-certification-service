import shutil

import pytest

from models import PackageStatus
from services.package_registry_service import PackageRegistryService
from services.runtime_discovery_service import RuntimeDiscoveryService

STORE_DIR = "test_runtime_discovery_store"


@pytest.fixture
def registry():
    shutil.rmtree(STORE_DIR, ignore_errors=True)
    reg = PackageRegistryService(store_dir=STORE_DIR)
    yield reg
    shutil.rmtree(STORE_DIR, ignore_errors=True)


def _register(reg, dataset_id, board, medium, owner="nupur", version="1.0"):
    return reg.register(
        dataset_id=dataset_id,
        dataset_version=version,
        schema_version=version,
        board=board,
        medium=medium,
        language="en",
        owner=owner,
    )


def test_discover_by_board(registry):
    _register(registry, "ds-a", board="maritime", medium="ais")
    _register(registry, "ds-b", board="aviation", medium="adsb")
    discovery = RuntimeDiscoveryService(registry=registry)

    results = discovery.discover(board="maritime")
    assert len(results) == 1
    assert results[0].dataset_id == "ds-a"


def test_discover_by_status(registry):
    pkg = _register(registry, "ds-c", board="maritime", medium="ais")
    registry.promote(pkg.package_id, PackageStatus.INGESTED, actor="tester", reason="test")
    discovery = RuntimeDiscoveryService(registry=registry)

    ingested = discovery.discover(status=PackageStatus.INGESTED)
    registered = discovery.discover(status=PackageStatus.REGISTERED)

    assert len(ingested) == 1
    assert len(registered) == 0


def test_discover_is_deterministically_ordered(registry):
    _register(registry, "ds-1", board="maritime", medium="ais")
    _register(registry, "ds-2", board="maritime", medium="ais")
    _register(registry, "ds-3", board="maritime", medium="ais")
    discovery = RuntimeDiscoveryService(registry=registry)

    first_call = [p.package_id for p in discovery.discover(board="maritime")]
    second_call = [p.package_id for p in discovery.discover(board="maritime")]

    assert first_call == second_call == sorted(first_call)


def test_discover_no_match_returns_empty(registry):
    _register(registry, "ds-x", board="maritime", medium="ais")
    discovery = RuntimeDiscoveryService(registry=registry)

    assert discovery.discover(dataset_id="does-not-exist") == []
