"""
BCAES Canonical Registry Service — orchestration layer consumed by main.py.

Wraps CanonicalRegistryStore + graph.py + validators.py behind a single
object so the FastAPI layer stays thin, matching the pattern already used
by PackageRegistryService / SharedDataRegistryService elsewhere in this repo.
"""
from typing import Dict, List, Optional

from bcaes_registry import graph, validators
from bcaes_registry.models import (
    RegisterObjectRequest,
    RegistryObject,
    RegistryType,
    UpdateObjectRequest,
)
from bcaes_registry.store import CanonicalRegistryStore, DependencyNotFoundError, ObjectNotFoundError

__all__ = ["BCAESRegistryService", "ObjectNotFoundError", "DependencyNotFoundError"]


class BCAESRegistryService:
    def __init__(self) -> None:
        self._store = CanonicalRegistryStore()

    # -- registry CRUD ---------------------------------------------------

    def register(self, registry_type: RegistryType, request: RegisterObjectRequest) -> RegistryObject:
        obj = self._store.register(registry_type, request)
        return self._store.with_derived_consumers(obj)

    def update(self, registry_type: RegistryType, object_id: str, request: UpdateObjectRequest) -> RegistryObject:
        obj = self._store.update(registry_type, object_id, request)
        return self._store.with_derived_consumers(obj)

    def delete(self, registry_type: RegistryType, object_id: str) -> None:
        self._store.delete(registry_type, object_id)

    def get(self, registry_type: RegistryType, object_id: str) -> RegistryObject:
        obj = self._store.get(registry_type, object_id)
        return self._store.with_derived_consumers(obj)

    def list_registry(self, registry_type: RegistryType) -> List[RegistryObject]:
        return [self._store.with_derived_consumers(o) for o in self._store.list_registry(registry_type)]

    def registry_summary(self) -> Dict[str, int]:
        return {rt.value: len(self._store.list_registry(rt)) for rt in RegistryType}

    # -- search / lookup ---------------------------------------------------

    def search(
        self,
        query: Optional[str] = None,
        registry_type: Optional[RegistryType] = None,
        owner: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RegistryObject]:
        results = self._store.search(query=query, registry_type=registry_type, owner=owner, status=status)
        return [self._store.with_derived_consumers(o) for o in results]

    # -- relationship / dependency explorers -----------------------------

    def relationships(self, object_id: str) -> Dict:
        return graph.relationships(self._store, object_id)

    def transitive_dependencies(self, object_id: str) -> Dict:
        return graph.transitive_dependencies(self._store, object_id)

    # -- validation --------------------------------------------------------

    def validate_classification(self) -> Dict:
        return validators.validate_classification(self._store)

    def detect_duplicates(self) -> Dict:
        return validators.detect_duplicates(self._store)

    def validate_ownership(self) -> Dict:
        return validators.validate_ownership(self._store)

    def validate_authority_boundaries(self) -> Dict:
        return validators.validate_authority_boundaries(self._store)

    def validate_version_compatibility(self) -> Dict:
        return validators.validate_version_compatibility(self._store)

    def validate_dependency_integrity(self) -> Dict:
        return validators.validate_dependency_integrity(self._store)

    def capability_reuse_check(self, name: str) -> Dict:
        return validators.capability_reuse_check(self._store, name)

    def validate_architecture(self) -> Dict:
        return validators.run_architecture_validation(self._store)
