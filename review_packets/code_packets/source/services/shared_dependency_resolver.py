"""
Phase 5 — Cross-service dataset retrieval & missing-dependency handling
(Task 4).

Given a service name + record_id, resolves the record's declared
dependency fields (services/shared_platform_services.py:
DEPENDENCY_FIELDS) against the other shared services, without asserting
any meaning about the referenced record — purely "does this pointer
resolve", not "what does it mean". Missing dependencies are reported, not
hard-failed, matching Task 4 Phase 4's "graceful failures" requirement.
"""
from typing import Any, Dict, List

from services.shared_platform_services import DEPENDENCY_FIELDS
from services.shared_record_store import SharedRecordNotFoundError, SharedRecordStore


class SharedDependencyResolver:
    def __init__(self, service_registry: Dict[str, SharedRecordStore]) -> None:
        self.service_registry = service_registry

    def resolve(self, service_name: str, record_id: str) -> Dict[str, Any]:
        store = self.service_registry[service_name]
        record = store.get(record_id)  # raises SharedRecordNotFoundError if missing

        dependency_fields = DEPENDENCY_FIELDS.get(service_name, {})
        resolved: Dict[str, Any] = {}
        missing: List[str] = []

        for field_name, target_service in dependency_fields.items():
            ref_id = record.payload.get(field_name)
            if not ref_id:
                continue  # dependency field simply not populated on this record
            target_store = self.service_registry.get(target_service)
            if target_store is None:
                missing.append(f"{field_name} -> unknown target service '{target_service}'")
                continue
            try:
                resolved[field_name] = target_store.get(ref_id).model_dump(mode="json")
            except SharedRecordNotFoundError:
                missing.append(f"{field_name}={ref_id} not found in '{target_service}'")

        return {
            "service": service_name,
            "record": record.model_dump(mode="json"),
            "resolved_dependencies": resolved,
            "missing_dependencies": missing,
            "fully_resolved": not missing,
        }
