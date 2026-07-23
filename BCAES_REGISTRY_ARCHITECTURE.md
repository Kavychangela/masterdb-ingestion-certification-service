# BCAES Canonical Registry Architecture

**BCAES Canonical Registry Service — Kavy.**

This document defines the BCAES Registry: a live, versioned, API-queryable
architectural registry that operationalizes BCAB/BCAES into a runtime
capability. It is the source of truth for this work; `README.md`,
`ARCHITECTURE.md`, `API_DOCUMENTATION.md`, and `HANDOVER.md` each carry a
short pointer back here rather than duplicating this content.

This is an additive, self-contained module (`bcaes_registry/`, `/bcaes/*`
routes) added to the existing MASTERDB service. It does not touch
certification, lifecycle, retrieval, TANTRA, discovery, or the Task 4
shared-data layer, and it does not talk to the live `MDUClient` — see
§5 "What this deliberately does not do."

---

## 1. What This Is (and Is Not)

**Is:** a canonical, queryable catalog of architectural objects — domains,
capabilities, platform services, products, programs, frameworks, engines,
runtimes, integrations, knowledge assets, interfaces — each with exactly
one classification, one owner, a version, declared dependencies, derived
consumers, declared authority boundaries, and reference links.

**Is not:**
- A redefinition of BCAB. This service has no opinion on what BCAB/BCAES
  *mean*; it only gives their objects a runtime home.
- A governance engine. It flags undeclared cross-owner dependencies for
  human review (§4.4); it does not grant, deny, or enforce access. That is
  GC Team's layer.
- A duplicate of MDU. MDU owns schema/provenance/semantic authority for
  *data*. This registry catalogs *architecture* (domains, capabilities,
  services) — a different object class entirely.
- Populated with real BCAB/BCAES content yet. **No source documents were
  available at build time** (see "Known Unknowns" in the task brief), so
  every registry starts empty. The eleven registries, their schema, and
  the full validation/query API are production-ready; populating them with
  the actual BCAB/BCAES catalog is a follow-up data-entry task, not a code
  task. See §6.

## 2. The Eleven Canonical Registries

| Registry            | id prefix | Registry           | id prefix |
|----------------------|-----------|---------------------|-----------|
| Domain               | `dom-`    | Framework           | `frw-`    |
| Capability            | `cap-`    | Engine              | `eng-`    |
| Platform Service      | `psv-`    | Runtime             | `run-`    |
| Product               | `prd-`    | Integration         | `itg-`    |
| Program               | `prg-`    | Knowledge Asset     | `kas-`    |
|                       |           | Interface           | `ifc-`    |

Every registry shares one schema (`bcaes_registry/models.py:RegistryObject`):

```
id, registry_type, classification, name, purpose, owner, status, version,
dependencies (with optional version pins), consumers (derived),
authority_boundaries, links, created_at, updated_at
```

### 2.1 Why `classification == registry_type`

The task's acceptance criteria require "every architectural object must
have one primary classification" and "no semantic drift." Rather than add
a free-text classification vocabulary that could itself drift or acquire
duplicate/ambiguous values over time, an object's classification is fixed
to the registry it lives in, assigned by the system at registration — never
user-supplied. There are exactly eleven canonical registries, so an object
structurally cannot carry more than one classification, and it cannot
silently drift to a different one later. The classification validator
(§4.1) exists to produce reviewable evidence of this and to catch
inconsistency introduced by direct state manipulation, not because the
invariant is expected to break through the API.

### 2.2 Why `consumers` is derived, not stored

`dependencies` is the only edge a caller writes. `consumers` is computed
on every read by scanning for objects that declare the target as a
dependency (`store.py:consumers_of`). This means there is exactly one
place relationship state can drift out of sync with itself: nowhere. A
dual-write model (caller sets both `dependencies` on the consumer and
`consumers` on the dependency) was rejected specifically because it
creates two sources of truth for one relationship.

## 3. Relationship Graph

Kept deliberately simple: `bcaes_registry/graph.py` builds adjacency from
`dependencies` at query time — no NetworkX, no separate graph store. This
was an explicit scope decision, not an oversight: the Learning Kit lists
NetworkX as a *study* topic, and the registries are queried far more often
than they're traversed at depth, so a persistent graph library would add
a second copy of the same edge data for no present benefit. If deep graph
algorithms (shortest path, centrality) become necessary later, this is the
one module to swap — every function here already returns plain dicts/lists,
so callers wouldn't need to change.

