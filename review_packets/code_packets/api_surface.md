# API Surface — BCAES Canonical Registry Service

14 endpoints under `/bcaes/*`. Full request/response documentation with
real examples: `API_DOCUMENTATION.md`. Live-captured evidence: this
folder's sibling `../api_responses_bcaes/`.

| Method | Path | Maps to task brief's "Build APIs including..." |
|--------|------|--------------------------------------------------|
| POST | `/bcaes/registries/{registry_type}/objects` | (registration — implicit prerequisite for all APIs below) |
| GET | `/bcaes/registries` | Registry Search (summary view) |
| GET | `/bcaes/registries/{registry_type}/objects` | Registry Search |
| GET | `/bcaes/registries/{registry_type}/objects/{id}` | Registry Lookup |
| PATCH | `/bcaes/registries/{registry_type}/objects/{id}` | (mutation — needed for the fix-then-revalidate workflow demonstrated in evidence #35-37) |
| DELETE | `/bcaes/registries/{registry_type}/objects/{id}` | (mutation) |
| GET | `/bcaes/search` | Registry Search |
| GET | `/bcaes/relationships/{id}` | Relationship Explorer |
| GET | `/bcaes/dependencies/{id}` | Dependency Explorer |
| GET | `/bcaes/capability-reuse-check` | Capability Reuse Checker |
| GET | `/bcaes/validate/classification` | Classification Validator |
| GET | `/bcaes/validate/duplicates` | Duplicate Detection |
| GET | `/bcaes/validate/ownership` | (extends "no hidden ownership" acceptance criterion) |
| GET | `/bcaes/validate/authority-boundaries` | (extends "no authority drift" acceptance criterion) |
| GET | `/bcaes/validate/version-compatibility` | (Phase 4 "version compatibility" testing requirement) |
| GET | `/bcaes/validate/dependency-integrity` | (supports Relationship/Dependency Explorer correctness) |
| GET | `/bcaes/validate/architecture` | Architecture Validation API (aggregates all checks above) |

All eight API categories named in the task brief's Phase 3 are covered.
`/validate/ownership`, `/validate/authority-boundaries`,
`/validate/version-compatibility`, and `/validate/dependency-integrity`
are additions beyond the named list, added because the brief's Phase 4
testing requirements ("no hidden ownership," "no authority drift,"
"version compatibility," relationship "correctness") need an individually
queryable check each, not just the aggregate — the aggregate
(`/validate/architecture`) is what actually satisfies "Architecture
Validation API."

## Error contract

Reuses the uniform `{"error": {"type", "message", "path"}}` shape already
established by `main.py`'s global exception handlers (see
`API_DOCUMENTATION.md`'s top-level error-contract section) — BCAES
introduces zero new error-response shapes. `404` for unknown registry
type or missing object id; `400` for a dependency id that doesn't exist
in any registry.
