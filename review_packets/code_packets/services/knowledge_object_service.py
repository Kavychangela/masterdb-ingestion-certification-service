"""
Knowledge Object & Provenance Engine.

Supports canonical Knowledge Packages: identity, lineage pointers, and
parent/child relationship validation, layered on top of the Dataset
Registry. Semantics for Knowledge Object / Provenance / Lineage are owned by
MDU (Nupur); this module consumes them through MDUContractAdapter rather
than inventing competing definitions. Where MDU has not yet finalized a
field, this module treats it as optional and records the gap instead of
enforcing an invented rule.
"""
import hashlib
from typing import Any, Dict, List, Optional

from models import KnowledgeObject
from services.artifact_store import ArtifactStore
from services.mdu_contract_adapter import MDUContractAdapter
from services.package_registry_service import PackageNotFoundError, PackageRegistryService


class KnowledgeObjectNotFoundError(KeyError):
    pass


class VersionIncompatibleError(ValueError):
    pass


class LineageValidationError(ValueError):
    pass


class KnowledgeObjectService:
    def __init__(
        self,
        registry: Optional[PackageRegistryService] = None,
        store_dir: str = "knowledge_object_store",
        mdu_adapter: Optional[MDUContractAdapter] = None,
    ) -> None:
        self.registry = registry or PackageRegistryService()
        self.store = ArtifactStore(reports_dir=store_dir)
        self.mdu_adapter = mdu_adapter or MDUContractAdapter()

    def register_object(
        self,
        package_id: str,
        parent_package: Optional[str] = None,
        child_packages: Optional[List[str]] = None,
        source_reference: Optional[str] = None,
        lineage_reference: Optional[str] = None,
        derivation_path: Optional[List[str]] = None,
    ) -> KnowledgeObject:
        package = self.registry.get(package_id)  # raises PackageNotFoundError

        parent_object: Optional[KnowledgeObject] = None
        if parent_package:
            try:
                self.registry.get(parent_package)
            except PackageNotFoundError as exc:
                raise LineageValidationError(
                    f"parent_package {parent_package} does not exist in the registry."
                ) from exc
            parent_object = self.get_by_package(parent_package)
            if parent_object:
                self._validate_version_compatibility(package.schema_version, parent_object.schema_version)

        knowledge_object = KnowledgeObject(
            knowledge_hash=self._compute_hash(
                package_id, source_reference, derivation_path or []
            ),
            package_id=package_id,
            schema_version=package.schema_version,
            parent_package=parent_package,
            child_packages=child_packages or [],
            source_reference=source_reference,
            lineage_reference=lineage_reference,
            derivation_path=derivation_path or [],
        )

        # relationship validation: keep parent's child_packages in sync
        if parent_object:
            if package_id not in parent_object.child_packages:
                parent_object.child_packages.append(package_id)
                self._save(parent_object)

        return self._save(knowledge_object)

    def get(self, knowledge_object_id: str) -> KnowledgeObject:
        raw = self.store.load(knowledge_object_id)
        if raw is None:
            raise KnowledgeObjectNotFoundError(
                f"No knowledge object found for knowledge_object_id={knowledge_object_id}"
            )
        return KnowledgeObject(**raw)

    def get_by_package(self, package_id: str) -> Optional[KnowledgeObject]:
        # Knowledge objects are stored keyed by package_id as a convenience
        # index alongside their canonical knowledge_object_id key.
        raw = self.store.load(f"by-package-{package_id}")
        if raw is None:
            return None
        return KnowledgeObject(**raw)

    def lineage(self, package_id: str) -> Dict[str, Any]:
        knowledge_object = self.get_by_package(package_id)
        mdu_provenance = self._consume_mdu_provenance(package_id)

        if knowledge_object is None:
            return {
                "package_id": package_id,
                "knowledge_object_registered": False,
                "ancestors": [],
                "descendants": [],
                "known_gaps": self.mdu_adapter.known_gaps(),
                "mdu_provenance": mdu_provenance,
            }

        ancestors: List[str] = []
        current = knowledge_object
        visited = {package_id}
        while current.parent_package:
            if current.parent_package in visited:
                break  # guard against corrupt cyclic data
            ancestors.append(current.parent_package)
            visited.add(current.parent_package)
            parent_object = self.get_by_package(current.parent_package)
            if parent_object is None:
                break
            current = parent_object

        return {
            "package_id": package_id,
            "knowledge_object_registered": True,
            "knowledge_object_id": knowledge_object.knowledge_object_id,
            "knowledge_hash": knowledge_object.knowledge_hash,
            "source_reference": knowledge_object.source_reference,
            "lineage_reference": knowledge_object.lineage_reference,
            "derivation_path": knowledge_object.derivation_path,
            "ancestors": ancestors,
            "descendants": knowledge_object.child_packages,
            "known_gaps": self.mdu_adapter.known_gaps(),
            "mdu_provenance": mdu_provenance,
        }

    def _consume_mdu_provenance(self, package_id: str) -> Dict[str, Any]:
        """
        Phase 1 — live lineage/provenance contract consumption.

        MDU's `/provenance` endpoint is documented as the lineage contract
        (there is no separate lineage endpoint). This looks up the
        package's `dataset_id` via the registry (MASTERDB-owned identity)
        and passes it straight through to MDU (MDU-owned semantics) without
        reinterpreting it. Always degrades gracefully — a missing/offline
        MDU never breaks a lineage read that MASTERDB can otherwise answer
        from its own parent/child pointers.
        """
        if not self.mdu_adapter.is_live():
            return {"source": "unavailable", "reason": "MDU not configured."}
        try:
            package = self.registry.get(package_id)
        except PackageNotFoundError:
            return {"source": "unavailable", "reason": "package not found in registry."}
        try:
            provenance = self.mdu_adapter.fetch_provenance_contract(package.dataset_id)
            return {"source": "mdu-live", "dataset_id": package.dataset_id, "provenance": provenance}
        except Exception as exc:  # noqa: BLE001 - MDU failures must never break lineage reads
            return {
                "source": "unavailable",
                "dataset_id": package.dataset_id,
                "reason": f"MDU provenance fetch failed: {exc}",
            }

    # -- internal -------------------------------------------------------------

    @staticmethod
    def _compute_hash(
        package_id: str, source_reference: Optional[str], derivation_path: List[str]
    ) -> str:
        digest = hashlib.sha256()
        digest.update(package_id.encode("utf-8"))
        digest.update((source_reference or "").encode("utf-8"))
        for step in derivation_path:
            digest.update(step.encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _validate_version_compatibility(child_schema_version: str, parent_schema_version: str) -> None:
        """
        Placeholder compatibility rule pending MDU's versioning contract:
        require matching major schema version (the segment before the first
        dot) between a package and its declared parent.
        """
        def major(version: str) -> str:
            return version.split(".", 1)[0]

        if major(child_schema_version) != major(parent_schema_version):
            raise VersionIncompatibleError(
                f"schema_version {child_schema_version} is not compatible with "
                f"parent schema_version {parent_schema_version} "
                f"(major version mismatch)."
            )

    def _save(self, knowledge_object: KnowledgeObject) -> KnowledgeObject:
        payload = knowledge_object.model_dump(mode="json")
        self.store.save(knowledge_object.knowledge_object_id, payload)
        self.store.save(f"by-package-{knowledge_object.package_id}", payload)
        return knowledge_object
