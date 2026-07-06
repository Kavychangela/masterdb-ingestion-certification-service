# Review Packet

## Summary

This sprint converges MASTERDB from a validation/certification boundary
into the canonical knowledge platform for the BHIV ecosystem. Added the
Knowledge Package Lifecycle Manager / Dataset Registry, the Knowledge
Object & Provenance Engine (consuming MDU semantics through a placeholder
adapter), and the Retrieval Readiness & Evidence Service, plus the
expanded Registry API, tests, and documentation this requires.

## Implemented — This Sprint

- `PackageRegistryService` (Dataset Registry, lifecycle transitions,
  history, replay)
- `KnowledgeObjectService` (Knowledge Object / Provenance, lineage,
  parent/child validation, version compatibility)
- `MDUContractAdapter` (placeholder consumption boundary for the
  not-yet-finalized MDU contract)
- `RetrievalReadinessService` (retrieval rule evaluation, replayable
  `RetrievalEvidence`, corrective actions)
- 7 required Registry API endpoints + 1 supporting endpoint
  (`POST /packages/{package_id}/knowledge-object`)
- New unit + API integration tests for all of the above
- `MDU_INTERFACE_CONTRACT.md` (Phase 5 deliverable)
- Updated `README.md`, `ARCHITECTURE.md`, `API_DOCUMENTATION.md`,
  `HANDOVER.md`

## Implemented — Prior Sprint (unchanged this round)

- `ValidationService`
- `CertificationService`
- `IngestionDecisionService`
- `ReportService`
- FastAPI REST API
- Auditable certification state machine
- JSON artifact persistence
- Unit tests and API integration tests
- Certified and rejected sample reports

## API Surface

Validation & Certification:

- `POST /validate`
- `POST /certify`
- `GET /status/{dataset_id}`
- `GET /report/{dataset_id}`

MASTERDB Registry (new):

- `POST /packages/register`
- `POST /packages/promote`
- `POST /packages/deprecate`
- `GET /packages/{package_id}`
- `GET /packages/{package_id}/lineage`
- `GET /packages/{package_id}/retrieval`
- `GET /packages/{package_id}/history`
- `POST /packages/{package_id}/knowledge-object` (supporting endpoint, not
  in the original 7 but required to populate lineage for meaningful
  retrieval assessments)

## Certification Rules

Validation always transitions `NEW -> VALIDATED` when checks complete.

Verification transitions `VALIDATED -> VERIFIED` only when:

- Integrity score is at least `75`
- No risk flags exist
- Metadata score is at least `80`
- Provenance score is at least `80`
- Integrity boundary score is at least `80`

Certification transitions `VERIFIED -> CERTIFIED` only when:

- Classification is `Trusted`
- Integrity score is at least `90`
- No risk flags exist
- No recommendations remain

Any failed certification rule transitions to `REJECTED`.

## Knowledge Package Lifecycle Rules

Allowed graph (see `models.PACKAGE_LIFECYCLE_GRAPH`):

`REGISTERED -> INGESTED -> VALIDATED -> VERIFIED -> CERTIFIED ->
RETRIEVAL_READY`, with `DEPRECATED` reachable from any non-terminal state
and `ARCHIVED` reachable only from `DEPRECATED`. `ARCHIVED` is terminal.
Every transition not present in the graph is rejected with a `400` and is
never appended to `history`.

## Retrieval Readiness Rules

- `PACKAGE_CERTIFIED`: lifecycle status is `CERTIFIED` or `RETRIEVAL_READY`.
- `NOT_DEPRECATED_OR_ARCHIVED`: lifecycle status is not `DEPRECATED` or
  `ARCHIVED`.
- `METADATA_COMPLETE`: `board`, `medium`, `language`, `owner`, and
  `schema_version` are all present.
- `LINEAGE_REGISTERED`: a `KnowledgeObject` with a `source_reference` is
  registered for the package.

Status derivation: failing either of the first two rules yields
`NOT_RETRIEVABLE`; failing `METADATA_COMPLETE` or `LINEAGE_REGISTERED`
(while certified and active) yields `PARTIALLY_RETRIEVABLE`; passing all
four while lifecycle status is `CERTIFIED` yields `RETRIEVABLE`; passing all
four while lifecycle status is `RETRIEVAL_READY` yields
`CERTIFIED_RETRIEVABLE`.

## Test Evidence

**This environment has no network access, so `fastapi`/`pydantic` could not
be installed here to execute the suite.** All new modules were syntax
checked with `python -m py_compile` and reviewed line-by-line against the
existing service's established patterns (which already depend on the same
libraries per `requirements.txt`). Run this in an environment with
dependencies installed to get real pass/fail results:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

Expected new test files: `tests/test_package_registry_service.py`,
`tests/test_knowledge_object_service.py`,
`tests/test_retrieval_readiness_service.py`, `tests/test_registry_api.py`,
in addition to the pre-existing suite.

## Risk Notes

- Artifact storage is file-based for this handoff, consistent with the
  existing `ArtifactStore` pattern (now reused for registry, knowledge
  object, and retrieval evidence stores under different directories). A
  future platform can replace it without changing service logic.
- `KnowledgeObjectService` currently mirrors a placeholder shape for MDU's
  Knowledge Object contract rather than consuming a finalized one — see
  `MDU_INTERFACE_CONTRACT.md` Known Gaps. This is intentional per the sprint
  brief ("create adapter interfaces with clear placeholders") and should be
  revisited once Nupur publishes the real contract.
- Version compatibility currently checks major-version equality only
  (`schema_version` prefix before the first `.`); this is a placeholder
  rule pending MDU's actual compatibility policy.
- Requests currently pass local paths. Upload handling can be added at the
  API boundary if future ingestion pipelines require multipart packages.
- Existing validators are deterministic but simple; deeper semantic
  validation can be added behind `ValidationService`.
- Test suite could not be executed in this sandbox (no network to install
  dependencies) — see Test Evidence above.

## Reviewer Checklist

- Confirm no business logic remains in `main.py`.
- Confirm API responses are JSON-only.
- Confirm certification transitions are auditable.
- Confirm rejected reports include rejection reasons.
- Confirm sample reports cover certified and rejected outcomes.
- Confirm non-goals were not implemented (no embeddings, vector DB, RAG,
  runtime reasoning, or invented canonical schema/ontology semantics).
- Confirm illegal lifecycle transitions are rejected and never recorded.
- Confirm every lifecycle transition records actor, reason, and timestamp.
- Confirm `PackageRegistryService.replay()` detects drift between stored
  status and transition history.
- Confirm retrieval readiness never reports `CERTIFIED_RETRIEVABLE` without
  both `RETRIEVAL_READY` lifecycle status and registered lineage.
- Confirm `KnowledgeObjectService` does not redefine Knowledge Object,
  Provenance, or Lineage semantics beyond the documented placeholder.
- Run `python -m pip install -r requirements.txt && python -m pytest` in a
  networked environment before merging, since it could not be run here.

