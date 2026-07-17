"""
Relationship graph over registered objects.

Deliberately simple: plain adjacency built from `RegistryObject.dependencies`
at query time, not a NetworkX DiGraph. The store already holds the only
copy of the edges (see store.py), so this module just walks it. If the
registries grow large enough to need real graph algorithms (shortest path,
centrality, etc.) this is the seam to swap in networkx without touching
callers — every function here returns plain dicts/lists.
"""
from typing import Dict, List, Set

from bcaes_registry.store import CanonicalRegistryStore


def relationships(store: CanonicalRegistryStore, object_id: str) -> Dict:
    """Direct dependencies and consumers of a single object."""
    obj = store.get_by_id(object_id)
    return {
        "id": obj.id,
        "name": obj.name,
        "registry_type": obj.registry_type.value,
        "dependencies": [
            {"id": d.id, "required_version": d.required_version}
            for d in obj.dependencies
        ],
        "consumers": store.consumers_of(object_id),
    }


def transitive_dependencies(store: CanonicalRegistryStore, object_id: str) -> Dict:
    """Full dependency chain reachable from `object_id`, with cycle
    protection (a cycle is reported, not followed forever)."""
    store.get_by_id(object_id)  # raises ObjectNotFoundError if missing

    visited: Set[str] = set()
    order: List[str] = []
    cycle_edges: List[List[str]] = []

    def walk(current: str, path: List[str]) -> None:
        if current in path:
            cycle_edges.append(path[path.index(current):] + [current])
            return
        if current in visited:
            return
        visited.add(current)
        try:
            obj = store.get_by_id(current)
        except Exception:
            return
        for dep in obj.dependencies:
            if dep.id != object_id:
                order.append(dep.id)
            walk(dep.id, path + [current])

    walk(object_id, [])
    # de-duplicate while preserving first-seen order (determinism)
    seen: Set[str] = set()
    deduped = []
    for oid in order:
        if oid not in seen:
            seen.add(oid)
            deduped.append(oid)

    return {
        "id": object_id,
        "transitive_dependencies": deduped,
        "depth": len(deduped),
        "cycles_detected": cycle_edges,
    }
