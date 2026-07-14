import shutil

import pytest

from services.shared_dependency_resolver import SharedDependencyResolver
from services.shared_platform_services import IdentityService, OrganizationService

STORE_DIRS = ["test_resolver_identity", "test_resolver_orgs"]


@pytest.fixture
def registry():
    for d in STORE_DIRS:
        shutil.rmtree(d, ignore_errors=True)
    reg = {
        "identity": IdentityService(store_dir="test_resolver_identity"),
        "organizations": OrganizationService(store_dir="test_resolver_orgs"),
    }
    yield reg
    for d in STORE_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def test_resolve_with_satisfied_dependency(registry):
    registry["identity"].register("id-1", {"display_name": "Kavy"}, actor="kavy", reason="init")
    registry["organizations"].register(
        "org-1", {"name": "BHIV", "owner_identity_id": "id-1"}, actor="kavy", reason="init"
    )
    resolver = SharedDependencyResolver(registry)
    result = resolver.resolve("organizations", "org-1")

    assert result["fully_resolved"] is True
    assert result["missing_dependencies"] == []
    assert result["resolved_dependencies"]["owner_identity_id"]["record_id"] == "id-1"


def test_resolve_reports_missing_dependency_without_failing(registry):
    registry["organizations"].register(
        "org-2", {"name": "Ghost Org", "owner_identity_id": "id-does-not-exist"},
        actor="kavy", reason="init",
    )
    resolver = SharedDependencyResolver(registry)
    result = resolver.resolve("organizations", "org-2")

    assert result["fully_resolved"] is False
    assert "id-does-not-exist" in result["missing_dependencies"][0]
    # Graceful failure: the base record is still returned even though a
    # dependency is missing.
    assert result["record"]["record_id"] == "org-2"


def test_resolve_with_no_dependency_field_populated(registry):
    registry["organizations"].register("org-3", {"name": "No Owner Set"}, actor="kavy", reason="init")
    resolver = SharedDependencyResolver(registry)
    result = resolver.resolve("organizations", "org-3")

    assert result["fully_resolved"] is True
    assert result["resolved_dependencies"] == {}
    assert result["missing_dependencies"] == []
