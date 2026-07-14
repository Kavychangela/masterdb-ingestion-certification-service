# Architecture Delta — Task 4

## Before (Task 1–3)

```
Client -> main.py -> {ValidationService, CertificationService,
                       PackageRegistryService, KnowledgeObjectService,
                       RetrievalReadinessService, MDUContractAdapter,
                       TantraInterfaceService, RuntimeDiscoveryService}
                   -> ArtifactStore (JSON files under reports/,
                      registry_store/, knowledge_object_store/,
                      retrieval_evidence_store/)
```

MASTERDB was a certification boundary plus a knowledge-platform runtime
(lifecycle, lineage, retrieval readiness) with two ecosystem-facing
integration surfaces: MDU (consumption only) and TANTRA (façade).

## After (Task 4 — additive)

```
Client -> main.py -> [ everything above, unchanged ]
                   -> shared_data_registry_service -> shared_data/registry.py
                   -> shared_service_registry (6x SharedRecordStore subclasses)
                        -> ArtifactStore (JSON files under shared_store/*)
                   -> shared_dependency_resolver -> shared_service_registry
                   -> shared_negotiate_version (services/shared_version_compatibility.py)
```

A new, parallel layer was added under `/shared/*`. It shares MASTERDB's
existing persistence primitive (`ArtifactStore`) and error-handling
convention (`_error_body` / uniform `{"error": {...}}` contract, reused
as-is — no changes to the exception handlers themselves) but introduces
its own:

- **Generic engine** (`SharedRecordStore`) instead of one bespoke service
  class per dataset — a deliberate simplification versus how
  `PackageRegistryService` / `KnowledgeObjectService` / etc. are each
  hand-written, because the six Task 4 datasets share identical
  versioning/audit/replay semantics and differ only in required fields.
- **Registry-as-data** (`shared_data/registry.py`) — a new pattern for
  this codebase: previously, "what datasets exist" was implicit in which
  service classes existed. Task 4 makes it an explicit, queryable list
  that is broader than what's currently implemented (9 of 15 datasets are
  registered but not yet built), which the old pattern couldn't represent.
- **Cross-service dependency resolution** — new concept, not present in
  Task 1–3 (where `KnowledgeObjectService.lineage()` is the closest analog,
  but that resolves parent/child packages *within* one dataset, not across
  independent shared datasets).

## What did NOT change

- `ValidationService`, `CertificationService`, `PackageRegistryService`,
  `KnowledgeObjectService`, `RetrievalReadinessService`,
  `MDUContractAdapter`, `TantraInterfaceService`, `RuntimeDiscoveryService`
  — zero code changes.
- `PACKAGE_LIFECYCLE_GRAPH`, `PackageStatus`, `CertificationState` and all
  other existing models — zero changes.
- Global exception handlers (`http_exception_handler`,
  `unhandled_exception_handler`) — zero changes; Task 4 routes raise the
  same `HTTPException` type and get the same uniform error body for free.
- All 50 pre-existing tests — pass unmodified (96 total now, 50 original +
  46 new).

## Ownership boundary preserved

The delta introduces no new claim on MDU-owned semantics. The one dataset
that touches MDU-owned content (`knowledge_references`) stores a pointer
only; resolving that pointer still goes through the pre-existing,
untouched `MDUContractAdapter` / `/mdu/*` routes. See
`MASTERDB_SHARED_DATA_ARCHITECTURE.md` §1 and §8 for the full ownership
argument.
