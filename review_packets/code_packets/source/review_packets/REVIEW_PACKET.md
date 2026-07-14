# Review Packet

## Summary

This sprint converges MASTERDB from an isolated backend into an ecosystem
capability: a live MDU client with contract validation/version negotiation
(Phase 1), a MASTERDB <-> TANTRA runtime interface (Phase 2), a Runtime
Discovery API (Phase 3), and Phase 4 hardening (uniform error contract,
structured logging, replay-consistency/audit-completeness endpoints) — on
top of the existing Knowledge Package Lifecycle, Knowledge Object/Provenance
consumption, and Retrieval Readiness services from the prior sprint.

## Implemented — This Sprint (Ecosystem Integration)

- `MDUClient` (`services/mdu_client.py`) — live HTTP client for MDU's
  schema/provenance/canonical/discovery endpoints, configured via
  `MDU_BASE_URL` / `MDU_API_KEY`.
- `MDUContractAdapter` upgraded with `fetch_schema_contract`,
  `fetch_provenance_contract`, `validate_schema_compatibility`, and a
  deterministic `negotiate_version` rule (exact match / minor-version
  drift / major-version mismatch), with permissive placeholder fallback
  when MDU is unreachable.
- `KnowledgeObjectService.lineage()` now consumes MDU's live provenance
  contract (tagged `mdu_provenance`, source `mdu-live` vs `unavailable`)
  alongside MASTERDB's own parent/child walk.
- `TantraInterfaceService` (`services/tantra_interface_service.py`) — the
  single façade TANTRA integrates against: dataset registration, package
  discovery, retrieval-readiness queries, certification-status queries,
  bundled runtime package lookup.
- `RuntimeDiscoveryService` (`services/runtime_discovery_service.py`) +
  `ArtifactStore.list_all()` — deterministic filtered package discovery by
  `package_id`/`dataset_id`/`board`/`medium`/`version`/`status`.
- Phase 4 hardening: uniform `{"error": {...}}` contract via global FastAPI
  exception handlers, structured logging (registration, transitions, MDU
  requests), `PackageRegistryService.audit_completeness()`, and two new
  endpoints — `GET /packages/{id}/replay`, `GET /packages/{id}/audit`.
- 9 new endpoints: `/mdu/status`, `/mdu/schema/{id}`,
  `/mdu/provenance/{id}`, `/mdu/schema-compatibility/{id}`,
  `/tantra/datasets/register`, `/tantra/packages/{id}/retrieval-readiness`,
  `/tantra/certification/{id}`, `/tantra/packages/{id}/runtime`,
  `/discovery/packages`, plus `/packages/{id}/replay` and
  `/packages/{id}/audit` (11 total).
- New tests: `test_mdu_contract_adapter.py`,
  `test_runtime_discovery_service.py`, `test_tantra_interface_service.py`,
  `test_audit_and_replay.py`.
- `MDU_INTERFACE_CONTRACT.md`, `README.md`, `ARCHITECTURE.md`,
  `API_DOCUMENTATION.md`, `HANDOVER.md` all updated for the above.

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
- `GET /packages/{package_id}/replay` (new — Phase 4)
- `GET /packages/{package_id}/audit` (new — Phase 4)

MDU Integration (new — Phase 1):

- `GET /mdu/status`
- `GET /mdu/schema/{dataset_id}`
- `GET /mdu/provenance/{dataset_id}`
- `GET /mdu/schema-compatibility/{dataset_id}?local_schema_version=...`

TANTRA Runtime Interface (new — Phase 2):

- `POST /tantra/datasets/register`
- `GET /tantra/packages/{package_id}/retrieval-readiness`
- `GET /tantra/certification/{dataset_id}`
- `GET /tantra/packages/{package_id}/runtime`

Runtime Discovery (new — Phase 3):

- `GET /discovery/packages` (filterable by `package_id`, `dataset_id`,
  `board`, `medium`, `version`, `status`)

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

**Full pytest suite executed locally 2026-07-08** (networked environment,
`MDU_BASE_URL`/`MDU_API_KEY` configured against the live MDU service):

```
50 passed, 1 warning in 3.97s
```

The one warning is a `StarletteDeprecationWarning` (`httpx` with
`starlette.testclient` deprecated in favor of `httpx2`) — not a failure,
tracked as a Known Gap below.

One test failure was found and fixed during this run:
`test_adapter_reports_not_live_when_unconfigured` assumed a clean
environment, but with real MDU credentials present in `.env`, `MDUClient`'s
fallback-to-env-var behavior made the test's premise false. Fixed by having
the test explicitly `monkeypatch.delenv("MDU_BASE_URL")` /
`monkeypatch.delenv("MDU_API_KEY")` rather than assuming ambient state —
this is a test-isolation fix, not a change to adapter behavior.

