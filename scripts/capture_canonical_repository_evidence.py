"""Live-captured evidence for the Canonical Document Repository, driven
through a real TestClient against the running app (same pattern as
scripts/capture_bcaes_evidence.py)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "review_packets" / "api_responses_canonical_repository"
OUT.mkdir(parents=True, exist_ok=True)

main.canonical_repository_service = main.CanonicalRepositoryService()
client = TestClient(main.app)


def dump(name: str, resp) -> None:
    (OUT / f"{name}.json").write_text(json.dumps({"status_code": resp.status_code, "body": resp.json()}, indent=2))
    print(f"wrote {name}.json [{resp.status_code}]")


doc = client.post(
    "/canonical-repository/documents",
    params={"actor": "Kavy"},
    json={"category": "bcaes_vol_4", "title": "BCAES Volume 4 - Master Product & Capability Registry", "owner": "Kavy"},
)
dump("01_post_register_placeholder_document", doc)
doc_id = doc.json()["id"]

dump("02_get_latest_shows_placeholder", client.get(f"/canonical-repository/documents/{doc_id}/latest", params={"actor": "x"}))
dump("03_post_duplicate_category_409", client.post(
    "/canonical-repository/documents", params={"actor": "x"},
    json={"category": "bcaes_vol_4", "title": "dup", "owner": "x"},
))
dump("04_get_unknown_category_404", client.get("/canonical-repository/by-category/not_a_volume", params={"actor": "x"}))
dump("05_post_publish_real_version", client.post(
    f"/canonical-repository/documents/{doc_id}/versions", params={"actor": "TaskLead"},
    json={"content": "Real BCAES Vol 4 content would go here.", "change_note": "centrally populated", "published_by": "TaskLead"},
))
dump("06_get_version_history", client.get(f"/canonical-repository/documents/{doc_id}/versions", params={"actor": "x"}))
dump("07_get_verify_chain_intact", client.get(f"/canonical-repository/documents/{doc_id}/verify", params={"actor": "x"}))
dump("08_get_document_status_now_published", client.get(f"/canonical-repository/documents/{doc_id}", params={"actor": "x"}))
dump("09_get_list_all_documents", client.get("/canonical-repository/documents", params={"actor": "x"}))

openapi = client.get("/openapi.json").json()
paths = sorted(p for p in openapi["paths"] if p.startswith("/canonical-repository"))
(OUT / "10_openapi_paths.json").write_text(json.dumps(paths, indent=2))
print(f"wrote 10_openapi_paths.json ({len(paths)} paths)")
print("\nAll responses above came from a live TestClient hitting main.app.")
