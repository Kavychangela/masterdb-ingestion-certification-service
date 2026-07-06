# MASTERDB <-> MDU Interface Contract v1

**Status: DRAFT / PLACEHOLDER.** This document records what MASTERDB
currently assumes about MDU-owned contracts (Knowledge Object, Provenance,
Lineage, canonical schema). It is written from the MASTERDB side only and
is intended as the starting point for joint sign-off with Nupur (MDU
owner), not as a finalized specification. MASTERDB does not redefine any of
the concepts below — it documents its current *consumption* of them so the
seam is explicit and auditable.

## Ownership

| Concept                     | Owner | MASTERDB's role                     |
|------------------------------|-------|--------------------------------------|
| Knowledge Object semantics    | MDU   | Consumer only, via `MDUContractAdapter` |
| Provenance schema             | MDU   | Consumer only                         |
| Lineage graph semantics       | MDU   | Consumer only (walks parent/child pointers it is given) |
| Canonical dataset schema       | MDU   | Consumer only (`schema_version` is opaque to MASTERDB) |
| Package Identity              | MASTERDB | Owner (`package_id`, lifecycle status) |
| Dataset Registry               | MASTERDB | Owner |
| Retrieval Readiness/Evidence   | MASTERDB | Owner |

## Consumed Contracts

MASTERDB currently consumes the following MDU-owned concepts, through
`services/mdu_contract_adapter.py::MDUContractAdapter`:

- **Knowledge Object identity** — MASTERDB currently generates its own
  `knowledge_object_id` and `knowledge_hash` (sha256 of `package_id` +
  `source_reference` + `derivation_path`) as a placeholder. **Not yet
  confirmed by MDU** whether this should instead be assigned or validated
  by MDU's own identity scheme.
- **Provenance `source_reference`** — treated as an opaque string (assumed
  URI/path). **Not yet confirmed** against MDU's canonical provenance
  schema.
- **Lineage `lineage_reference`** — treated as an optional opaque pointer.
  **Not yet confirmed** against MDU's lineage graph representation.
- **`derivation_path`** — treated as an ordered list of free-text
  transformation step names. **Not yet confirmed** — MDU may define a
  richer, typed representation.

## Required Fields (MASTERDB side, current placeholder)

| Field                | Required | Confirmed by MDU | Notes |
|-----------------------|----------|-------------------|-------|
| `knowledge_object_id` | Yes      | No                | MASTERDB-generated; format pending MDU review |
| `source_reference`    | Yes      | No                | Assumed opaque string |
| `lineage_reference`   | No       | No                | Optional pointer, shape TBD |
| `derivation_path`     | No       | No                | Ordered string list, shape TBD |
| `parent_package`      | No       | N/A (MASTERDB-owned) | References a MASTERDB `package_id`, validated to exist in the registry |
| `schema_version`      | Yes      | No                | Opaque to MASTERDB; only major-version prefix is compared for compatibility |

## Version Compatibility

MASTERDB currently enforces a **placeholder** compatibility rule: a child
package's `schema_version` must share the same major-version prefix (text
before the first `.`) as its declared parent's `schema_version`. This is a
conservative stand-in and is explicitly **not** a claim about MDU's actual
schema evolution policy. It should be replaced once MDU defines real
compatibility semantics (e.g. semantic versioning rules, migration
requirements, or a compatibility matrix).

## Known Gaps

1. MDU's canonical Knowledge Object contract has not been finalized or
   shared as of this sprint — this document and `MDUContractAdapter`
   reflect MASTERDB's best-effort placeholder, not a ratified spec.
2. Identity assignment for `knowledge_object_id` may need to move to MDU or
   be validated against an MDU-issued scheme.
3. Version compatibility rules are a placeholder (major-version equality)
   pending MDU's real policy.
4. No confirmed schema for `lineage_reference` or `derivation_path` exists
   yet; both are currently unstructured.
5. "Runtime Discovery," listed under MASTERDB's responsibilities in the
   sprint brief, does not yet have a dedicated endpoint; `GET
   /packages/{package_id}` and `GET /packages/{package_id}/retrieval` serve
   this informally today.

## Future Extension Points

- Swap `MDUContractAdapter`'s placeholder snapshot for a live contract
  fetched from or validated against MDU once Phase 5 convergence with
  Nupur completes. `KnowledgeObjectService` was written to depend only on
  this adapter seam, so this should not require changes to lifecycle or
  retrieval logic.
- Add a dedicated Runtime Discovery endpoint if MDU or downstream
  consumers need a distinct service/tool discovery contract beyond package
  lookup.
- Extend `RetrievalEvidence` rules if MDU introduces additional
  provenance-completeness requirements that should gate retrieval.
- Replace the major-version compatibility placeholder once MDU's version
  compatibility policy is confirmed.

## No Duplicate Ownership

This document intentionally avoids redefining Knowledge Object, Provenance,
Lineage, or canonical schema semantics. Where MASTERDB's code currently
makes an assumption about their shape, it is called out above as a
placeholder and localized to `services/mdu_contract_adapter.py` so that a
future MDU-confirmed contract can replace it without touching
`PackageRegistryService` or `RetrievalReadinessService`.
