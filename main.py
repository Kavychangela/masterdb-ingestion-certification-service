import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv


load_dotenv()
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from models import (
    CertificationRequest,
    KnowledgeObjectRegisterRequest,
    PackageDeprecateRequest,
    PackagePromoteRequest,
    PackageRegisterRequest,
    PackageStatus,
    ValidationRequest,
)
from services.artifact_store import ArtifactStore
from services.certification_service import CertificationService
from services.knowledge_object_service import (
    KnowledgeObjectService,
    LineageValidationError,
    VersionIncompatibleError,
)
from services.mdu_client import MDUUnavailableError
from services.mdu_contract_adapter import MDUContractAdapter
from services.package_registry_service import (
    InvalidTransitionError,
    PackageNotFoundError,
    PackageRegistryService,
)
from services.report_service import ReportService
from services.retrieval_readiness_service import RetrievalReadinessService
from services.runtime_discovery_service import RuntimeDiscoveryService
from services.tantra_interface_service import (
    CertificationStatusNotFoundError,
    TantraInterfaceService,
)
from services.validation_service import ValidationService



app = FastAPI(
    title="MASTERDB Core Knowledge Platform",
    version="1.2.0",
)

logger = logging.getLogger("masterdb")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s masterdb: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Phase 4 — Uniform error contract
#
# Every error response (validation failure, missing entity, invalid
# transition, upstream MDU failure, or unhandled exception) is shaped the
# same way so downstream consumers (TANTRA included) can parse errors
# generically instead of branching on endpoint-specific bodies.
#   { "error": { "type": str, "message": str, "path": str } }
# ---------------------------------------------------------------------------


def _error_body(request: Request, error_type: str, message: str) -> Dict[str, Any]:
    return {"error": {"type": error_type, "message": message, "path": request.url.path}}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning("HTTPException %s at %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(request, "http_error", str(exc.detail)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=_error_body(request, "internal_error", "An unexpected error occurred."),
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

# --- Ecosystem integration surfaces: MDU (Nupur), TANTRA, Runtime Discovery --
mdu_contract_adapter = MDUContractAdapter()
runtime_discovery_service = RuntimeDiscoveryService(registry=package_registry_service)
tantra_interface_service = TantraInterfaceService(
    registry=package_registry_service,
    knowledge_object_service=knowledge_object_service,
    retrieval_readiness_service=retrieval_readiness_service,
    report_service=report_service,
    discovery_service=runtime_discovery_service,
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


@app.get("/packages/{package_id}/replay")
def replay_package(package_id: str) -> dict:
    """Phase 4 — replay consistency: recompute status purely from history."""
    try:
        replayed_status = package_registry_service.replay(package_id)
        return {
            "package_id": package_id,
            "replay_consistent": True,
            "replayed_status": replayed_status.value,
        }
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        return {
            "package_id": package_id,
            "replay_consistent": False,
            "replay_error": str(exc),
        }


@app.get("/packages/{package_id}/audit")
def audit_package(package_id: str) -> dict:
    """Phase 4 — audit completeness report for a package's transition history."""
    try:
        return package_registry_service.audit_completeness(package_id)
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


# ---------------------------------------------------------------------------
# Phase 1 — Live MDU Integration
#
# MASTERDB does not own schema/provenance/lineage semantics; these endpoints
# expose what MDU reports, plus MASTERDB's own version-negotiation decision
# on top of it. If MDU is unconfigured/unreachable, responses degrade to a
# flagged placeholder rather than failing the caller outright.
# ---------------------------------------------------------------------------


@app.get("/mdu/status")
def mdu_status() -> dict:
    return {
        "live": mdu_contract_adapter.is_live(),
        "contract_finalized": mdu_contract_adapter.is_contract_finalized(),
        "known_gaps": mdu_contract_adapter.known_gaps(),
    }


@app.get("/mdu/schema/{dataset_id}")
def mdu_schema(dataset_id: str) -> dict:
    try:
        return mdu_contract_adapter.fetch_schema_contract(dataset_id)
    except MDUUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/mdu/provenance/{dataset_id}")
def mdu_provenance(dataset_id: str) -> dict:
    try:
        return mdu_contract_adapter.fetch_provenance_contract(dataset_id)
    except MDUUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/mdu/schema-compatibility/{dataset_id}")
def mdu_schema_compatibility(dataset_id: str, local_schema_version: str) -> dict:
    return mdu_contract_adapter.validate_schema_compatibility(
        dataset_id=dataset_id, local_schema_version=local_schema_version
    )


# ---------------------------------------------------------------------------
# Phase 2 — MASTERDB <-> TANTRA Runtime Interface
# ---------------------------------------------------------------------------


@app.post("/tantra/datasets/register")
def tantra_register_dataset(request: PackageRegisterRequest) -> dict:
    package = tantra_interface_service.register_dataset(
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


@app.get("/tantra/packages/{package_id}/retrieval-readiness")
def tantra_retrieval_readiness(package_id: str) -> dict:
    try:
        return tantra_interface_service.retrieval_readiness(package_id)
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tantra/certification/{dataset_id}")
def tantra_certification_status(dataset_id: str) -> dict:
    try:
        return tantra_interface_service.certification_status(dataset_id)
    except CertificationStatusNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tantra/packages/{package_id}/runtime")
def tantra_runtime_package_lookup(package_id: str) -> dict:
    try:
        return tantra_interface_service.runtime_package_lookup(package_id)
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase 3 — Runtime Discovery API
#
# Shared by TANTRA and any other downstream consumer. Deterministic filtered
# lookup only — no ranking, no relevance scoring.
# ---------------------------------------------------------------------------


@app.get("/discovery/packages")
def discover_packages(
    package_id: Optional[str] = Query(default=None),
    dataset_id: Optional[str] = Query(default=None),
    board: Optional[str] = Query(default=None),
    medium: Optional[str] = Query(default=None),
    version: Optional[str] = Query(default=None),
    status: Optional[PackageStatus] = Query(default=None),
) -> dict:
    results = runtime_discovery_service.discover_as_dicts(
        package_id=package_id,
        dataset_id=dataset_id,
        board=board,
        medium=medium,
        version=version,
        status=status,
    )
    return {"count": len(results), "packages": results}

