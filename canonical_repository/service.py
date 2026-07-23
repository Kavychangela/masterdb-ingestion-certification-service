"""
BCAES/BCAB Canonical Document Repository — service layer.

WHERE ACCESS ENFORCEMENT PLUGS IN LATER: every read/write method below
accepts `actor` and `actor_roles` and currently does nothing with them
except record `published_by` on writes. To turn this into real
enforcement once a real identity layer exists, the change is localized:
add a check here (e.g. `if not set(actor_roles) & set(document.access_
policy.write_roles): raise PermissionError(...)`) before the mutating
calls, and the same for reads against `read_roles`. Nothing above this
layer (main.py routes) or below it (store.py) needs to change.
"""
from typing import Dict, List, Optional

from canonical_repository.models import (
    AccessPolicy,
    CanonicalDocument,
    DocumentCategory,
    DocumentVersion,
    PublishVersionRequest,
    RegisterDocumentRequest,
)
from canonical_repository.store import (
    CanonicalRepositoryStore,
    DocumentNotFoundError,
    DuplicateCategoryError,
)

__all__ = [
    "CanonicalRepositoryService",
    "DocumentNotFoundError",
    "DuplicateCategoryError",
]

_PLACEHOLDER_TEMPLATE = (
    "[PLACEHOLDER — not the real {category} text]\n\n"
    "This is demo scaffolding for the BCAES Canonical Repository API. "
    "The actual {category} content will be populated centrally by the "
    "BCAES task owner once this repository is confirmed ready — see "
    "CANONICAL_REPOSITORY_ARCHITECTURE.md. Do not treat this content as "
    "authoritative for any architectural decision."
)


class CanonicalRepositoryService:
    def __init__(self) -> None:
        self._store = CanonicalRepositoryStore()

    def register(
        self, request: RegisterDocumentRequest, actor: str, actor_roles: List[str]
    ) -> CanonicalDocument:
        access_policy = request.access_policy or AccessPolicy()
        is_placeholder = request.initial_content is None
        content = request.initial_content or _PLACEHOLDER_TEMPLATE.format(
            category=request.category.value
        )
        return self._store.register(
            category=request.category,
            title=request.title,
            owner=request.owner,
            access_policy=access_policy,
            initial_content=content,
            change_note=request.change_note,
            is_placeholder=is_placeholder,
        )

    def publish_version(
        self,
        document_id: str,
        request: PublishVersionRequest,
        actor: str,
        actor_roles: List[str],
    ) -> DocumentVersion:
        return self._store.publish_version(
            document_id=document_id,
            content=request.content,
            change_note=request.change_note,
            published_by=request.published_by,
        )

    def get(self, document_id: str, actor: str, actor_roles: List[str]) -> CanonicalDocument:
        return self._store.get(document_id)

    def get_by_category(
        self, category: DocumentCategory, actor: str, actor_roles: List[str]
    ) -> CanonicalDocument:
        return self._store.get_by_category(category)

    def list_all(self, actor: str, actor_roles: List[str]) -> List[CanonicalDocument]:
        return self._store.list_all()

    def version_history(
        self, document_id: str, actor: str, actor_roles: List[str]
    ) -> List[DocumentVersion]:
        return self._store.version_history(document_id)

    def get_version(
        self, document_id: str, version_number: int, actor: str, actor_roles: List[str]
    ) -> DocumentVersion:
        return self._store.get_version(document_id, version_number)

    def latest_version(
        self, document_id: str, actor: str, actor_roles: List[str]
    ) -> DocumentVersion:
        return self._store.latest_version(document_id)

    def verify_chain(self, document_id: str, actor: str, actor_roles: List[str]) -> Dict:
        return self._store.verify_chain(document_id)