- `relationships(id)` — direct dependencies + derived consumers.
- `transitive_dependencies(id)` — full dependency chain, cycle-safe (a
  cycle is reported in `cycles_detected`, not followed forever).

## 4. Validation Engine

`bcaes_registry/validators.py`. Every check is a pure function of current
store state — no clocks, no randomness, no hidden mutation — so running
the same check twice against the same state always produces byte-identical
output. `/bcaes/validate/architecture` aggregates all six checks and adds
a `replay_hash` (SHA-256 of the sorted-key JSON payload) as reviewable
proof of that determinism; see `review_packets/` for two live captures of
the same state producing an identical hash.

| # | Check | Acceptance criterion it satisfies |
|---|-------|-------------------------------------|
| 4.1 | `validate_classification` | "one primary classification" |
| 4.2 | `detect_duplicates` | "no duplicate reusable capabilities" (generalized to all 11 registries) + "no duplicate id" |
| 4.3 | `validate_ownership` | "no hidden ownership" — owner + authority_boundaries required |
| 4.4 | `validate_authority_boundaries` | "no authority drift" — cross-owner dependency must be declared |
| 4.5 | `validate_version_compatibility` | "version compatibility" — reuses `services/shared_version_compatibility.negotiate_version`, the same policy already governing Task 4's shared services, rather than a second implementation |
| 4.6 | `validate_dependency_integrity` | dependency ids always resolve, re-verified on demand |

`capability_reuse_check(name)` is a separate, non-blocking lookup (not part
of the aggregate report): it searches the Capability Registry for exact
and substring name matches so a caller can check for an existing capability
*before* registering a new one, satisfying "Capability Reuse Checker"
without making reuse mandatory (that would be a governance decision).

## 5. What This Deliberately Does Not Do

- **No persistence.** The store is in-memory (`CanonicalRegistryStore`),
  matching "keep it simple" — mirrors the pattern of `PackageRegistryService`
  before its JSON-file persistence was added; this can be added the same
  way later without changing the service/API layer above it.
- **No MDU integration.** BCAB/BCAES objects and MDU's schema/provenance
  objects are different object classes; wiring them together (e.g. an
  Interface Registry entry pointing at a live MDU contract) is a Nupur
  design conversation, not a code decision this task should make alone.
- **No governance enforcement.** Authority-boundary violations are
  reported, never blocked. GC Team owns the decision of what happens next.

## 6. API Surface

Seventeen endpoints under `/bcaes/*`, mounted directly on `main.app`
(`bcaes_registry_service = BCAESRegistryService()` instantiated in
`main.py` alongside the other services). Full request/response shapes are
in `API_DOCUMENTATION.md`; live-captured examples are in
`review_packets/api_responses/`.

```
POST   /bcaes/registries/{registry_type}/objects
GET    /bcaes/registries
GET    /bcaes/registries/{registry_type}/objects
GET    /bcaes/registries/{registry_type}/objects/{object_id}
PATCH  /bcaes/registries/{registry_type}/objects/{object_id}
DELETE /bcaes/registries/{registry_type}/objects/{object_id}
GET    /bcaes/search
GET    /bcaes/relationships/{object_id}
GET    /bcaes/dependencies/{object_id}
GET    /bcaes/capability-reuse-check
GET    /bcaes/validate/classification
GET    /bcaes/validate/duplicates
GET    /bcaes/validate/ownership
GET    /bcaes/validate/authority-boundaries
GET    /bcaes/validate/version-compatibility
GET    /bcaes/validate/dependency-integrity
GET    /bcaes/validate/architecture
POST   /bcaes/convergence/{object_id}
GET    /bcaes/convergence/{object_id}
GET    /bcaes/convergence
GET    /bcaes/snapshot
```

> **Correction (this pass):** an earlier version of this document claimed
> these endpoints existed and that 136/136 tests passed. Neither was true
> — `main.py` never imported `bcaes_registry` at all, so none of the
> `/bcaes/*` routes existed and `tests/test_bcaes_api.py` errored on setup
> (`AttributeError: module 'main' has no attribute 'BCAESRegistryService'`,
> 12 errors). The module itself was correct; it was simply never wired in.
> That's fixed now — `bcaes_registry_service` is instantiated in `main.py`
> and all seventeen routes are live. See §7 for the real, re-run numbers.

