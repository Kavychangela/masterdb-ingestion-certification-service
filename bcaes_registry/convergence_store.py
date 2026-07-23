"""
BCAES Production Convergence — store.

Mirrors CanonicalRegistryStore's "one dict, no hidden state" pattern. A
convergence record can only be created for an object id that already
exists in the canonical registry — declaring convergence for something
unregistered would be a second source of truth about what exists, which
is exactly what the registry exists to prevent.
"""
from datetime import datetime, timezone
from typing import Dict, List

from bcaes_registry.convergence_models import ConvergenceRecord, ConvergenceUpdateRequest
from bcaes_registry.store import CanonicalRegistryStore, ObjectNotFoundError


class ConvergenceStore:
    def __init__(self, registry_store: CanonicalRegistryStore) -> None:
        self._registry_store = registry_store
        self._records: Dict[str, ConvergenceRecord] = {}

    def upsert(self, object_id: str, request: ConvergenceUpdateRequest) -> ConvergenceRecord:
        """Merge-patch: only fields explicitly present in the request body
        overwrite the stored record. A team updating `governance_status`
        must not silently reset `sdk_adoption` back to `not_started` just
        because their call didn't mention it — each dimension is owned by
        a different collaborator (see convergence_models docstring)."""
        # Raises ObjectNotFoundError if object_id isn't registered anywhere.
        self._registry_store.get_by_id(object_id)

        existing = self._records.get(object_id)
        data = existing.model_dump() if existing else {"object_id": object_id}
        for field, value in request.model_dump(exclude_unset=True).items():
            data[field] = value
        data["object_id"] = object_id
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        record = ConvergenceRecord(**data)
        self._records[object_id] = record
        return record

    def get(self, object_id: str) -> ConvergenceRecord:
        record = self._records.get(object_id)
        if record is None:
            raise ObjectNotFoundError(f"No convergence record for '{object_id}'.")
        return record

    def all_records(self) -> List[ConvergenceRecord]:
        return list(self._records.values())
