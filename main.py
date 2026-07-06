from fastapi import FastAPI, HTTPException
from models import (
    CertificationRequest,
    KnowledgeObjectRegisterRequest,
    PackageDeprecateRequest,
    PackagePromoteRequest,
    PackageRegisterRequest,
    ValidationRequest,
)
from services.artifact_store import ArtifactStore
from services.certification_service import CertificationService
from services.knowledge_object_service import (
    KnowledgeObjectService,
    LineageValidationError,
    VersionIncompatibleError,
)
from services.package_registry_service import (
    InvalidTransitionError,
    PackageNotFoundError,
    PackageRegistryService,
)
from services.report_service import ReportService
from services.retrieval_readiness_service import RetrievalReadinessService
from services.validation_service import ValidationService



app = FastAPI(
    title="MASTERDB Core Knowledge Platform",
    version="1.1.0",
)

artifact_store = ArtifactStore()
validation_service = ValidationService(artifact_store=artifact_store)
certification_service = CertificationService(
    validation_service=validation_service,
    artifact_store=artifact_store,
)
report_service = ReportService(artifact_store=artifact_store)

# --- MASTERDB knowledge platform runtime (Knowledge Package Lifecycle,
# Provenance/Lineage, Retrieval Readiness) ---------------------------------
package_registry_service = PackageRegistryService()
knowledge_object_service = KnowledgeObjectService(registry=package_registry_service)
retrieval_readiness_service = RetrievalReadinessService(
    registry=package_registry_service,
    knowledge_object_service=knowledge_object_service,
)


@app.post("/validate")
def validate_dataset(request: ValidationRequest) -> dict:
    try:
        report = validation_service.validate(
            dataset_path=request.dataset_path,
            metadata_path=request.metadata_path,
            dataset_id=request.dataset_id,
        )
        return {
            "dataset_id": report["dataset_id"],
            "state": report["state"],
            "report": report,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/certify")
def certify_dataset(request: CertificationRequest) -> dict:
    try:
        report = certification_service.certify(
            dataset_id=request.dataset_id,
            dataset_path=request.dataset_path,
            metadata_path=request.metadata_path,
        )
        return {
            "dataset_id": report["dataset_id"],
            "state": report["state"],
            "decision": report["ingestion_decision"],
            "report": report,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/status/{dataset_id}")
def get_status(dataset_id: str) -> dict:
    try:
        return report_service.get_status(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/report/{dataset_id}")
def get_report(dataset_id: str) -> dict:
    try:
        return report_service.get_report(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase 4 — MASTERDB Registry API
# ---------------------------------------------------------------------------


@app.post("/packages/register")
def register_package(request: PackageRegisterRequest) -> dict:
    package = package_registry_service.register(
        dataset_id=request.dataset_id,
        dataset_version=request.dataset_version,
        schema_version=request.schema_version,
        board=request.board,
        medium=request.medium,
        language=request.language,
        owner=request.owner,
        actor=request.actor,
        reason=request.reason,
    )
    return package.model_dump(mode="json")


@app.post("/packages/promote")
def promote_package(request: PackagePromoteRequest) -> dict:
    try:
        package = package_registry_service.promote(
            package_id=request.package_id,
            to_status=request.to_status,
            actor=request.actor,
            reason=request.reason,
        )
        return package.model_dump(mode="json")
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/packages/deprecate")
def deprecate_package(request: PackageDeprecateRequest) -> dict:
    try:
        package = package_registry_service.deprecate(
            package_id=request.package_id,
            actor=request.actor,
            reason=request.reason,
        )
        return package.model_dump(mode="json")
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/packages/{package_id}")
def get_package(package_id: str) -> dict:
    try:
        return package_registry_service.get(package_id).model_dump(mode="json")
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/packages/{package_id}/history")
def get_package_history(package_id: str) -> dict:
    try:
        history = package_registry_service.history(package_id)
        return {
            "package_id": package_id,
            "history": [record.model_dump(mode="json") for record in history],
        }
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/packages/{package_id}/knowledge-object")
def register_knowledge_object(package_id: str, request: KnowledgeObjectRegisterRequest) -> dict:
    if request.package_id != package_id:
        raise HTTPException(
            status_code=400,
            detail="package_id in the path and request body must match.",
        )
    try:
        knowledge_object = knowledge_object_service.register_object(
            package_id=request.package_id,
            parent_package=request.parent_package,
            source_reference=request.source_reference,
            lineage_reference=request.lineage_reference,
            derivation_path=request.derivation_path,
        )
        return knowledge_object.model_dump(mode="json")
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (VersionIncompatibleError, LineageValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/packages/{package_id}/lineage")
def get_package_lineage(package_id: str) -> dict:
    try:
        package_registry_service.get(package_id)  # confirms the package exists
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return knowledge_object_service.lineage(package_id)


@app.get("/packages/{package_id}/retrieval")
def get_package_retrieval(package_id: str) -> dict:
    try:
        evidence = retrieval_readiness_service.assess(package_id)
        return evidence.model_dump(mode="json")
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

