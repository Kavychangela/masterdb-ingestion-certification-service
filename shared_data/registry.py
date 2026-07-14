"""
Phase 1 — Shared Data Service Registry (Task 4: Shared Data Services &
MASTERDB Convergence).

Canonical, product-agnostic registry of reusable ecosystem datasets that
MASTERDB is responsible for as the shared operational data layer sitting
between Product Databases and MDU. This module is documentation-as-code:
it is the single source of truth consumed by SharedDataRegistryService
(services/shared_data_registry_service.py) and mirrored in
MASTERDB_SHARED_DATA_ARCHITECTURE.md.

Ownership note: entries owned by "MASTERDB" are owned as *storage /
versioning / audit infrastructure* for that dataset, not as semantic or
business authority over its contents. MASTERDB does not redefine MDU's
canonical schema/provenance/lineage semantics anywhere in this registry —
see the `knowledge_references` entry, which is the one dataset that points
at MDU-owned content rather than storing it.

`implemented=True` entries have a live Phase 2 service contract and Phase 4
runtime API (see services/shared_platform_services.py and the /shared/*
routes in main.py). `implemented=False` entries are registered/designed per
Phase 1 but do not yet have a runtime service — this mirrors real
ecosystem rollout, where the registry is deliberately broader than what has
been built out at any given point in time, without ever duplicating a
product database's own private tables.
"""
from typing import Any, Dict, List, TypedDict


class SharedDatasetDefinition(TypedDict):
    name: str
    purpose: str
    owner: str
    consumers: List[str]
    update_policy: str
    lifecycle: str
    dependency_map: List[str]
    implemented: bool
    service_endpoint: str  # "" if not yet implemented as a runtime service


SHARED_DATA_REGISTRY: List[SharedDatasetDefinition] = [
    {
        "name": "authentication",
        "purpose": (
            "Shared record of authentication credential/session references "
            "so individual products don't each build their own credential "
            "store."
        ),
        "owner": "MASTERDB",
        "consumers": ["TANTRA", "UniGuru", "Product Databases", "Authentication Services"],
        "update_policy": "Write-on-auth-event; append-only audit trail per record.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["identity"],
        "implemented": True,
        "service_endpoint": "/shared/authentication",
    },
    {
        "name": "identity",
        "purpose": (
            "Canonical identity/user profile records shared across the "
            "ecosystem (distinct from any single product's private user "
            "table)."
        ),
        "owner": "MASTERDB",
        "consumers": ["TANTRA", "UniGuru", "Product Databases", "Authentication Services"],
        "update_policy": "Write-on-profile-change; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": True,
        "service_endpoint": "/shared/identity",
    },
    {
        "name": "users",
        "purpose": (
            "Cross-product user membership / role-assignment records "
            "(distinct from `identity`, which is the profile itself)."
        ),
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-membership-change; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["identity", "organizations"],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "organizations",
        "purpose": (
            "Shared organization/tenant records reusable across products "
            "instead of each product modeling its own."
        ),
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-org-change; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["identity"],
        "implemented": True,
        "service_endpoint": "/shared/organizations",
    },
    {
        "name": "roles",
        "purpose": "Reusable role definitions available to any product's authorization model.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "Authentication Services"],
        "update_policy": "Low-frequency write; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "permissions",
        "purpose": "Reusable permission definitions, composable into roles by consuming products.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "Authentication Services"],
        "update_policy": "Low-frequency write; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["roles"],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "uniguru_db",
        "purpose": (
            "Shared operational data specific to UniGuru that benefits "
            "from cross-product reuse (not UniGuru's private application "
            "database)."
        ),
        "owner": "MASTERDB",
        "consumers": ["UniGuru", "TANTRA"],
        "update_policy": "Product-driven write; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "knowledge_references",
        "purpose": (
            "Lightweight pointers (dataset_id / package_id) into MDU-owned "
            "knowledge. MASTERDB stores the reference only, never the "
            "canonical schema/provenance/lineage content itself."
        ),
        "owner": "MASTERDB (pointer only) / MDU (referenced content)",
        "consumers": ["TANTRA", "UniGuru", "Product Databases"],
        "update_policy": "Write-on-reference-creation; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["MDU:schema", "MDU:provenance"],
        "implemented": True,
        "service_endpoint": "/shared/knowledge-references",
    },
    {
        "name": "notifications",
        "purpose": "Shared notification/event delivery records and templates reusable across products.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-send; append-only audit trail.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": ["identity"],
        "implemented": True,
        "service_endpoint": "/shared/notifications",
    },
    {
        "name": "configuration",
        "purpose": "Shared key/value configuration reusable across products (not product-private config).",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-change; versioned, replay-safe.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": True,
        "service_endpoint": "/shared/configuration",
    },
    {
        "name": "feature_flags",
        "purpose": "Shared feature-flag state reusable across products.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-toggle; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "audit_events",
        "purpose": (
            "Cross-cutting audit log of shared-platform events, distinct "
            "from each dataset's own per-record history."
        ),
        "owner": "MASTERDB",
        "consumers": ["All products (read-only)", "TANTRA"],
        "update_policy": "Append-only.",
        "lifecycle": "REGISTERED (append-only; never updated or deprecated)",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "shared_lookup_tables",
        "purpose": (
            "Reusable enumerations/lookup values (e.g. country codes, "
            "board types) shared across products."
        ),
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Low-frequency write; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "localization",
        "purpose": "Shared translation/locale strings reusable across products.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Write-on-translation-update; versioned.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
    {
        "name": "system_settings",
        "purpose": "Shared, low-churn system-level settings distinct from per-product `configuration`.",
        "owner": "MASTERDB",
        "consumers": ["Product Databases", "TANTRA", "UniGuru"],
        "update_policy": "Low-frequency write; versioned, replay-safe.",
        "lifecycle": "REGISTERED -> UPDATED* -> DEPRECATED",
        "dependency_map": [],
        "implemented": False,
        "service_endpoint": "",
    },
]


def get_dataset(name: str) -> Dict[str, Any]:
    for entry in SHARED_DATA_REGISTRY:
        if entry["name"] == name:
            return dict(entry)
    raise KeyError(f"No shared dataset definition named '{name}'.")
