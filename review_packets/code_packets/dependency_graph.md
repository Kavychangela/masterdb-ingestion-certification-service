# Dependency Graph — BCAES Canonical Registry Service

## Design choice: no NetworkX (explicit, per instruction to keep this simple)

`bcaes_registry/graph.py` does not use a graph library. It reads
`RegistryObject.dependencies` directly off the store and walks it with
plain recursion. This was scoped down deliberately: the Learning Kit
lists NetworkX as something to *study*, not a hard requirement to ship
with, and the registries are read/queried far more often than they're
traversed at depth. See `BCAES_REGISTRY_ARCHITECTURE.md` §3 for the full
rationale and the swap-in seam if this changes later.

## What the module provides

```python
relationships(store, object_id) -> {
    id, name, registry_type,
    dependencies: [{id, required_version}],   # direct only
    consumers: [id, ...],                      # direct only, derived
}

transitive_dependencies(store, object_id) -> {
    id,
    transitive_dependencies: [id, ...],  # de-duplicated, first-seen order
    depth: int,
    cycles_detected: [[id, id, ..., id], ...],  # each inner list is one cycle path
}
```

## Cycle handling

```python
def walk(current, path):
    if current in path:            # revisiting a node already on this
        cycle_edges.append(...)     # branch's path = a cycle; record and stop
        return
    if current in visited:          # already fully explored elsewhere; skip
        return
    visited.add(current)
    ...
    for dep in obj.dependencies:
        walk(dep.id, path + [current])
```

`path` (the current recursion stack) is distinct from `visited` (every
node ever seen) — this is what lets the walk detect *cycles* specifically,
rather than just terminating on any revisit, and it's what keeps a
diamond-shaped dependency graph (A depends on B and C, both B and C
depend on D) from being misreported as a cycle: D is `visited` once
reached via B, so the C branch's `if current in visited` short-circuits
cleanly instead of re-walking or falsely flagging a cycle.

## Determinism

`transitive_dependencies` de-duplicates in first-seen (insertion) order
before returning, so the same starting state always produces the same
`transitive_dependencies` list in the same order — required for the
result to feed cleanly into the replay-safe validation report (§ see
`validation_flow.md`) without introducing its own source of
nondeterminism.

## Test coverage

`tests/test_bcaes_registry_service.py`: multi-hop transitive resolution
(`test_transitive_dependencies_resolve_multiple_hops`), direct-only
relationships (`test_relationships_lists_direct_edges_only`), and cycle
detection (`test_transitive_dependencies_detects_cycle`). Live-captured
transitive-dependency evidence: `api_responses_bcaes/28`.