Run yourself with:

```bash
python -m pip install -r requirements.txt
# set MDU_BASE_URL / MDU_API_KEY in .env
python -m pytest -v
```

## Live MDU Verification (confirmed 2026-07-08)

Ad-hoc script `scripts/confirm_mdu_contract.py` was written to call MDU's
real endpoints and diff the response shape against
`MDUContractSnapshot`'s placeholder field assumptions. Run against
`BHIV-DS-MARITIME-AIS-LIVE-001` (resolved UUID
`6f84dede-43f4-488d-8bb4-c17f712d7e1a`). Findings:

**Two real bugs found and fixed as a result:**

1. **`MDUClient.get_dataset_schema()` returns a list, not a dict.** MDU
   returns schema *version history* as a JSON array; the adapter's
   `validate_schema_compatibility()` called `.get()` on it directly, which
   would have raised `AttributeError` on first live use (not caught by the
   existing `MDUUnavailableError` handling). Fixed in
   `mdu_contract_adapter.py` by taking `schema[0]` as current, with a
   TODO to confirm with Nupur whether index 0 is guaranteed newest or
   whether sorting by `frozen_at`/`created_at` is needed.
2. **Canonical ID vs internal UUID mismatch.** MASTERDB's registry stores
   canonical string dataset IDs (e.g. `BHIV-DS-MARITIME-AIS-LIVE-001`), but
   MDU's `/schemas/dataset/{id}` and `/datasets/{id}/provenance` endpoints
   require MDU's internal UUID — passing a canonical ID returns a `422`.
   Fixed by adding `MDUContractAdapter._resolve_mdu_id()`, which resolves a
   canonical ID to MDU's UUID via `/datasets/canonical/{id}` (which does
   accept the canonical string) and caches the mapping. Both bugs were
   verified fixed against the live service, not just unit-tested:

```
>>> fetch_provenance_contract('BHIV-DS-MARITIME-AIS-LIVE-001')
[{'id': 'ae6b1aee-...', 'event_type': 'ORIGIN', ...}, ... 5 events total]

>>> validate_schema_compatibility('BHIV-DS-MARITIME-AIS-LIVE-001', '1.0.0')
{'source': 'mdu-live', 'mdu_schema_version': '1.0.0',
 'compatible': True, 'negotiation': 'exact_match'}
```

**Field-level confirmation against `MDUContractSnapshot`:**

- `source_reference` — confirmed present on every provenance event, exact
  name match. Flipped to `confirmed_by_mdu=True`.
- `knowledge_object_id`, `lineage_reference`, `derivation_path` — **none
  exist in MDU's real model.** MDU's provenance is an append-only list of
  events (`ORIGIN`, `INGESTION`, `VALIDATION`, `TRUST_CHANGE`, ...), each
  with its own `id` and a shared `dataset_id` — there is no single
  "knowledge object" record with those three fields. This is a structural
  mismatch between the placeholder model and MDU's real model, not a
  naming issue. Remains `confirmed_by_mdu=False`, now with notes citing
  this evidence instead of "pending confirmation." **Needs a design
  conversation with Nupur before MASTERDB's Knowledge Object contract can
  be finalized** — see Risk Notes.

Re-run the verification script yourself:

```bash
python scripts/confirm_mdu_contract.py <a-real-dataset-id-or-uuid>
```


## Evidence Not Included (and why)

The original task brief also asks for Swagger/terminal screenshots, a
continuous runtime recording, and Docker build evidence. None of that is
included here yet, for the same reason as before: producing a screenshot
of a server that was never started, or a recording that was never
captured, would be fabricated evidence. What *has* been done — full pytest
pass and live MDU calls above — is real and reproducible. Still pending,
requires a local machine with a display/terminal:

```bash
uvicorn main:app --reload
# open /docs, screenshot Swagger UI, exercise each endpoint, screenshot
# responses; screenshot terminal/log output

docker build -t masterdb .
docker run -p 8000:8000 --env-file .env masterdb
# screenshot clean startup, then kill and restart, screenshot that too
```

## Risk Notes

- Artifact storage is file-based for this handoff, consistent with the
  existing `ArtifactStore` pattern (now reused for registry, knowledge
  object, and retrieval evidence stores under different directories). A
  future platform can replace it without changing service logic.
- `KnowledgeObjectService` currently mirrors a placeholder shape for MDU's
  Knowledge Object contract rather than consuming a finalized one.
  **Confirmed 2026-07-08 against live MDU:** this is a real, structural
  gap, not just an unconfirmed one — MDU's actual model is an append-only
  provenance event list with no `knowledge_object_id`, `lineage_reference`,
  or `derivation_path` fields. See "Live MDU Verification" above. This
  needs a design conversation with Nupur, not a field rename, before
  `MDU_INTERFACE_CONTRACT.md` can be finalized.
