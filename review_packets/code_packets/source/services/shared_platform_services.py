"""
Phase 2 — Shared Service Contracts (Task 4).

Six reusable ecosystem-facing services, each a thin, dataset-specific
wrapper over the generic SharedRecordStore engine
(services/shared_record_store.py). No service here adds business logic,
semantic interpretation, or ontology — each only declares identity (dataset
name) and a minimal required-field contract. Cross-service dependency
resolution lives separately in services/shared_dependency_resolver.py so
that concern doesn't leak into these definitions either.

SERVICE_CONTRACTS below is the machine-readable form of each service's
contract (Inputs / Outputs / Version / Dependencies / Failure Behaviour /
Ownership Boundary), served via GET /shared/contracts. The prose form of
the same contracts lives in MASTERDB_SHARED_DATA_ARCHITECTURE.md — keep
both in sync by hand if either changes.
"""
from typing import Any, Dict

from services.shared_record_store import SharedRecordStore

SHARED_DATA_API_VERSION = "1.0.0"


class AuthenticationService(SharedRecordStore):
    """
    Dataset: authentication credential/session references.

    Ownership boundary: MASTERDB stores and versions credential *records*
    (e.g. auth provider, subject reference) on behalf of consuming
    products. It does not perform authentication itself (no password
    hashing/verification, no token issuance) — that remains each product's
    own concern. MASTERDB is a shared registry, not an identity provider.
    """

    def __init__(self, store_dir: str = "shared_store/authentication") -> None:
        super().__init__(
            dataset="authentication",
            store_dir=store_dir,
            required_fields=["subject_id", "provider"],
        )


class IdentityService(SharedRecordStore):
    """Dataset: canonical identity/user profile records shared across products."""

    def __init__(self, store_dir: str = "shared_store/identity") -> None:
        super().__init__(
            dataset="identity",
            store_dir=store_dir,
            required_fields=["display_name"],
        )


class OrganizationService(SharedRecordStore):
    """
    Dataset: organization/tenant records. May reference an
    `owner_identity_id` in its payload for cross-service resolution — see
    DEPENDENCY_FIELDS below.
    """

    def __init__(self, store_dir: str = "shared_store/organizations") -> None:
        super().__init__(
            dataset="organizations",
            store_dir=store_dir,
            required_fields=["name"],
        )


class ConfigurationService(SharedRecordStore):
    """Dataset: shared configuration / feature-flag-style key-value records."""

    def __init__(self, store_dir: str = "shared_store/configuration") -> None:
        super().__init__(
            dataset="configuration",
            store_dir=store_dir,
            required_fields=["key", "value"],
        )


class KnowledgeReferenceService(SharedRecordStore):
    """
    Dataset: lightweight pointers (dataset_id / package_id) into MDU-owned
    knowledge. MASTERDB stores the *reference* only, never the canonical
    schema/provenance/lineage content itself — that remains MDU's (Nupur's)
    ownership boundary, consumed only via services/mdu_contract_adapter.py.
    """

    def __init__(self, store_dir: str = "shared_store/knowledge_references") -> None:
        super().__init__(
            dataset="knowledge_references",
            store_dir=store_dir,
            required_fields=["dataset_id"],
        )


class NotificationRegistryService(SharedRecordStore):
    """Dataset: notification/event delivery records and templates shared across products."""

    def __init__(self, store_dir: str = "shared_store/notifications") -> None:
        super().__init__(
            dataset="notifications",
            store_dir=store_dir,
            required_fields=["channel", "template"],
        )


# Cross-service dependency declarations: service_name -> {payload_field: target_service}.
# Consumed only by services/shared_dependency_resolver.py for read-time
# resolution (Phase 5 — cross-service dataset retrieval / missing
# dependency handling). Declaring a dependency here is a pointer-lookup
# rule, not a semantic claim about what the referenced record means.
DEPENDENCY_FIELDS: Dict[str, Dict[str, str]] = {
    "organizations": {"owner_identity_id": "identity"},
    "authentication": {"subject_id": "identity"},
    "notifications": {"recipient_identity_id": "identity"},
}


def build_shared_service_registry() -> Dict[str, SharedRecordStore]:
    """
    Instantiates the six shared platform services, keyed by the URL-facing
    service name used under /shared/{service_name}/...
    """
    return {
        "authentication": AuthenticationService(),
        "identity": IdentityService(),
        "organizations": OrganizationService(),
        "configuration": ConfigurationService(),
        "knowledge-references": KnowledgeReferenceService(),
        "notifications": NotificationRegistryService(),
    }


SERVICE_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "authentication": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.subject_id", "payload.provider", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": ["identity (optional, via payload.subject_id)"],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record. Never fabricates or silently drops a record."
        ),
        "ownership_boundary": (
            "MASTERDB stores/versions credential *references* only — not an "
            "identity provider. No password hashing, no token issuance, no "
            "auth decisioning."
        ),
    },
    "identity": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.display_name", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": [],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record."
        ),
        "ownership_boundary": (
            "MASTERDB owns storage/versioning of the shared profile record. "
            "It does not own or infer identity semantics (e.g. verification "
            "status) beyond what a product explicitly writes into payload."
        ),
    },
    "organizations": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.name", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": ["identity (optional, via payload.owner_identity_id)"],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record. GET .../resolve reports a missing dependency rather "
            "than failing the whole request."
        ),
        "ownership_boundary": (
            "MASTERDB owns the shared organization record only; it does not "
            "own product-specific tenant configuration, which stays in each "
            "product's own database."
        ),
    },
    "configuration": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.key", "payload.value", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": [],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record. Replay-safe: GET .../replay recomputes version/state "
            "purely from stored history."
        ),
        "ownership_boundary": (
            "MASTERDB stores shared, cross-product configuration values "
            "verbatim. It does not interpret or apply configuration "
            "(no governance/decision logic on top of a value)."
        ),
    },
    "knowledge-references": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.dataset_id", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": ["MDU (schema/provenance, via MDUContractAdapter — not another shared dataset)"],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record. Does NOT attempt to resolve the referenced MDU content "
            "itself — use /mdu/schema/{dataset_id} or "
            "/mdu/provenance/{dataset_id} for that, which already degrade "
            "gracefully if MDU is unreachable."
        ),
        "ownership_boundary": (
            "MASTERDB stores the *pointer* (dataset_id/package_id) only. "
            "Canonical schema, provenance, and lineage content are owned by "
            "MDU (Nupur) and are never duplicated here."
        ),
    },
    "notifications": {
        "version": SHARED_DATA_API_VERSION,
        "inputs": {
            "register": ["record_id", "payload.channel", "payload.template", "actor", "reason"],
            "update": ["payload", "actor", "reason"],
            "deprecate": ["actor", "reason"],
        },
        "outputs": "SharedRecord — versioned record with full transition/audit history.",
        "dependencies": ["identity (optional, via payload.recipient_identity_id)"],
        "failure_behaviour": (
            "404 if record_id unknown; 409 on duplicate register; 400 on "
            "missing required payload fields or mutation of a deprecated "
            "record. GET .../resolve reports a missing dependency rather "
            "than failing the whole request."
        ),
        "ownership_boundary": (
            "MASTERDB stores shared notification/template records only; it "
            "does not perform delivery (no SMTP/push/SMS sending logic)."
        ),
    },
}
