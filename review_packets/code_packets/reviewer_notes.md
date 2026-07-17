# Reviewer Notes — BCAES Canonical Registry Service

For Nupur / whoever reviews this. Read `critical_files.md` first for the
three-file path through the code; this is the "things worth flagging"
list on top of that.

## What's genuinely done

- All eleven registries, full CRUD, search, relationship + transitive
  dependency explorers, capability reuse checker, six validators + one
  aggregate — all live, all tested (40 new tests, 96% coverage on
  `bcaes_registry/`), all captured end-to-end against a real running
  server (`review_packets/api_responses_bcaes/`, 16 request/response
  pairs including three deliberate failure cases and one full
  flag-fix-revalidate cycle).
- Full suite: 136/136 passing, zero regressions against the existing
  service (`review_packets/runtime_bcaes/full_suite_136_passing.txt`).
- `replay_hash` on `/bcaes/validate/architecture` is proven identical
  across repeated calls against unchanged state — not just asserted, but
  captured live twice and diffed byte-identical.

## What's explicitly NOT done, and why

1. **No BCAB/BCAES content in the registries.** No source documents were
   available (see "Known Unknowns" in the task brief). Every registry is
   schema-ready and empty. This is a data-entry follow-up through the
   existing `POST` API, not an engineering gap — flagging it clearly so
   it isn't mistaken for an oversight.
2. **No persistence.** In-memory only; resets on service restart. Kept
   simple per instruction. If this needs to survive restarts, the
   `PackageRegistryService` / `SharedRecordStore` JSON-per-record pattern
   already in this repo is the obvious template to follow — deliberately
   not pre-built against a registry with no real data yet.
3. **No MDU wiring.** Whether an Interface Registry object should
   eventually reference a live MDU contract is left as an open question
   for you rather than decided unilaterally — the task's own Non-Goals
   say "do not duplicate MDU responsibilities," and I read that as "don't
   guess at this integration without you."
4. **No governance logic.** Authority-boundary violations are reported,
   never blocked or auto-resolved. That enforcement decision belongs to
   GC Team per the task's Integration Block.

## One design choice worth double-checking with the team

`classification` is fixed to equal `registry_type` (system-assigned,
never client-supplied) rather than being a separate free-text field. This
was the simplest way to satisfy "one primary classification" +
"no semantic drift" without inventing a second classification vocabulary
that could itself drift. If BCAB/BCAES actually define classification as
something more granular than "which of the eleven registries," this is
the one schema decision that would need revisiting once real source
documents are available — everything else in the schema (owner, version,
dependencies, authority_boundaries, links) is generic enough to survive
that change unaffected.

## Everything else

Standard patterns already established elsewhere in this repo: uniform
error contract (`_error_body`/global exception handlers, unchanged),
`{registry_type}` path-param validation mirroring `_shared_service()`'s
`{service_name}` pattern, version negotiation reused as-is from
`services/shared_version_compatibility.py` rather than reimplemented.
