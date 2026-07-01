from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CertificationState(str, Enum):
    NEW = "NEW"
    VALIDATED = "VALIDATED"
    VERIFIED = "VERIFIED"
    CERTIFIED = "CERTIFIED"
    REJECTED = "REJECTED"


class ValidationRequest(BaseModel):
    dataset_path: str
    metadata_path: Optional[str] = None
    dataset_id: Optional[str] = None


class CertificationRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    metadata_path: Optional[str] = None


class TransitionRecord(BaseModel):
    from_state: CertificationState
    to_state: CertificationState
    rule: str
    passed: bool
    reason: str


class IngestionDecision(BaseModel):
    dataset_id: str
    eligible_for_masterdb: bool
    state: CertificationState
    classification: str
    integrity_score: float
    rejection_reasons: List[str] = Field(default_factory=list)
    audit_trail: List[TransitionRecord] = Field(default_factory=list)


class ServiceResponse(BaseModel):
    dataset_id: str
    state: CertificationState
    report: Dict[str, Any]

