# Registry Schema — BCAES Canonical Registry Service

Single shared schema (`bcaes_registry/models.py:RegistryObject`) across
all eleven registries — the task brief lists the same field set for every
registry, so one schema with a `registry_type` discriminant, rather than
eleven near-identical classes.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | System-assigned, `{prefix}-{uuid12}`, e.g. `cap-198f8afd4901`. Never client-supplied. |
| `registry_type` | enum (11 values) | Which registry the object lives in. Set at registration, immutable. |
| `classification` | enum (11 values) | Always equal to `registry_type` — see `BCAES_REGISTRY_ARCHITECTURE.md` §2.1 for why. |
| `name` | `str` | Required, non-empty (validated). |
| `purpose` | `str` | Required, non-empty (validated). |
| `owner` | `str` | Required, non-empty (validated by `ownership` check too, at read time). |
| `status` | enum: `draft`, `active`, `deprecated`, `retired` | Defaults to `draft` at registration. |
| `version` | `str` | Free-form (e.g. `"1.0"`), defaults to `"1.0"`. Compared via `negotiate_version` when a dependent pins a `required_version`. |
| `dependencies` | `List[{id, required_version?}]` | The only edge a caller writes. Validated to exist at registration and on update. |
| `consumers` | `List[str]` | **Derived, read-only.** Computed from every other object's `dependencies` on every read — never stored, never client-supplied. |
| `authority_boundaries` | `List[str]` | Owners/teams this object is authorized to declare dependencies on. Required non-empty (ownership check). |
| `links` | `List[str]` | Free-form reference URLs/pointers. |
| `created_at` / `updated_at` | ISO-8601 UTC | Set by the server. |

## Id prefixes

```
domain -> dom-   framework -> frw-   integration -> itg-
capability -> cap-   engine -> eng-   knowledge_asset -> kas-
platform_service -> psv-   runtime -> run-   interface -> ifc-
product -> prd-
program -> prg-
```

## What's intentionally NOT in the schema

- No free-text classification field — see §2.1 of the architecture doc.
- No `parent`/`children` fields — hierarchy, if BCAB/BCAES define one, is
  expressed through `dependencies`/`consumers` rather than a second
  relationship mechanism.
- No embedded validation-result fields — validation is always computed
  fresh (`/bcaes/validate/*`), never cached on the object, so a stale
  cached "passed: true" can never sit alongside data that has since
  drifted.
