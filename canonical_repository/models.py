"""
BCAES/BCAB Canonical Document Repository — data models.

Per the task lead's instruction (2026-07-22): this is the single source of
truth for BCAB and BCAES Volume 1-7 documents inside MASTERDB. Kavy is
explicitly NOT to implement against personal copies of those documents —
the canonical *content* is populated centrally once this repository is
ready. Until then, documents carry clearly-labeled placeholder content so
the API is demonstrable end-to-end.

Scope decisions made explicit here (confirmed 2026-07-22):
- Access control is SCHEMA-ONLY in this pass: every document declares
  `read_roles` / `write_roles`, and every mutating/reading call accepts an
  `actor` + `actor_roles` the caller self-reports — but nothing in
  `service.py` currently rejects a call whose roles don't match. That's a
  deliberate placeholder for a real identity layer (this whole repo has no
  auth anywhere yet), not an oversight. See `service.py` module docstring
  for exactly where enforcement would plug in.
- Content is placeholder, not real BCAB/BCAES text, and is labeled as such
  in every response so nobody mistakes it for the real thing.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentCategory(str, Enum):
    BCAB = "bcab"
    BCAES_VOL_1 = "bcaes_vol_1"
    BCAES_VOL_2 = "bcaes_vol_2"
    BCAES_VOL_3 = "bcaes_vol_3"
    BCAES_VOL_4 = "bcaes_vol_4"
    BCAES_VOL_5 = "bcaes_vol_5"
    BCAES_VOL_6 = "bcaes_vol_6"
    BCAES_VOL_7 = "bcaes_vol_7"


class DocumentStatus(str, Enum):
    PLACEHOLDER = "placeholder"  # no centrally-populated content yet
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class AccessPolicy(BaseModel):
    """Declared, not enforced, in this pass — see module docstring."""

    read_roles: List[str] = Field(default_factory=lambda: ["ecosystem-reader"])
    write_roles: List[str] = Field(default_factory=lambda: ["bcaes-editor"])


class RegisterDocumentRequest(BaseModel):
    category: DocumentCategory
    title: str
    owner: str
    access_policy: Optional[AccessPolicy] = None
    initial_content: Optional[str] = None
    change_note: str = "Initial registration."


class PublishVersionRequest(BaseModel):
    content: str
    change_note: str
    published_by: str


class DocumentVersion(BaseModel):
    """Immutable once created — a new call to publish a version always
    appends a new DocumentVersion rather than mutating an existing one,
    so `content_hash` chains give a real, checkable provenance trail."""

    document_id: str
    version_number: int
    content: str
    content_hash: str
    change_note: str
    published_by: str
    published_at: str = Field(default_factory=_utcnow)
    is_placeholder: bool = False


class CanonicalDocument(BaseModel):
    id: str
    category: DocumentCategory
    title: str
    owner: str
    status: DocumentStatus
    access_policy: AccessPolicy
    current_version: int
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
