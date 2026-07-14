"""
Generic, reusable persistence + audit engine for MASTERDB's shared
ecosystem datasets (Task 4 — Shared Data Services & MASTERDB Convergence).

This is intentionally generic and dataset-agnostic: every shared dataset
(Authentication, Identity, Organizations, Configuration, Knowledge
References, Notifications, ...) is backed by the SAME engine so behavior
(versioning, replay-safety, audit trail, failure handling) is uniform
across the shared data platform instead of being reimplemented per
dataset. Domain-specific services (services/shared_platform_services.py)
are thin wrappers that only declare a dataset name and a minimal
required-field contract — they must NOT add interpretation or business
logic on top of this engine, per the Task 4 mandate ("No semantic
interpretation. No ontology creation. No governance logic.").
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models import SharedRecord, SharedRecordTransition
from services.artifact_store import ArtifactStore

logger = logging.getLogger("masterdb")


class SharedRecordNotFoundError(KeyError):
    """Raised when a record_id does not exist in a shared dataset store."""


class SharedRecordExistsError(ValueError):
    """Raised on an attempt to register a record_id that already exists."""


class SharedRecordValidationError(ValueError):
    """Raised when a payload is missing a dataset's declared required fields."""


class SharedRecordDeprecatedError(ValueError):
    """Raised when a mutation is attempted against an already-deprecated record."""


class SharedRecordStore:
    """
    One instance = one shared dataset (e.g. "identity", "configuration").

    Storage: one JSON file per record_id, under `store_dir`, via the same
    ArtifactStore used elsewhere in MASTERDB — no new persistence mechanism
    introduced for Task 4.
    """

    def __init__(
        self,
        dataset: str,
        store_dir: str,
        required_fields: Optional[List[str]] = None,
    ) -> None:
        self.dataset = dataset
        self.required_fields = required_fields or []
        self.store = ArtifactStore(reports_dir=store_dir)

    # -- validation ----------------------------------------------------------

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        missing = [f for f in self.required_fields if f not in payload]
        if missing:
            raise SharedRecordValidationError(
                f"[{self.dataset}] payload missing required field(s): {missing}"
            )

    # -- mutation --------------------------------------------------------------

    def register(
        self,
        record_id: str,
        payload: Dict[str, Any],
        actor: str = "system",
        reason: str = "Initial record registration.",
    ) -> SharedRecord:
        if self.store.load(record_id) is not None:
            raise SharedRecordExistsError(
                f"[{self.dataset}] record_id={record_id} already exists; use "
                "update() instead of register()."
            )
        self._validate_payload(payload)
        record = SharedRecord(
            record_id=record_id, dataset=self.dataset, payload=payload, version=1
        )
        record.history.append(
            SharedRecordTransition(version=1, action="REGISTERED", actor=actor, reason=reason)
        )
        logger.info(
            "shared record registered dataset=%s record_id=%s actor=%s",
            self.dataset, record_id, actor,
        )
        return self._save(record)

    def update(
        self, record_id: str, payload: Dict[str, Any], actor: str, reason: str
    ) -> SharedRecord:
        record = self.get(record_id)
        if record.deprecated:
            raise SharedRecordDeprecatedError(
                f"[{self.dataset}] record_id={record_id} is deprecated and cannot be updated."
            )
        self._validate_payload(payload)
        record.payload = payload
        record.version += 1
        record.updated_at = datetime.now(timezone.utc).isoformat()
        record.history.append(
            SharedRecordTransition(version=record.version, action="UPDATED", actor=actor, reason=reason)
        )
        logger.info(
            "shared record updated dataset=%s record_id=%s version=%s actor=%s",
            self.dataset, record_id, record.version, actor,
        )
        return self._save(record)

    def deprecate(self, record_id: str, actor: str, reason: str) -> SharedRecord:
        record = self.get(record_id)
        if record.deprecated:
            raise SharedRecordDeprecatedError(
                f"[{self.dataset}] record_id={record_id} is already deprecated."
            )
        record.deprecated = True
        record.version += 1
        record.updated_at = datetime.now(timezone.utc).isoformat()
        record.history.append(
            SharedRecordTransition(version=record.version, action="DEPRECATED", actor=actor, reason=reason)
        )
        logger.info(
            "shared record deprecated dataset=%s record_id=%s actor=%s",
            self.dataset, record_id, actor,
        )
        return self._save(record)

    # -- reads --------------------------------------------------------------

    def get(self, record_id: str) -> SharedRecord:
        raw = self.store.load(record_id)
        if raw is None:
            raise SharedRecordNotFoundError(
                f"[{self.dataset}] no record found for record_id={record_id}"
            )
        return SharedRecord(**raw)

    def exists(self, record_id: str) -> bool:
        return self.store.load(record_id) is not None

    def list_all(self) -> List[SharedRecord]:
        return [SharedRecord(**raw) for raw in self.store.list_all()]

    def history(self, record_id: str) -> List[SharedRecordTransition]:
        return self.get(record_id).history

    def replay(self, record_id: str) -> Dict[str, Any]:
        """
        Phase 5 — replay consistency. Rebuilds version/deprecated state
        purely from the recorded transition history and compares it against
        the stored record, so drift/corruption is detectable instead of
        silently trusted. Never raises for a bad history — returns a report
        with `replay_consistent: False` so a caller (API included) can
        surface it rather than crash.
        """
        record = self.get(record_id)
        replayed_version = 0
        replayed_deprecated = False
        for index, transition in enumerate(record.history):
            expected_version = index + 1
            if transition.version != expected_version:
                return {
                    "record_id": record_id,
                    "replay_consistent": False,
                    "replay_error": (
                        f"transition {transition.transition_id} has version "
                        f"{transition.version}, expected {expected_version}."
                    ),
                }
            replayed_version = transition.version
            if transition.action == "DEPRECATED":
                replayed_deprecated = True

        consistent = (
            replayed_version == record.version
            and replayed_deprecated == record.deprecated
        )
        return {
            "record_id": record_id,
            "replay_consistent": consistent,
            "replayed_version": replayed_version,
            "replayed_deprecated": replayed_deprecated,
            "stored_version": record.version,
            "stored_deprecated": record.deprecated,
        }

    # -- internal --------------------------------------------------------------

    def _save(self, record: SharedRecord) -> SharedRecord:
        self.store.save(record.record_id, record.model_dump(mode="json"))
        return record
