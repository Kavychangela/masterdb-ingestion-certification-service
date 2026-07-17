# Validation Flow — BCAES Canonical Registry Service

## Execution order and independence

`bcaes_registry/validators.py:CHECKS` lists six checks, each a pure
function `(store) -> {check, passed, violations}`. `run_architecture_validation`
runs all six, unconditionally — a failure in one does not skip the others,
so a single call always surfaces every problem in the current state, not
just the first one hit.

```
run_architecture_validation(store)
  ├─ validate_classification(store)          -> always passes by construction
  ├─ detect_duplicates(store)                 -> duplicate id, duplicate name-in-registry
  ├─ validate_ownership(store)                 -> missing owner / missing authority_boundaries
  ├─ validate_authority_boundaries(store)      -> undeclared cross-owner dependency
  ├─ validate_version_compatibility(store)     -> negotiate_version() per pinned dependency
  └─ validate_dependency_integrity(store)      -> every dependency id still resolves
        │
        ▼
  aggregate {passed, checks[], object_count, replay_hash}
```

## Replay safety — how it's actually proven, not just claimed

Every check above reads `store.all_objects()` and nothing else — no
`datetime.now()`, no random ids inside the check (ids are already fixed by
the time a check runs), no I/O. `run_architecture_validation` hashes the
full result payload (`sort_keys=True` JSON) with SHA-256. Two calls
against unchanged state therefore produce an identical `replay_hash` by
construction, not by a separate "replay" code path re-deriving the same
answer a different way.

**Live proof** (`api_responses_bcaes/36` and `37`): two consecutive
`GET /bcaes/validate/architecture` calls against the same three-object
state both returned
`replay_hash: 5bf16c56df27180b2b332414e3c3eb4381c576e223aa3b1bf6a784cd04883db0`.
A `diff` of the two raw response files is byte-identical (captured in
`runtime_bcaes/`). Automated coverage of the same property:
`tests/test_bcaes_registry_service.py::
test_architecture_validation_is_replay_safe` and
`test_architecture_validation_hash_changes_when_state_changes` (the
negative case — the hash *must* change when state changes, or it isn't
proving anything).

## Individually queryable checks

Each of the six checks is also exposed standalone
(`/bcaes/validate/classification`, `/duplicates`, `/ownership`,
`/authority-boundaries`, `/version-compatibility`,
`/dependency-integrity`) so a caller can ask one focused question without
paying for (or parsing) the full aggregate — useful for a CI step that
only cares about, say, duplicate detection.

## End-to-end failure → fix → pass, captured live

1. Registered a platform service (owner `Nupur`) depending on a
   capability (owner `Kavy`) without declaring `Kavy` in its authority
   boundaries — `api_responses_bcaes/26`.
2. `/bcaes/validate/architecture` returned `passed: false` with one
   `authority_boundaries` violation naming both ids and both owners.
3. `PATCH` added `Kavy` to the platform service's `authority_boundaries`
   — `api_responses_bcaes/35`.
4. Re-ran `/bcaes/validate/architecture` — `passed: true`, all six checks
   green — `api_responses_bcaes/36`.

This is the same flow the Duplicate Detection and Dependency Integrity
checks would produce for their respective violation types; only Authority
Boundaries was walked end-to-end here for evidence brevity, since the
underlying pattern (flag → PATCH → re-validate → confirm) is identical
across all six checks and is exercised for the others in the automated
test suite.
