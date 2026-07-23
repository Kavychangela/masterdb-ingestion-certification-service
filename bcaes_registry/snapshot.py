"""
BCAES Current Reality Snapshot (Volume 7).

Per the task brief: "No manually maintained copies." This module holds no
state of its own — every field is computed on each call from the current
CanonicalRegistryStore and ConvergenceStore. Calling it twice with no
registry changes in between returns identical content (modulo
`generated_at`), the same determinism guarantee `validate_architecture`
gives for its `replay_hash`.
"""
from datetime import datetime, timezone
from typing import Dict

from bcaes_registry import validators
from bcaes_registry.convergence_store import ConvergenceStore
from bcaes_registry.models import RegistryType
from bcaes_registry.store import CanonicalRegistryStore


def generate_snapshot(store: CanonicalRegistryStore, convergence_store: ConvergenceStore) -> Dict:
    registry_summary = {rt.value: len(store.list_registry(rt)) for rt in RegistryType}
    architecture = validators.run_architecture_validation(store)

    records = convergence_store.all_records()
    tracked_object_ids = {r.object_id for r in records}
    all_object_ids = {o.id for o in store.all_objects()}
    untracked = sorted(all_object_ids - tracked_object_ids)

    convergence_overview = {
        "objects_registered": len(all_object_ids),
        "objects_with_convergence_data": len(records),
        "objects_without_convergence_data": len(untracked),
        "untracked_object_ids": untracked,
        "average_maturity_score": (
            round(sum(r.maturity_score for r in records) / len(records), 4)
            if records
            else 0.0
        ),
        "production_ready_count": sum(
            1 for r in records if r.production_readiness.value == "complete"
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registries": registry_summary,
        "total_objects": len(all_object_ids),
        "architecture_validation": {
            "passed": architecture["passed"],
            "replay_hash": architecture["replay_hash"],
            "failing_checks": [c["check"] for c in architecture["checks"] if not c["passed"]],
        },
        "convergence": convergence_overview,
        "scope_note": (
            "Generated entirely from this service's own registry and convergence "
            "state. It does not reach into TANTRA, MDU, Bucket, or InsightFlow — "
            "cross-system reality requires each of those services to register "
            "and update their own objects through the /bcaes API."
        ),
    }
