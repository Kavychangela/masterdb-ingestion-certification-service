"""
BCAES Canonical Registry — data models.

Design decision (kept deliberately simple, see BCAES_REGISTRY_ARCHITECTURE.md
"Why classification == registry_type"): an object's *primary classification*
is structurally the registry it lives in. There are exactly eleven canonical
registries (BCAES Volumes 1-3), so an object can never carry more than one
classification — this satisfies "every architectural object must have one
primary classification" and "no semantic drift" by construction, without a
separate free-text classification vocabulary that could drift over time.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegistryType(str, Enum):
    DOMAIN = "domain"
    CAPABILITY = "capability"
    PLATFORM_SERVICE = "platform_service"
    PRODUCT = "product"
    PROGRAM = "program"
    FRAMEWORK = "framework"
    ENGINE = "engine"
    RUNTIME = "runtime"
    INTEGRATION = "integration"
    KNOWLEDGE_ASSET = "knowledge_asset"
    INTERFACE = "interface"


_ID_PREFIX: Dict[RegistryType, str] = {
    RegistryType.DOMAIN: "dom",
    RegistryType.CAPABILITY: "cap",
    RegistryType.PLATFORM_SERVICE: "psv",
    RegistryType.PRODUCT: "prd",
    RegistryType.PROGRAM: "prg",
    RegistryType.FRAMEWORK: "frw",
    RegistryType.ENGINE: "eng",
    RegistryType.RUNTIME: "run",
    RegistryType.INTEGRATION: "itg",
    RegistryType.KNOWLEDGE_ASSET: "kas",
    RegistryType.INTERFACE: "ifc",
}


def new_object_id(registry_type: RegistryType) -> str:
    prefix = _ID_PREFIX[registry_type]
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ObjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DependencyRef(BaseModel):
    """A declared dependency on another registry object, with an optional
    version pin used by the version-compatibility validator."""

    id: str
    required_version: Optional[str] = None


class RegisterObjectRequest(BaseModel):
    name: str
    purpose: str
    owner: str
    status: ObjectStatus = ObjectStatus.DRAFT
    version: str = "1.0"
    authority_boundaries: List[str] = Field(default_factory=list)
    dependencies: List[DependencyRef] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)

    @field_validator("name", "purpose", "owner")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class UpdateObjectRequest(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[ObjectStatus] = None
    version: Optional[str] = None
    authority_boundaries: Optional[List[str]] = None
    dependencies: Optional[List[DependencyRef]] = None
    links: Optional[List[str]] = None


class RegistryObject(BaseModel):
    """A single canonical architectural object.

    `consumers` is never written directly by a caller — it is derived from
    every other object's `dependencies` so it can never drift out of sync
    with the dependency edges it mirrors.
    """

    id: str
    registry_type: RegistryType
    classification: RegistryType  # == registry_type, see module docstring
    name: str
    purpose: str
    owner: str
    status: ObjectStatus
    version: str
    dependencies: List[DependencyRef]
    consumers: List[str]
    authority_boundaries: List[str]
    links: List[str]
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
