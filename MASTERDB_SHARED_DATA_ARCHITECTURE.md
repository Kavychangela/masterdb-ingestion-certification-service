# MASTERDB Shared Data Architecture

**Task 4 — Shared Data Services & MASTERDB Convergence.**

This document defines how MASTERDB evolves from a certification/knowledge-
platform boundary into the ecosystem's **shared operational data layer**,
sitting between Product Databases and MDU. It is the source of truth for
Task 4; `README.md`, `ARCHITECTURE.md`, `API_DOCUMENTATION.md`, and
`HANDOVER.md` each carry a short pointer back here rather than duplicating
this content.

Everything below was built without touching MASTERDB's existing
certification/lifecycle/lineage/retrieval/TANTRA/discovery surfaces — this
is a new, additive layer (`shared_data/`, `services/shared_*`, `/shared/*`
routes), not a rewrite of Task 1–3's work.

---

## 1. Three-Layer Model & Responsibilities

```
Product Database  --->  MASTERDB  --->  MDU
 (per-product,           (shared,          (canonical,
  private)                cross-product)    ecosystem-wide)
```

### 1.1 Product Database — owns application-specific operational data

- Anything private to one product: business transactions, product-specific
  UI state, feature usage, internal working tables.
- **Cannot own**: shared identity, shared organizations, canonical schemas,
  provenance, or anything another product would reasonably need to reuse.
- Reads shared datasets from MASTERDB rather than re-implementing them.

### 1.2 MASTERDB — owns reusable ecosystem datasets & cross-platform operational services

- Owns **storage, versioning, and audit** of the 15 shared dataset
  categories in the registry (`shared_data/registry.py`) — see §2.
- Owns the six live shared service contracts (Authentication, Identity,
  Organizations, Configuration, Knowledge References, Notifications) — see
  §3.
- Owns deterministic runtime APIs for reading/writing those datasets — see
  §4 — plus everything from Task 1–3 (certification, Knowledge Package
  Lifecycle, Retrieval Readiness, TANTRA interface, Runtime Discovery).
