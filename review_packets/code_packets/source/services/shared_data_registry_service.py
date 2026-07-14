"""
Phase 1 — read surface over the Shared Data Service Registry.

Thin, side-effect-free query layer on top of shared_data/registry.py. Kept
separate from the registry module itself so the registry stays pure data
(easy for Nupur/others to diff) while lookup/filtering logic lives here.
"""
from typing import Any, Dict, List

from shared_data.registry import SHARED_DATA_REGISTRY, get_dataset


class SharedDatasetNotFoundError(KeyError):
    """Raised when a requested dataset name is not in the registry."""


class SharedDataRegistryService:
    def list_all(self) -> List[Dict[str, Any]]:
        return [dict(entry) for entry in SHARED_DATA_REGISTRY]

    def get(self, name: str) -> Dict[str, Any]:
        try:
            return get_dataset(name)
        except KeyError as exc:
            raise SharedDatasetNotFoundError(str(exc)) from exc

    def filter_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        return [
            dict(entry) for entry in SHARED_DATA_REGISTRY
            if owner.lower() in entry["owner"].lower()
        ]

    def filter_by_consumer(self, consumer: str) -> List[Dict[str, Any]]:
        return [
            dict(entry) for entry in SHARED_DATA_REGISTRY
            if any(consumer.lower() in c.lower() for c in entry["consumers"])
        ]

    def implemented_only(self) -> List[Dict[str, Any]]:
        return [dict(entry) for entry in SHARED_DATA_REGISTRY if entry["implemented"]]
