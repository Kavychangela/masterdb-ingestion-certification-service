# Critical Files — BCAES Canonical Registry Service

Per the task brief: "Core execution flow (maximum three critical files)."
These three are sufficient to understand the entire feature without
reading the rest of `bcaes_registry/`.

## 1. `bcaes_registry/models.py`

Read this first. Defines the eleven registry types, the id-prefix scheme,
and the single `RegistryObject` schema every registry shares. The
docstring at the top of the file explains the one non-obvious design
decision (`classification == registry_type`) that everything else depends
on — understand this and the rest of the module reads as a
straightforward CRUD/validation layer on top of it.

## 2. `bcaes_registry/store.py`

The only place state lives (`CanonicalRegistryStore._objects`, one dict
per registry type) and the only place edges are written
(`RegistryObject.dependencies`, set at `register()`/`update()`).
`consumers_of()` — the derivation that makes `consumers` never need to be
written directly — is the key method to understand here.

## 3. `main.py` (BCAES section, appended at end of file)

The FastAPI wiring: 14 thin route handlers that translate HTTP into calls
on `bcaes_registry_service`, plus `_bcaes_registry_type()`, the one helper
that turns an unknown `{registry_type}` path param into a clean `404`
rather than a `422` — matching the existing `_shared_service()` pattern
already used for the Task 4 layer three lines above it in the same file.

## Deliberately not "critical"

`graph.py` and `validators.py` are straightforward once the three files
above are understood — each function in them is a short, independently
readable pure function over `store.py`'s state, documented inline. Start
with the three above; the rest follows.