- Version compatibility currently checks major-version equality only
  (`schema_version` prefix before the first `.`); this is MASTERDB's own
  negotiation policy, confirmed working live (exact-match case verified
  against real MDU schema data — see above), but the *rule itself* is
  still MASTERDB's placeholder policy pending MDU's actual compatibility
  stance.
- Requests currently pass local paths. Upload handling can be added at the
  API boundary if future ingestion pipelines require multipart packages.
- Existing validators are deterministic but simple; deeper semantic
  validation can be added behind `ValidationService`.
- `is_replay_safe` on individual provenance events can be `False` even
  when the dataset overall has `replay_compatibility: PARTIAL` (confirmed
  live — two `TRUST_CHANGE` events on the sample dataset had
  `is_replay_safe: False` while `ORIGIN`/`INGESTION`/`VALIDATION` events
  were `True`). Confirm `RetrievalReadinessService`/replay endpoints treat
  this as a per-event flag, not a dataset-level constant.
- `starlette.testclient`'s use of `httpx` is now deprecated
  (`StarletteDeprecationWarning`, confirmed in local pytest run) in favor
  of `httpx2`. Not currently breaking, but worth migrating before Starlette
  drops the old path in a future release.
- The uniform error contract (`{"error": {...}}`) changes the shape of
  every error response versus the prior `{"detail": ...}` FastAPI default.
  No existing test asserted on that shape, but any external caller that
  parses `detail` directly will need to switch to `error.message`.

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
- Confirm `MDUClient` never appears anywhere outside
  `services/mdu_client.py` (single seam for MDU's base URL/paths/auth).
- Confirm every MDU-dependent code path degrades to a flagged placeholder
  instead of raising when MDU is unconfigured/unreachable.
- Confirm `TantraInterfaceService` adds no new ownership — every method is
  a direct delegation to an existing service.
- Confirm `/discovery/packages` results are deterministically ordered.
- Confirm the new `{"error": {...}}` contract is acceptable to any existing
  external caller before merging (see Risk Notes).
- Run `python -m pip install -r requirements.txt && python -m pytest -v` —
  **done 2026-07-08, 50 passed, 0 failed.** Re-run to confirm on your
  machine before merge.
- Live MDU verification — **done 2026-07-08**, see "Live MDU Verification"
  above. Two real bugs found and fixed as a direct result (schema
  list-vs-dict, canonical-ID-to-UUID resolution). Re-run
  `scripts/confirm_mdu_contract.py` to reconfirm before merge, since MDU's
  schema is not under MASTERDB's control and could change.
- **Escalate to Nupur before merge:** the Knowledge Object model mismatch
  (`knowledge_object_id`/`lineage_reference`/`derivation_path` don't exist
  in MDU's real provenance-event model) needs a design decision, not more
  guessing in `mdu_contract_adapter.py`.
- Still outstanding: Swagger/terminal screenshots, Docker build/restart
  evidence, continuous runtime recording — see "Evidence Not Included."

## Task 4 — Shared Data Services & MASTERDB Convergence

Full detail: `../MASTERDB_SHARED_DATA_ARCHITECTURE.md`. This packet's
`code_packets/` folder holds the changed-file inventory and architecture
delta mandated by the Task 4 deliverables list; `runtime/` and
`api_responses/` hold live evidence for every implemented feature.

**Delivered**: Shared Data Service Registry (15 datasets), 6 live shared
service contracts (Authentication, Identity, Organizations, Configuration,
Knowledge References, Notifications), 13 `/shared/*` runtime endpoints,
46 new tests (96 total, all passing), ecosystem dependency mapping, and
full doc updates across `README.md`, `ARCHITECTURE.md`,
`API_DOCUMENTATION.md`, `HANDOVER.md`, this file, and the root
`REVIEW_PACKET.md`.

**Evidence in this folder:**

- `runtime/task4_full_test_run.txt` — verbose pytest run, 96/96 passed.
- `runtime/task4_live_api_console_log.txt` — structured logging from a
  live `/shared/*` request sequence.
- `api_responses/01_..14_...json` — 14 captured request/response pairs
  covering registry reads, contract reads, register/update/history/
  replay/resolve, and 400/404/409 failure paths.
- `code_packets/changed_files.md` — per-file description of every change.
- `code_packets/changed_file_list.txt` — plain changed-file list.
- `code_packets/architecture_delta.md` — before/after architecture diagram
  and explicit "what did NOT change" list.

**Not yet captured** (same limitation as the rest of this packet — no
browser/screenshot tooling in this environment): Swagger UI screenshots
and terminal screenshots for `/shared/*`. The JSON evidence above is
real, live output from the running app; screenshots would be a visual
restatement of the same data and can be captured by running
`uvicorn main:app --reload` locally and hitting `/docs`.

