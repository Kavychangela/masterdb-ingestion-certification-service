"""
Runtime Discovery Service.

Gives downstream systems (TANTRA and others) one deterministic surface to
find Knowledge Packages by any combination of package_id, dataset_id,
board, medium, version (dataset_version or schema_version), and lifecycle
status — without needing to know MASTERDB's internal storage layout.

This is a read-only filter over PackageRegistryService's system of record.
It does not mutate state, does not perform ranking/relevance scoring (no
retrieval/RAG semantics — that is explicitly out of scope for MASTERDB),
and always returns results in a stable sort order so identical queries
against identical state are byte-for-byte replayable.
"""
from typing import Any, Dict, List, Optional

from models import KnowledgePackage, PackageStatus
from services.package_registry_service import PackageRegistryService


class RuntimeDiscoveryService:
    def __init__(self, registry: Optional[PackageRegistryService] = None) -> None:
        self.registry = registry or PackageRegistryService()

    def discover(
        self,
        package_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        board: Optional[str] = None,
        medium: Optional[str] = None,
        version: Optional[str] = None,
        status: Optional[PackageStatus] = None,
    ) -> List[KnowledgePackage]:
        records = self.registry.store.list_all()
        packages = [KnowledgePackage(**record) for record in records]

        def matches(pkg: KnowledgePackage) -> bool:
            if package_id and pkg.package_id != package_id:
                return False
            if dataset_id and pkg.dataset_id != dataset_id:
                return False
            if board and pkg.board != board:
                return False
            if medium and pkg.medium != medium:
                return False
            if version and version not in (pkg.dataset_version, pkg.schema_version):
                return False
            if status and pkg.status != status:
                return False
            return True

        results = [pkg for pkg in packages if matches(pkg)]
        # Deterministic ordering independent of filesystem iteration order:
        # sort by package_id so repeated identical queries always return
        # results in the same sequence.
        results.sort(key=lambda pkg: pkg.package_id)
        return results

    def discover_as_dicts(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return [pkg.model_dump(mode="json") for pkg in self.discover(**kwargs)]
