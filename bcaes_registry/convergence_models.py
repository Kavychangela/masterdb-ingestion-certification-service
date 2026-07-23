"""
BCAES Production Convergence — data models (BCAES Volume 6).

Design decision: convergence status is *declared*, not inferred by probing
live systems. This service has no network reach into TANTRA, MDU, Bucket,
or InsightFlow, so it cannot itself measure "SDK adoption" or "observability
status" for a product. What it *can* do — and what satisfies "production
convergence is measurable" — is give every registered object a single,
versioned, queryable place to declare and update those statuses, so the
number stops living in a spreadsheet or a person's head. Each collaborating
team (or the object owner) is the source of truth for their own dimension,
the same way `owner` and `authority_boundaries` already work on
RegistryObject.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConvergenceStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class ConvergenceDimensions(BaseModel):
    """The eight dimensions Phase 4 of the task brief requires every
    product to expose. `production_readiness` is a ninth, summary field —
    it is declared explicitly rather than auto-derived from the other
    eight, because a product owner may have a valid reason to call
    something production-ready (or not) that a simple AND/OR over the
    other fields would get wrong."""

    integration_status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    sdk_adoption: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    replay_status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    observability_status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    evidence_status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    governance_status: ConvergenceStatus = ConvergenceStatus.NOT_STARTED
    production_readiness: ConvergenceStatus = ConvergenceStatus.NOT_STARTED


class ConvergenceUpdateRequest(ConvergenceDimensions):
    """All dimension fields are optional on update (partial patch); at
    least one must differ from NOT_STARTED to be a meaningful call, but
    that is not enforced — an owner resetting a dimension back to
    not_started is a legitimate correction, not an error."""

    remaining_work: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class ConvergenceRecord(ConvergenceDimensions):
    object_id: str
    remaining_work: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    updated_at: str = Field(default_factory=_utcnow)

    @property
    def maturity_score(self) -> float:
        """Fraction of the seven tracked dimensions marked COMPLETE.
        production_readiness counts like any other dimension here —
        it is a declared status, not a gate — so this score is a rough
        convergence signal, not a pass/fail production gate."""
        fields = [
            self.integration_status,
            self.sdk_adoption,
            self.replay_status,
            self.observability_status,
            self.evidence_status,
            self.governance_status,
            self.production_readiness,
        ]
        complete = sum(1 for f in fields if f == ConvergenceStatus.COMPLETE)
        return round(complete / len(fields), 4)
