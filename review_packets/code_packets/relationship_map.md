# Relationship Map — BCAES Canonical Registry Service

## Edge model

One directed edge type: **depends_on**, written on the dependent object's
`dependencies` list. **consumes** (the inverse) is never written — it is
derived by `store.py:consumers_of()` scanning every object for
`dependencies` that name the target.

```
   depends_on (stored)
A ───────────────────► B

   consumes (derived, same edge, opposite view)
A ◄─────────────────── B      (B.consumers includes A)
```

## Live example (captured, see api_responses_bcaes/24-29)

```
dom-3a3090bf1d89 (Ingestion Certification Domain, owner: Kavy)
        ▲
        │ depends_on
        │
cap-198f8afd4901 (Schema Validation, owner: Kavy)
        ▲
        │ depends_on (required_version: "1.0")
        │
psv-9f0eb2861461 (MDU Contract Adapter, owner: Nupur)
```

- `GET /bcaes/relationships/cap-198f8afd4901` → direct edges only:
  depends on the domain, consumed by the platform service.
- `GET /bcaes/dependencies/psv-9f0eb2861461` → transitive walk: both the
  capability and the domain, `depth: 2`.
- `GET /bcaes/registries/domain/objects/dom-3a3090bf1d89` → `consumers:
  ["cap-198f8afd4901"]`, computed on that read, not stored on the domain
  object itself.

## Cross-owner edge (the authority-boundary case)

The platform service above is owned by `Nupur` but depends on a
capability owned by `Kavy`. This is allowed — BCAES does not gate
dependency creation on ownership — but it is *flagged* by
`/bcaes/validate/authority-boundaries` unless `Nupur` also appears in the
platform service's `authority_boundaries`. Evidence of both states
(flagged, then fixed) is captured in `api_responses_bcaes/26`, `33`
(pre-fix architecture validation would show this violation), `35` (the
fix via `PATCH`), and `36` (clean re-validation).

## Cycles

`graph.py:transitive_dependencies()` walks the current path on each
recursive call; if it revisits a node already on that path, the cycle is
recorded in `cycles_detected` and that branch stops, rather than
recursing forever. See `tests/test_bcaes_registry_service.py::
test_transitive_dependencies_detects_cycle` for a two-node cycle
(A depends on B, B depends on A) walked and reported cleanly.
