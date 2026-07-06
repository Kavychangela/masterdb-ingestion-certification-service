import pytest

from services.knowledge_object_service import (
    KnowledgeObjectService,
    LineageValidationError,
    VersionIncompatibleError,
)
from services.package_registry_service import PackageRegistryService


def make_services(tmp_path):
    registry = PackageRegistryService(store_dir=str(tmp_path / "registry"))
    knowledge_objects = KnowledgeObjectService(
        registry=registry, store_dir=str(tmp_path / "knowledge_objects")
    )
    return registry, knowledge_objects


def register_package(registry, dataset_id, schema_version="2"):
    return registry.register(
        dataset_id=dataset_id,
        dataset_version="1.0.0",
        schema_version=schema_version,
        board="AI",
        medium="text",
        language="en",
        owner="kavy",
    )


def test_register_object_computes_deterministic_hash(tmp_path):
    registry, knowledge_objects = make_services(tmp_path)
    package = register_package(registry, "ds-1")

    knowledge_object = knowledge_objects.register_object(
        package_id=package.package_id,
        source_reference="s3://bucket/source.csv",
        derivation_path=["ingest", "clean"],
    )

    again = knowledge_objects._compute_hash(
        package.package_id, "s3://bucket/source.csv", ["ingest", "clean"]
    )
    assert knowledge_object.knowledge_hash == again


def test_parent_child_relationship_is_tracked(tmp_path):
    registry, knowledge_objects = make_services(tmp_path)
    parent_package = register_package(registry, "ds-parent")
    child_package = register_package(registry, "ds-child")

    knowledge_objects.register_object(
        package_id=parent_package.package_id,
        source_reference="s3://bucket/parent.csv",
    )
    knowledge_objects.register_object(
        package_id=child_package.package_id,
        parent_package=parent_package.package_id,
        source_reference="s3://bucket/child.csv",
        derivation_path=["filter"],
    )

    lineage = knowledge_objects.lineage(child_package.package_id)
    assert lineage["ancestors"] == [parent_package.package_id]

    parent_object = knowledge_objects.get_by_package(parent_package.package_id)
    assert child_package.package_id in parent_object.child_packages


def test_missing_parent_package_raises(tmp_path):
    registry, knowledge_objects = make_services(tmp_path)
    child_package = register_package(registry, "ds-child")

    with pytest.raises(LineageValidationError):
        knowledge_objects.register_object(
            package_id=child_package.package_id,
            parent_package="does-not-exist",
            source_reference="s3://bucket/child.csv",
        )


def test_incompatible_major_schema_version_raises(tmp_path):
    registry, knowledge_objects = make_services(tmp_path)
    parent_package = register_package(registry, "ds-parent", schema_version="2.0")
    child_package = register_package(registry, "ds-child", schema_version="3.0")

    knowledge_objects.register_object(
        package_id=parent_package.package_id,
        source_reference="s3://bucket/parent.csv",
    )

    with pytest.raises(VersionIncompatibleError):
        knowledge_objects.register_object(
            package_id=child_package.package_id,
            parent_package=parent_package.package_id,
            source_reference="s3://bucket/child.csv",
        )


def test_lineage_for_unregistered_object_reports_gap(tmp_path):
    registry, knowledge_objects = make_services(tmp_path)
    package = register_package(registry, "ds-1")

    lineage = knowledge_objects.lineage(package.package_id)

    assert lineage["knowledge_object_registered"] is False
    assert lineage["known_gaps"]
