import shutil

import pytest

from services.shared_platform_services import (
    SERVICE_CONTRACTS,
    AuthenticationService,
    ConfigurationService,
    IdentityService,
    KnowledgeReferenceService,
    NotificationRegistryService,
    OrganizationService,
    build_shared_service_registry,
)
from services.shared_record_store import SharedRecordValidationError

STORE_DIRS = [
    "test_shared_auth",
    "test_shared_identity",
    "test_shared_orgs",
    "test_shared_config",
    "test_shared_kref",
    "test_shared_notif",
]


@pytest.fixture(autouse=True)
def clean_stores():
    for d in STORE_DIRS:
        shutil.rmtree(d, ignore_errors=True)
    yield
    for d in STORE_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def test_authentication_service_requires_subject_and_provider():
    service = AuthenticationService(store_dir="test_shared_auth")
    with pytest.raises(SharedRecordValidationError):
        service.register("auth-1", {"provider": "google"}, actor="kavy", reason="init")
    record = service.register(
        "auth-1", {"subject_id": "id-1", "provider": "google"}, actor="kavy", reason="init"
    )
    assert record.dataset == "authentication"


def test_identity_service_requires_display_name():
    service = IdentityService(store_dir="test_shared_identity")
    record = service.register("id-1", {"display_name": "Kavy"}, actor="kavy", reason="init")
    assert record.payload["display_name"] == "Kavy"


def test_organization_service_requires_name():
    service = OrganizationService(store_dir="test_shared_orgs")
    record = service.register("org-1", {"name": "BHIV"}, actor="kavy", reason="init")
    assert record.dataset == "organizations"


def test_configuration_service_requires_key_and_value():
    service = ConfigurationService(store_dir="test_shared_config")
    with pytest.raises(SharedRecordValidationError):
        service.register("cfg-1", {"key": "max_retries"}, actor="kavy", reason="init")
    record = service.register(
        "cfg-1", {"key": "max_retries", "value": 3}, actor="kavy", reason="init"
    )
    assert record.payload["value"] == 3


def test_knowledge_reference_service_requires_dataset_id():
    service = KnowledgeReferenceService(store_dir="test_shared_kref")
    record = service.register(
        "kref-1", {"dataset_id": "BHIV-DS-MARITIME-AIS-LIVE-001"}, actor="kavy", reason="init"
    )
    assert record.dataset == "knowledge_references"


def test_notification_registry_service_requires_channel_and_template():
    service = NotificationRegistryService(store_dir="test_shared_notif")
    record = service.register(
        "notif-1", {"channel": "email", "template": "welcome"}, actor="kavy", reason="init"
    )
    assert record.dataset == "notifications"


def test_build_shared_service_registry_returns_six_named_services():
    registry = build_shared_service_registry()
    assert set(registry.keys()) == {
        "authentication",
        "identity",
        "organizations",
        "configuration",
        "knowledge-references",
        "notifications",
    }


def test_service_contracts_cover_all_six_services():
    assert set(SERVICE_CONTRACTS.keys()) == {
        "authentication",
        "identity",
        "organizations",
        "configuration",
        "knowledge-references",
        "notifications",
    }
    for name, contract in SERVICE_CONTRACTS.items():
        for required_key in (
            "version", "inputs", "outputs", "dependencies",
            "failure_behaviour", "ownership_boundary",
        ):
            assert required_key in contract, f"{name} contract missing '{required_key}'"
