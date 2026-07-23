import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def _fresh_repository():
    main.canonical_repository_service = main.CanonicalRepositoryService()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def _register(client, category="bcaes_vol_4", **overrides):
    body = {"category": category, "title": "BCAES Volume 4", "owner": "Kavy"}
    body.update(overrides)
    return client.post("/canonical-repository/documents", params={"actor": "Kavy"}, json=body)


def test_register_creates_placeholder_by_default(client):
    resp = _register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "placeholder"
    assert body["current_version"] == 1


def test_registered_placeholder_content_is_labeled(client):
    doc = _register(client).json()
    resp = client.get(f"/canonical-repository/documents/{doc['id']}/latest", params={"actor": "x"})
    body = resp.json()
    assert body["is_placeholder"] is True
    assert "PLACEHOLDER" in body["content"]
    assert "bcaes_vol_4" in body["content"]


def test_register_with_explicit_content_is_not_placeholder(client):
    resp = _register(client, category="bcaes_vol_5", initial_content="real seed text")
    body = resp.json()
    assert body["status"] == "draft"
    latest = client.get(f"/canonical-repository/documents/{body['id']}/latest", params={"actor": "x"})
    assert latest.json()["is_placeholder"] is False
    assert latest.json()["content"] == "real seed text"


def test_duplicate_category_rejected(client):
    _register(client, category="bcaes_vol_6")
    resp = _register(client, category="bcaes_vol_6")
    assert resp.status_code == 409


def test_unknown_category_404(client):
    resp = client.get("/canonical-repository/by-category/not_a_volume", params={"actor": "x"})
    assert resp.status_code == 404


def test_get_by_category(client):
    doc = _register(client, category="bcab").json()
    resp = client.get("/canonical-repository/by-category/bcab", params={"actor": "x"})
    assert resp.status_code == 200
    assert resp.json()["id"] == doc["id"]


def test_publish_version_increments_and_updates_status(client):
    doc = _register(client).json()
    resp = client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "TaskLead"},
        json={"content": "Real BCAES Vol 4 text.", "change_note": "centrally populated", "published_by": "TaskLead"},
    )
    assert resp.status_code == 200
    version = resp.json()
    assert version["version_number"] == 2
    assert version["is_placeholder"] is False

    updated_doc = client.get(f"/canonical-repository/documents/{doc['id']}", params={"actor": "x"}).json()
    assert updated_doc["status"] == "published"
    assert updated_doc["current_version"] == 2


def test_publish_version_missing_document_404(client):
    resp = client.post(
        "/canonical-repository/documents/doc-nonexistent/versions",
        params={"actor": "x"},
        json={"content": "c", "change_note": "n", "published_by": "x"},
    )
    assert resp.status_code == 404


def test_version_history_is_append_only(client):
    doc = _register(client).json()
    client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "x"},
        json={"content": "v2", "change_note": "n", "published_by": "x"},
    )
    client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "x"},
        json={"content": "v3", "change_note": "n", "published_by": "x"},
    )
    resp = client.get(f"/canonical-repository/documents/{doc['id']}/versions", params={"actor": "x"})
    versions = resp.json()["versions"]
    assert [v["version_number"] for v in versions] == [1, 2, 3]
    assert versions[0]["content"] != versions[1]["content"] != versions[2]["content"]


def test_get_specific_version(client):
    doc = _register(client).json()
    client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "x"},
        json={"content": "v2 text", "change_note": "n", "published_by": "x"},
    )
    resp = client.get(f"/canonical-repository/documents/{doc['id']}/versions/2", params={"actor": "x"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "v2 text"


def test_get_missing_version_404(client):
    doc = _register(client).json()
    resp = client.get(f"/canonical-repository/documents/{doc['id']}/versions/99", params={"actor": "x"})
    assert resp.status_code == 404


def test_verify_chain_intact(client):
    doc = _register(client).json()
    client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "x"},
        json={"content": "v2", "change_note": "n", "published_by": "x"},
    )
    resp = client.get(f"/canonical-repository/documents/{doc['id']}/verify", params={"actor": "x"})
    body = resp.json()
    assert body["chain_intact"] is True
    assert body["versions_checked"] == 2
    assert body["mismatched_versions"] == []


def test_list_documents(client):
    _register(client, category="bcaes_vol_1")
    _register(client, category="bcaes_vol_2")
    resp = client.get("/canonical-repository/documents", params={"actor": "x"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_access_policy_defaults_present_but_not_enforced(client):
    """Schema-only pass (confirmed 2026-07-22): an actor with no declared
    roles can still read and write. This test pins that down explicitly so
    a future enforcement change is a deliberate, visible diff here rather
    than a silent behavior change."""
    doc = _register(client).json()
    assert doc["access_policy"]["read_roles"] == ["ecosystem-reader"]
    assert doc["access_policy"]["write_roles"] == ["bcaes-editor"]

    resp = client.post(
        f"/canonical-repository/documents/{doc['id']}/versions",
        params={"actor": "nobody", "roles": ""},
        json={"content": "unauthorized-looking write", "change_note": "n", "published_by": "nobody"},
    )
    assert resp.status_code == 200


def test_custom_access_policy_is_stored(client):
    resp = _register(
        client,
        category="bcaes_vol_7",
        access_policy={"read_roles": ["tantra-runtime"], "write_roles": ["gc-team"]},
    )
    body = resp.json()
    assert body["access_policy"]["read_roles"] == ["tantra-runtime"]
    assert body["access_policy"]["write_roles"] == ["gc-team"]