- **Cannot own**: canonical schema/provenance/lineage *semantics* (MDU's),
  or any single product's private operational data.
- Product-agnostic by construction: nothing in `shared_data/` or
  `services/shared_*` references a specific product's business logic.

### 1.3 MDU — owns canonical schemas, provenance, semantic contracts, and version compatibility authority

- Owns the actual meaning of a dataset's schema and its provenance/lineage
  event chain — MASTERDB never redefines this (see
  `MDU_INTERFACE_CONTRACT.md`).
- MASTERDB's `knowledge_references` shared dataset stores only a *pointer*
  (`dataset_id`/`package_id`) into MDU's content; the content itself is
  fetched live through `MDUContractAdapter`, never duplicated into
  `shared_store/knowledge_references/`.

**No ownership overlap.** Every shared dataset in the registry names
exactly one owner (`shared_data/registry.py:owner`), and `knowledge_references`
is the one entry that explicitly splits pointer-ownership (MASTERDB) from
content-ownership (MDU) rather than blurring the two.

---

## 2. Phase 1 — Shared Data Service Registry

Fifteen dataset categories are registered in `shared_data/registry.py`,
each declaring `purpose`, `owner`, `consumers`, `update_policy`,
`lifecycle`, and `dependency_map`. Read live via `GET /shared/registry`.

| Dataset | Owner | Implemented (live service) |
|---|---|---|
| authentication | MASTERDB | ✅ `/shared/authentication` |
| identity | MASTERDB | ✅ `/shared/identity` |
| users | MASTERDB | ⛔ registered, not yet built |
| organizations | MASTERDB | ✅ `/shared/organizations` |
| roles | MASTERDB | ⛔ registered, not yet built |
| permissions | MASTERDB | ⛔ registered, not yet built |
| uniguru_db | MASTERDB | ⛔ registered, not yet built |
| knowledge_references | MASTERDB (pointer) / MDU (content) | ✅ `/shared/knowledge-references` |
| notifications | MASTERDB | ✅ `/shared/notifications` |
| configuration | MASTERDB | ✅ `/shared/configuration` |
| feature_flags | MASTERDB | ⛔ registered, not yet built |
| audit_events | MASTERDB | ⛔ registered, not yet built |
| shared_lookup_tables | MASTERDB | ⛔ registered, not yet built |
| localization | MASTERDB | ⛔ registered, not yet built |
| system_settings | MASTERDB | ⛔ registered, not yet built |

The registry is deliberately broader than what has a live runtime service:
Phase 1 (design) is complete for all 15; Phase 2/4 (contract + runtime) is
complete for the 6 marked ✅, matching the "Examples" list in the Task 4
brief. Adding a 7th live service means adding one `SharedRecordStore`
subclass (see §3) — the registry entry already exists.

---

## 3. Phase 2 — Shared Service Contracts

All six services are thin subclasses of one generic, reusable engine —
`SharedRecordStore` (`services/shared_record_store.py`) — so behavior
(versioning, audit trail, replay-safety, failure handling) is uniform
across the platform instead of reimplemented per dataset. Machine-readable
contracts are served live at `GET /shared/contracts`; summarized below.

| Service | Version | Required payload fields | Dependencies | Ownership boundary |
|---|---|---|---|---|
| Authentication | 1.0.0 | `subject_id`, `provider` | identity (optional) | Stores credential *references* only — not an identity provider |
| Identity | 1.0.0 | `display_name` | none | Stores the shared profile only; no identity semantics beyond what's written |
| Organizations | 1.0.0 | `name` | identity (optional) | Shared org record only; product-specific tenant config stays in-product |
| Configuration | 1.0.0 | `key`, `value` | none | Stores values verbatim; no interpretation/governance logic |
| Knowledge References | 1.0.0 | `dataset_id` | MDU (via `MDUContractAdapter`) | Stores the pointer only; content stays MDU's |
| Notifications | 1.0.0 | `channel`, `template` | identity (optional) | Stores records/templates only; no delivery (SMTP/push/SMS) logic |

Every service exposes the same contract shape:

- **Inputs**: `register(record_id, payload, actor, reason)`, `update(record_id, payload, actor, reason)`, `deprecate(record_id, actor, reason)`.
- **Outputs**: a `SharedRecord` — `record_id`, `dataset`, `payload`, `version`, `deprecated`, `created_at`, `updated_at`, `history[]`.
- **Failure behaviour**: `404` unknown record, `409` duplicate register, `400` missing required field or mutation of a deprecated record. Nothing is silently fabricated or dropped.

---

## 4. Phase 3 — Ecosystem Dependency Mapping

```
Application DB
   |  (owns private operational data; never exposes internal schema)
   v
MASTERDB  <---  read path: /shared/{service}, /shared/{service}/{id}
   |             write path: POST .../register, PUT .../{id}, POST .../{id}/deprecate
   |             sync: synchronous, request/response (no async queue in Task 4 scope)
   v
MDU  <---  read-only via MDUContractAdapter (/mdu/schema, /mdu/provenance)
           MASTERDB never writes to MDU; MDU is consumed, not owned.
```

- **Ownership**: as in §1 — one owner per dataset, no duplication.
- **Synchronization**: shared datasets are synchronous request/response;
  MASTERDB does not currently push changes to product databases or poll
  MDU on a schedule (both are explicit non-goals for Task 4 — see
  `HANDOVER.md` → Non-Goals).
- **Read path**: Product/TANTRA/UniGuru → `GET /shared/{service}/{record_id}`
  (optionally → `.../resolve` for cross-service dependency resolution, or
  `.../history` / `.../replay` for audit).
- **Write path**: Product → `POST /shared/{service}/register` →
  `PUT /shared/{service}/{record_id}` for updates →
  `POST /shared/{service}/{record_id}/deprecate` to retire.
- **Authority boundary**: MASTERDB can reject a write (400/409) but never
  silently reinterprets a payload; MDU's schema/provenance responses are
  passed through verbatim by `MDUContractAdapter`, never "improved."
- **What each layer explicitly cannot own**:
  - Product DB cannot own shared identity/org/config data other products need.
  - MASTERDB cannot own canonical schema/provenance/lineage semantics.
  - MDU cannot own product-private operational data or MASTERDB's own audit trail.

---

## 5. Phase 4 — Runtime Integration

All `/shared/*` routes (`main.py`) are:

- **Version-aware**: `GET /shared/version-compatibility?local_version=&remote_version=`
  applies the same major/minor negotiation rule used by
  `MDUContractAdapter.negotiate_version` (kept as an independent copy in
  `services/shared_version_compatibility.py` so the shared-platform code
  has no import dependency on the MDU-specific adapter).
- **Replay-safe**: `GET /shared/{service}/{record_id}/replay` rebuilds
  version/deprecated state purely from the stored transition history and
  reports `replay_consistent: false` on drift rather than crashing.
- **Observable**: every mutation is logged (`logger.info(...)`, same
  `masterdb` logger as the rest of the service) and produces a
  `SharedRecordTransition` entry.
- **Auditable**: `GET /shared/{service}/{record_id}/history` returns the
  full, ordered transition trail (actor, reason, timestamp, action, version)
  for every record.
- **Stateless where practical**: services hold no in-memory session state;
  each request reads/writes JSON files under `shared_store/{dataset}/` via
  the same `ArtifactStore` used elsewhere in MASTERDB.
- **No semantic interpretation / no ontology / no governance logic**:
  `payload` is a free-form dict end to end. `SharedRecordStore` only checks
  that declared required *keys* are present — it never inspects or
  interprets their values.

### Full route surface

```
GET    /shared/registry
GET    /shared/registry/{dataset_name}
GET    /shared/contracts
GET    /shared/contracts/{service_name}
GET    /shared/version-compatibility?local_version=&remote_version=

POST   /shared/{service_name}/register
PUT    /shared/{service_name}/{record_id}
POST   /shared/{service_name}/{record_id}/deprecate
GET    /shared/{service_name}
GET    /shared/{service_name}/{record_id}
GET    /shared/{service_name}/{record_id}/history
GET    /shared/{service_name}/{record_id}/replay
GET    /shared/{service_name}/{record_id}/resolve
```

`{service_name}` is one of: `authentication`, `identity`, `organizations`,
`configuration`, `knowledge-references`, `notifications`.

---

## 6. Phase 5 — Testing Evidence

46 new tests (96 total, all passing — see `review_packets/` for the
terminal log) cover every Phase 5 requirement from the Task 4 brief:

| Requirement | Test file | Representative test |
|---|---|---|
| Cross-service dataset retrieval | `tests/test_shared_dependency_resolver.py`, `tests/test_shared_api.py` | `test_resolve_cross_service_dependency_via_api` |
| Version compatibility | `tests/test_shared_version_compatibility.py`, `tests/test_shared_api.py` | `test_version_compatibility_endpoint` |
| Graceful failures | `tests/test_shared_record_store.py`, `tests/test_shared_api.py` | `test_register_duplicate_record_returns_409`, `test_deprecate_then_update_returns_400` |
| Missing dependency handling | `tests/test_shared_dependency_resolver.py` | `test_resolve_reports_missing_dependency_without_failing` |
| Replay consistency | `tests/test_shared_record_store.py`, `tests/test_shared_api.py` | `test_replay_detects_version_drift`, `test_replay_and_history_endpoints` |
| API validation | `tests/test_shared_api.py` | `test_register_missing_required_field_returns_400`, `test_unknown_service_name_returns_404` |

---

## 7. Example Runtime Flows

**Flow A — TANTRA registers a shared organization and resolves its owner:**

```
POST /shared/identity/register       {record_id: "id-1", payload: {display_name: "Kavy"}}
POST /shared/organizations/register  {record_id: "org-1", payload: {name: "BHIV", owner_identity_id: "id-1"}}
GET  /shared/organizations/org-1/resolve
  -> {fully_resolved: true, resolved_dependencies: {owner_identity_id: {...id-1 record...}}}
```

**Flow B — A product references MDU-owned content through MASTERDB without duplicating it:**

```
POST /shared/knowledge-references/register
  {record_id: "kref-1", payload: {dataset_id: "BHIV-DS-MARITIME-AIS-LIVE-001"}}
GET  /mdu/schema/BHIV-DS-MARITIME-AIS-LIVE-001    <- MDU's actual schema, fetched live
GET  /mdu/provenance/BHIV-DS-MARITIME-AIS-LIVE-001 <- MDU's actual provenance chain
```

`knowledge_references` never stores the schema/provenance itself — only the
pointer — so there is nothing to go stale relative to MDU.

**Flow C — Configuration change, then replay to verify audit integrity:**

```
POST /shared/configuration/register  {record_id: "cfg-1", payload: {key: "max_retries", value: 3}}
PUT  /shared/configuration/cfg-1     {payload: {key: "max_retries", value: 5}}
GET  /shared/configuration/cfg-1/replay
  -> {replay_consistent: true, replayed_version: 2, stored_version: 2}
```

---

## 8. What This Explicitly Does Not Do

Per the Task 4 brief's "Do NOT" list:

- Does not redefine MDU semantics — `knowledge_references` stores pointers
  only; `MDUContractAdapter` is untouched.
- Does not duplicate product databases — no product-specific tables were
  added anywhere in `shared_data/` or `services/shared_*`.
- Does not introduce business logic into MASTERDB — `SharedRecordStore`
  validates only that required *keys* exist, never their meaning.
- Does not change constitutional ownership of schemas or provenance — MDU
  remains the sole owner; see §1.3.
