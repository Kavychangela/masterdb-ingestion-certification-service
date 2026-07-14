import pytest

from services.shared_data_registry_service import (
    SharedDataRegistryService,
    SharedDatasetNotFoundError,
)

EXPECTED_MINIMUM_CATEGORIES = {
    "authentication", "identity", "users", "organizations", "roles",
    "permissions", "uniguru_db", "knowledge_references", "notifications",
    "configuration", "feature_flags", "audit_events", "shared_lookup_tables",
    "localization", "system_settings",
}


def test_registry_declares_all_minimum_categories():
    service = SharedDataRegistryService()
    names = {entry["name"] for entry in service.list_all()}
    assert EXPECTED_MINIMUM_CATEGORIES.issubset(names)


def test_every_entry_declares_all_required_metadata():
    service = SharedDataRegistryService()
    for entry in service.list_all():
        for field in (
            "purpose", "owner", "consumers", "update_policy",
            "lifecycle", "dependency_map", "implemented", "service_endpoint",
        ):
            assert field in entry, f"{entry['name']} missing '{field}'"
        assert entry["purpose"], f"{entry['name']} has empty purpose"
        assert entry["owner"], f"{entry['name']} has empty owner"


def test_get_known_dataset():
    service = SharedDataRegistryService()
    entry = service.get("identity")
    assert entry["name"] == "identity"


def test_get_unknown_dataset_raises():
    service = SharedDataRegistryService()
    with pytest.raises(SharedDatasetNotFoundError):
        service.get("does-not-exist")


def test_filter_by_consumer_tantra():
    service = SharedDataRegistryService()
    results = service.filter_by_consumer("TANTRA")
    assert len(results) > 0
    assert all(
        any("tantra" in c.lower() for c in entry["consumers"]) for entry in results
    )


def test_implemented_only_matches_live_services():
    service = SharedDataRegistryService()
    implemented = {e["name"] for e in service.implemented_only()}
    assert implemented == {
        "authentication", "identity", "organizations",
        "knowledge_references", "notifications", "configuration",
    }