## 6.1 Production Convergence (BCAES Volume 6)

`bcaes_registry/convergence_models.py` + `convergence_store.py`. Every
registered object can carry a `ConvergenceRecord` with the eight
dimensions the task brief's Phase 4 requires (`integration_status`,
`sdk_adoption`, `replay_status`, `observability_status`, `evidence_status`,
`governance_status`, `production_readiness`, plus `remaining_work`).

This is **declared state, not inferred telemetry.** This service has no
network reach into TANTRA, MDU, Bucket, or InsightFlow, so it cannot
itself measure SDK adoption or observability. What "production convergence
is measurable" means here is that every dimension has one canonical,
versioned, API-queryable home instead of living in a spreadsheet — each
collaborating team updates their own dimension via
`POST /bcaes/convergence/{object_id}`. Updates are a merge-patch: a call
that only sets `governance_status` does not reset `sdk_adoption` back to
`not_started`, so multiple teams can update the same object independently
without clobbering each other.

`maturity_score` is a simple fraction (dimensions marked `complete` / 7);
it is a rough signal for sorting/dashboards, not a production gate.

## 6.2 Current Reality Snapshot (BCAES Volume 7)

`bcaes_registry/snapshot.py`, exposed at `GET /bcaes/snapshot`. Computed
fresh on every call from the current registry + convergence state — no
manually maintained copy, per the task brief. Returns registry counts,
the architecture validation result (with `replay_hash`), and a
convergence overview (objects tracked vs. untracked, average maturity,
production-ready count). The response includes an explicit scope note:
it reflects only what has been registered in *this* service — it cannot
see reality inside TANTRA, MDU, Bucket, or InsightFlow unless those teams
register their own objects and convergence records through this API.

## 7. Testing

`tests/test_bcaes_registry_service.py` (service/store/graph/validators, 26
tests), `tests/test_bcaes_api.py` (registry HTTP layer, 14 tests), and
`tests/test_bcaes_convergence_api.py` (convergence + snapshot HTTP layer, 7
tests) — 47 tests, 97% statement coverage on `bcaes_registry/` (verified
with `pytest --cov=bcaes_registry --cov-report=term-missing`, this pass).
Full repo suite: **143/143 passing** (96 pre-existing + 47 new), zero
regressions, re-run and verified in this pass — not carried over from the
earlier (inaccurate) claim. See `review_packets/testing_evidence/`.

## 8. Follow-Up (Known Unknowns From the Task Brief)

- **Registry population.** No BCAB/BCAES source documents were available
  to seed the registries. The schema and API are ready to receive real
  objects the moment those documents (or a structured export of them)
  exist — this is a data task, not an engineering one.
- **Product mappings / capability inventory.** Depends on population.
- **Integration adoption by remaining BHIV products.** Each product team
  registers its own objects through the API above; no code change needed
  per new adopter.
- **Live cross-system integration (TANTRA runtime, MDU semantic registry,
  Bucket evidence/replay storage, InsightFlow/Pravah observability).**
  This build environment has no network reach to any of those services.
  The `/bcaes/*` API is ready to be called *by* them, and this service is
  ready to call *them* once real base URLs/credentials and confirmed
  contracts exist (the same pattern already used for the live `MDUClient`
  elsewhere in this repo) — but that integration cannot be faked here
  without becoming exactly the kind of unverified claim this pass just
  corrected.
- **Central Depot deposit.** No such system is reachable from this
  environment either; depositing the completed bootstrap is a hand-off
  step for whoever owns that repository/registry, not something this
  service can perform on its own.
- **Cross-team screenshots (Runtime Explorer, Dependency Explorer,
  Executive Dashboard, TANTRA/Bucket/MDU/InsightFlow integration
  evidence) required by REVIEW_PACKET.md.** Each of those UIs and
  systems belongs to a different team; only they can capture real
  evidence of their own side of the integration. This repo can supply
  its half — API responses, test/coverage reports, replay hashes — which
  is what `review_packets/` already contains.
