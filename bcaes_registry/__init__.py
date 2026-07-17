"""
BCAES Canonical Registry Service.

Operationalizes BCAB/BCAES into a live, queryable architectural registry.
See BCAES_REGISTRY_ARCHITECTURE.md at the repo root for the full design.

Scope reminder (do not violate):
  - Does not redefine BCAB.
  - Does not change architectural semantics.
  - Does not introduce governance logic (GC Team owns that).
  - Does not duplicate MDU responsibilities (services/mdu_* owns that).
  - Does not invent new architectural objects beyond the eleven canonical
    registries below.
"""
