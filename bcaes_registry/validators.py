"""
BCAES Canonical Registry — validation engine.

Each check is a pure function of the store's current state: same state in,
same report out, every time. That is what makes /bcaes/validate/architecture
replay-safe (see review_packets/ replay evidence) without any extra
bookkeeping — determinism falls out of "no hidden mutable state, no
randomness, no wall-clock-dependent logic in the checks themselves".
"""
import hashlib
import json
from typing import Dict, List

from bcaes_registry.store import CanonicalRegistryStore
from services.shared_version_compatibility import negotiate_version


def validate_classification(store: CanonicalRegistryStore) -> Dict:
    """Every object's classification must equal the registry it lives in
    (see models.py docstring) — i.e. exactly one primary classification,
    always. Structurally guaranteed at registration time; this check exists
    to produce reviewable evidence and to catch any object that somehow
    ended up inconsistent (e.g. hand-edited store state)."""
    violations = [
        {"id": o.id, "registry_type": o.registry_type.value,
         "classification": o.classification.value}
        for o in store.all_objects()
        if o.classification != o.registry_type
    ]
    return {"check": "classification", "passed": not violations, "violations": violations}


def detect_duplicates(store: CanonicalRegistryStore) -> Dict:
    """No two objects in the same registry may share a name (case- and
    whitespace-insensitive) — this is the 'no duplicate reusable
    capabilities' rule generalized to all eleven registries."""
    violations: List[Dict] = []
    all_objects = store.all_objects()

    seen_ids: Dict[str, str] = {}
    for o in all_objects:
        if o.id in seen_ids:
            violations.append({"type": "duplicate_id", "id": o.id})
        seen_ids[o.id] = o.registry_type.value

    by_registry: Dict[str, Dict[str, List[str]]] = {}
    for o in all_objects:
        key = o.name.strip().lower()
        by_registry.setdefault(o.registry_type.value, {}).setdefault(key, []).append(o.id)

    for registry_type, names in by_registry.items():
        for name, ids in names.items():
            if len(ids) > 1:
                violations.append(
                    {"type": "duplicate_name", "registry_type": registry_type,
                     "name": name, "ids": sorted(ids)}
                )
    return {"check": "duplicates", "passed": not violations, "violations": violations}


def validate_ownership(store: CanonicalRegistryStore) -> Dict:
    """'No hidden ownership' — every object must declare a non-empty owner
    and at least one authority boundary."""
    violations = []
    for o in store.all_objects():
        if not o.owner or not o.owner.strip():
            violations.append({"id": o.id, "reason": "missing_owner"})
        if not o.authority_boundaries:
            violations.append({"id": o.id, "reason": "missing_authority_boundaries"})
    return {"check": "ownership", "passed": not violations, "violations": violations}


def validate_authority_boundaries(store: CanonicalRegistryStore) -> Dict:
    """'No authority drift' — if an object depends on an object owned by a
    different team, the dependent must explicitly list that owner in its
    own authority_boundaries. This does not grant or enforce access (that
    is GC Team's governance layer); it only flags undeclared cross-owner
    dependencies for review."""
    violations = []
    for o in store.all_objects():
        for dep in o.dependencies:
            try:
                dep_obj = store.get_by_id(dep.id)
            except Exception:
                continue
            if dep_obj.owner != o.owner and dep_obj.owner not in o.authority_boundaries:
                violations.append(
                    {"id": o.id, "owner": o.owner, "depends_on": dep.id,
                     "dependency_owner": dep_obj.owner,
                     "reason": "cross_owner_dependency_not_declared"}
                )
    return {"check": "authority_boundaries", "passed": not violations, "violations": violations}


def validate_version_compatibility(store: CanonicalRegistryStore) -> Dict:
    """For every dependency edge that pins a required_version, negotiate it
    against the dependency's current version using the same policy already
    used for shared-service negotiation (services/shared_version_compatibility.py)."""
    violations = []
    for o in store.all_objects():
        for dep in o.dependencies:
            if not dep.required_version:
                continue
            try:
                dep_obj = store.get_by_id(dep.id)
            except Exception:
                continue
            result = negotiate_version(dep.required_version, dep_obj.version)
            if not result["compatible"]:
                violations.append(
                    {"id": o.id, "depends_on": dep.id,
                     "required_version": dep.required_version,
                     "actual_version": dep_obj.version,
                     "reason": result["reason"]}
                )
    return {"check": "version_compatibility", "passed": not violations, "violations": violations}


def validate_dependency_integrity(store: CanonicalRegistryStore) -> Dict:
    """Every declared dependency id must resolve to a real object.
    Re-verified on demand (registration already enforces this) so the
    check remains meaningful even after direct store edits."""
    violations = []
    for o in store.all_objects():
        for dep in o.dependencies:
            try:
                store.get_by_id(dep.id)
            except Exception:
                violations.append({"id": o.id, "missing_dependency": dep.id})
    return {"check": "dependency_integrity", "passed": not violations, "violations": violations}


def capability_reuse_check(store: CanonicalRegistryStore, name: str) -> Dict:
    """Search the Capability Registry for existing capabilities with the
    same or a similar name, before a new one is registered."""
    from bcaes_registry.models import RegistryType

    q = name.strip().lower()
    capabilities = store.list_registry(RegistryType.CAPABILITY)
    exact = [c.id for c in capabilities if c.name.strip().lower() == q]
    similar = [
        c.id for c in capabilities
        if c.id not in exact and (q in c.name.lower() or c.name.lower() in q)
    ]
    return {
        "query": name,
        "exact_matches": exact,
        "similar_matches": similar,
        "reuse_recommended": bool(exact or similar),
    }


CHECKS = [
    validate_classification,
    detect_duplicates,
    validate_ownership,
    validate_authority_boundaries,
    validate_version_compatibility,
    validate_dependency_integrity,
]


def run_architecture_validation(store: CanonicalRegistryStore) -> Dict:
    """Aggregate every check into one deterministic, replay-safe report."""
    results = [check(store) for check in CHECKS]
    passed = all(r["passed"] for r in results)
    payload = {"passed": passed, "checks": results, "object_count": len(store.all_objects())}
    replay_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    payload["replay_hash"] = replay_hash
    return payload
