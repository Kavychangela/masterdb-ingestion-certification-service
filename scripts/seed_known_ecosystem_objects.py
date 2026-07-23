"""
Seeds the BCAES Canonical Registry with the ecosystem objects the task
brief itself names explicitly in its "Integration Block" — real owners,
real roles, nothing invented. This is NOT the full BCAB/BCAES catalog
(that still doesn't exist anywhere accessible — see
BCAES_REGISTRY_ARCHITECTURE.md §8) — it's the subset of objects and
owners the brief already tells us are real.

Deliberately excluded: BCAB itself (a governing document/methodology,
not a runtime object this registry catalogs), and TMS (named only in the
bare "Dependencies" list with no owner or role given anywhere in the
brief — registering it would mean guessing an owner, which is exactly
the "no hidden ownership" rule this registry exists to prevent).

Run against a live process: python scripts/seed_known_ecosystem_objects.py
Note: the store is in-memory (see BCAES_REGISTRY_ARCHITECTURE.md §5), so
this only populates whatever process runs it — it does not persist across
a restart of `main.py` until/unless disk persistence is added.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

client = TestClient(main.app)


def register(registry_type: str, name: str, purpose: str, owner: str, authority_boundaries=None):
    body = {
        "name": name,
        "purpose": purpose,
        "owner": owner,
        "status": "active",
        "authority_boundaries": authority_boundaries or [owner],
    }
    resp = client.post(f"/bcaes/registries/{registry_type}/objects", json=body)
    if resp.status_code != 200:
        print(f"FAILED to register {name}: {resp.status_code} {resp.text}")
        return None
    obj = resp.json()
    print(f"registered {registry_type}/{obj['id']} — {name} (owner: {owner})")
    return obj


# --- Runtime -----------------------------------------------------------
tantra = register(
    "runtime", "TANTRA", "Sovereign Core / TANTRA Runtime — runtime discovery, "
    "execution contracts, capability discovery.", "Rajaryan",
)

# --- Platform services ---------------------------------------------------
mdu = register(
    "platform_service", "MDU", "Registry schemas, provenance, version "
    "compatibility, Semantic Registry, replay metadata, schema governance.",
    "Nupur",
)
bucket = register(
    "platform_service", "Bucket", "Evidence Registry, Replay Registry, "
    "provenance storage, Central Depository, artifact storage.", "Ashmit",
)
insightflow = register(
    "platform_service", "InsightFlow / Pravah", "Runtime Explorer, Dependency "
    "Explorer, Executive Dashboard, observability integration, runtime "
    "telemetry.", "InsightFlow / Pravah Owner",
)
gc = register(
    "platform_service", "GC", "Authority Matrix, Decision Ledger, Doctrine "
    "Registry, constitutional validation, governance boundaries.", "GC Team",
)

# --- Products ------------------------------------------------------------
masterdb = register(
    "product", "MASTERDB", "Knowledge Registry, Dataset Registry, Knowledge "
    "Grounding, registry synchronization.", "MasterDB Team",
    authority_boundaries=["MasterDB Team", "Kavy"],
)
setu = register(
    "product", "SETU", "Registry consumption inside operational systems.",
    "SETU Team",
)

# --- Integration: this specific service's registration into the bootstrap -
masterdb_ingestion_service = register(
    "integration",
    "MASTERDB Ingestion Certification Service",
    "Dataset validation/certification, Knowledge Package Lifecycle, "
    "Provenance/Lineage, Retrieval Readiness; exposes MDU client, TANTRA "
    "interface, and Runtime Discovery API.",
    "Kavy",
    authority_boundaries=["Kavy", "Nupur", "Rajaryan"],
)

print("\nSeed complete. Objects registered only where the task brief names a")
print("real owner/role; TMS and BCAB were deliberately left out (see module")
print("docstring). Run GET /bcaes/registries or /bcaes/snapshot to inspect.")
