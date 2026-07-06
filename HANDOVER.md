# Handover

## Owner Role

MASTERDB Core Knowledge Platform Engineer — ingestion readiness, Knowledge
Package Lifecycle, Provenance/Lineage consumption, and Retrieval Readiness
for the BHIV ecosystem.

## What This Service Does

This service validates dataset packages, certifies ingestion eligibility,
and now also owns the Knowledge Package Lifecycle (Dataset Registry),
Knowledge Object/Provenance consumption, and Retrieval Readiness/Evidence
that make MASTERDB a knowledge platform rather than only a validation
boundary. All output is deterministic and replayable through persisted
JSON records — validation/certification reports, package lifecycle
history, knowledge object/lineage records, and retrieval evidence.

## How To Run

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the API:

```bash
uvicorn main:app --reload
```

Run tests:

```bash
python -m pytest
```

## Integration Contract

Future ingestion pipelines should call:

1. `POST /validate`
2. `POST /certify`
3. `GET /status/{dataset_id}` or `GET /report/{dataset_id}`

The only accepted ingestion decision is:

```json
{
  "eligible_for_masterdb": true,
  "state": "CERTIFIED"
}
```

Any other state must be treated as not eligible for MASTERDB ingestion.

Once a dataset is certified, register it as a `KnowledgePackage` and drive it
through the lifecycle:

1. `POST /packages/register`
2. `POST /packages/promote` (repeat through `INGESTED -> VALIDATED ->
   VERIFIED -> CERTIFIED -> RETRIEVAL_READY`)
3. `POST /packages/{package_id}/knowledge-object` to attach lineage
4. `GET /packages/{package_id}/lineage` and
   `GET /packages/{package_id}/retrieval` to check readiness before any
   downstream system treats the package as retrievable

Only `CERTIFIED_RETRIEVABLE` (or `RETRIEVABLE`, with awareness that lineage
metadata is present but the package hasn't been marked `RETRIEVAL_READY`
yet) should be treated as safe to retrieve from. `NOT_RETRIEVABLE` and
`PARTIALLY_RETRIEVABLE` must not be surfaced to retrieval consumers.

## Files To Know

- `main.py`: REST entrypoint only.
- `services/validation_service.py`: Validation orchestration.
- `services/certification_service.py`: State transition rules.
- `services/report_service.py`: Status and report lookup.
- `services/artifact_store.py`: File-based report persistence.
- `services/package_registry_service.py`: Dataset Registry / Knowledge
  Package Lifecycle Manager. Owns `PACKAGE_LIFECYCLE_GRAPH`, transition
  validation, history, and replay.
- `services/knowledge_object_service.py`: Knowledge Object & Provenance
  Engine. Consumes MDU semantics through `MDUContractAdapter`; validates
  parent/child relationships and major-version schema compatibility.
- `services/mdu_contract_adapter.py`: Placeholder consumption boundary for
  MDU's not-yet-finalized contract. Update this file, not the service
  logic, once MDU publishes the real contract.
- `services/retrieval_readiness_service.py`: Retrieval Readiness & Evidence
  Service. Produces replayable `RetrievalEvidence`.
- `config/validation_rules.json`: Scoring and threshold rules.
- `config/schema.json`: Dataset schema expectations.
- `MDU_INTERFACE_CONTRACT.md`: Consumed contracts, required fields, version
  compatibility rules, known gaps, and future extension points for the
  MASTERDB <-> MDU integration.

## Sample Artifacts

- `reports/sample-certified.json`
- `reports/sample-rejected.json`
- `registry_store/`, `knowledge_object_store/`, `retrieval_evidence_store/`
  are created on first use and hold package, lineage, and retrieval
  evidence records respectively (git-ignored sample data is not checked in;
  run the test suite or the example `curl` calls in `README.md` to
  populate them locally).

## Extension Points

- Replace `ArtifactStore` with platform storage (applies to all four
  stores: reports, registry, knowledge objects, retrieval evidence).
- Add upload endpoints while keeping `ValidationService` unchanged.
- Add new validators under `validators/` and include them in `ValidationService`.
- Adjust thresholds in `config/validation_rules.json`.
- Once MDU finalizes its contract, update `MDUContractAdapter` and
  `MDU_INTERFACE_CONTRACT.md` together; `KnowledgeObjectService` should not
  need structural changes if the adapter seam is respected.
- Runtime Discovery (service/tool discovery for downstream consumers) is
  named in MASTERDB's responsibilities but not yet implemented as an
  endpoint; `GET /packages/{package_id}` and `/retrieval` currently serve
  that purpose informally. Flagged as a Known Gap in
  `MDU_INTERFACE_CONTRACT.md`.

## Non-Goals

Do not add vector search, RAG, embeddings, runtime reasoning, canonical
schema/ontology definitions, or UI logic to this service. Registry and
Knowledge Package Lifecycle are now in-scope (this sprint); do not
duplicate MDU's ownership of Knowledge Object/Provenance/Lineage
*semantics* — MASTERDB only consumes them through the adapter boundary.

