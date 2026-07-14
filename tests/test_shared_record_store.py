import shutil

import pytest

from services.shared_record_store import (
    SharedRecordDeprecatedError,
    SharedRecordExistsError,
    SharedRecordNotFoundError,
    SharedRecordStore,
    SharedRecordValidationError,
)

STORE_DIR = "test_shared_record_store"


@pytest.fixture
def store():
    shutil.rmtree(STORE_DIR, ignore_errors=True)
    s = SharedRecordStore(
        dataset="widgets", store_dir=STORE_DIR, required_fields=["name"]
    )
    yield s
    shutil.rmtree(STORE_DIR, ignore_errors=True)


def test_register_creates_record_at_version_1(store):
    record = store.register("rec-1", {"name": "Widget A"}, actor="kavy", reason="init")
    assert record.record_id == "rec-1"
    assert record.dataset == "widgets"
    assert record.version == 1
    assert record.deprecated is False
    assert len(record.history) == 1
    assert record.history[0].action == "REGISTERED"


def test_register_missing_required_field_raises_validation_error(store):
    with pytest.raises(SharedRecordValidationError):
        store.register("rec-2", {"not_name": "oops"}, actor="kavy", reason="init")


def test_register_duplicate_record_id_raises_exists_error(store):
    store.register("rec-3", {"name": "Widget C"}, actor="kavy", reason="init")
    with pytest.raises(SharedRecordExistsError):
        store.register("rec-3", {"name": "Widget C again"}, actor="kavy", reason="dup")


def test_get_missing_record_raises_not_found(store):
    with pytest.raises(SharedRecordNotFoundError):
        store.get("does-not-exist")


def test_update_increments_version_and_appends_history(store):
    store.register("rec-4", {"name": "Widget D"}, actor="kavy", reason="init")
    updated = store.update("rec-4", {"name": "Widget D2"}, actor="kavy", reason="rename")
    assert updated.version == 2
    assert updated.payload["name"] == "Widget D2"
    assert len(updated.history) == 2
    assert updated.history[-1].action == "UPDATED"


def test_update_validates_required_fields(store):
    store.register("rec-5", {"name": "Widget E"}, actor="kavy", reason="init")
    with pytest.raises(SharedRecordValidationError):
        store.update("rec-5", {"missing": True}, actor="kavy", reason="bad update")


def test_deprecate_marks_record_and_blocks_further_updates(store):
    store.register("rec-6", {"name": "Widget F"}, actor="kavy", reason="init")
    deprecated = store.deprecate("rec-6", actor="kavy", reason="retired")
    assert deprecated.deprecated is True
    assert deprecated.version == 2

    with pytest.raises(SharedRecordDeprecatedError):
        store.update("rec-6", {"name": "Widget F2"}, actor="kavy", reason="should fail")

    with pytest.raises(SharedRecordDeprecatedError):
        store.deprecate("rec-6", actor="kavy", reason="double deprecate")


def test_history_and_list_all(store):
    store.register("rec-7", {"name": "Widget G"}, actor="kavy", reason="init")
    store.update("rec-7", {"name": "Widget G2"}, actor="kavy", reason="rename")
    history = store.history("rec-7")
    assert [t.action for t in history] == ["REGISTERED", "UPDATED"]

    store.register("rec-8", {"name": "Widget H"}, actor="kavy", reason="init")
    all_records = store.list_all()
    assert {r.record_id for r in all_records} == {"rec-7", "rec-8"}


def test_replay_is_consistent_for_well_formed_history(store):
    store.register("rec-9", {"name": "Widget I"}, actor="kavy", reason="init")
    store.update("rec-9", {"name": "Widget I2"}, actor="kavy", reason="rename")
    store.deprecate("rec-9", actor="kavy", reason="retired")

    replay = store.replay("rec-9")
    assert replay["replay_consistent"] is True
    assert replay["replayed_version"] == 3
    assert replay["replayed_deprecated"] is True


def test_replay_detects_version_drift(store):
    record = store.register("rec-10", {"name": "Widget J"}, actor="kavy", reason="init")
    # Simulate corruption: tamper with the stored version without a matching
    # transition, then confirm replay flags the drift instead of trusting it.
    raw = store.store.load("rec-10")
    raw["version"] = 99
    store.store.save("rec-10", raw)

    replay = store.replay("rec-10")
    assert replay["replay_consistent"] is False
