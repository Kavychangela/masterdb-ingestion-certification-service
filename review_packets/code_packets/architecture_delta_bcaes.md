# Architecture Delta — BCAES Canonical Registry Service

## Before

```
MASTERDB service:
  certification / lifecycle / lineage / retrieval / TANTRA / discovery
  Task 4 shared-data platform (/shared/*)

No architectural catalog existed. BCAB/BCAES were documentation only —
nothing in the codebase made them queryable, versioned, or validated.
```

## After

```
MASTERDB service:
  certification / lifecycle / lineage / retrieval / TANTRA / discovery   <- untouched
  Task 4 shared-data platform (/shared/*)                                <- untouched
  BCAES Canonical Registry (/bcaes/*)                                    <- NEW

    bcaes_registry/models.py       11 registry types, RegistryObject schema
    bcaes_registry/store.py        in-memory CanonicalRegistryStore
    bcaes_registry/graph.py        relationship / transitive-dependency queries
    bcaes_registry/validators.py   6 checks + capability reuse
    bcaes_registry/service.py      BCAESRegistryService (what main.py calls)
```

## Why a fourth, parallel layer rather than folding into an existing one

- **Not folded into Task 4's shared-data layer** (`shared_data/`,
  `SharedRecordStore`): that layer owns *operational data* (identity,
  organizations, notifications — things with real runtime values flowing
  through them). BCAES owns *architectural metadata* (what a capability
  *is*, not data a capability produces). Different object class, different
  lifecycle (data is written continuously; architecture objects are
  registered rarely and mostly read).
- **Not folded into `PackageRegistryService`**: that service is
  certification-domain specific (dataset packages, CERTIFIED/REJECTED
  states). BCAES objects have no certification lifecycle at all.
- **Result**: three independent registries now coexist in one service
  (`PackageRegistryService` for packages, `SharedDataRegistryService` +
  six `SharedRecordStore`s for operational data, `BCAESRegistryService`
  for architecture), each with the storage/validation model that actually
  fits its object class, none sharing code that wasn't already a genuine
  fit (version negotiation is the one deliberate exception — reused as-is
  from `services/shared_version_compatibility.py`, see reviewer_notes.md).

## Dependency Direction

```
bcaes_registry/  --depends on-->  services/shared_version_compatibility.py
                                    (negotiate_version, reused not duplicated)

bcaes_registry/  --no dependency on-->  services/mdu_client.py
                                          services/mdu_contract_adapter.py
                                          shared_data/*
                                          services/package_registry_service.py

main.py  --depends on-->  bcaes_registry/service.py  (one import block,
                            one instantiation, 14 routes — same pattern as
                            every other service in this file)
```

No existing dependency edge in the service changed direction or was
removed.
