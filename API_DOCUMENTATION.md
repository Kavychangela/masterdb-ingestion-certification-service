# API Documentation

Base URL for local development:

```text
http://127.0.0.1:8000
```

All endpoints return structured JSON only.

## POST /validate

Runs deterministic validation checks and stores a validation report.

Request:

```json
{
  "dataset_id": "sample-certified",
  "dataset_path": "datasets/certifiable_sample.csv",
  "metadata_path": "datasets/metadata.json"
}
```

Response:

```json
{
  "dataset_id": "sample-certified",
  "state": "VALIDATED",
  "report": {
    "dataset_id": "sample-certified",
    "state": "VALIDATED",
    "integrity_score": 100.0,
    "classification": "Trusted",
    "risk_flags": []
  }
}
```

## POST /certify

Runs certification against an existing report. If `dataset_id` is unknown, callers may include `dataset_path` and `metadata_path` to validate and certify in one call.

Request using an existing report:

```json
{
  "dataset_id": "sample-certified"
}
```

Request using a dataset package:

```json
{
  "dataset_id": "sample-certified",
  "dataset_path": "datasets/certifiable_sample.csv",
  "metadata_path": "datasets/metadata.json"
}
```

Response:

```json
{
  "dataset_id": "sample-certified",
  "state": "CERTIFIED",
  "decision": {
    "dataset_id": "sample-certified",
    "eligible_for_masterdb": true,
    "state": "CERTIFIED",
    "classification": "Trusted",
    "integrity_score": 100.0,
    "rejection_reasons": [],
    "audit_trail": []
  },
  "report": {}
}
```

## GET /status/{dataset_id}

Returns compact ingestion status for dashboards, registries, and orchestration services.

Response:

```json
{
  "dataset_id": "sample-certified",
  "state": "CERTIFIED",
  "classification": "Trusted",
  "integrity_score": 100.0,
  "eligible_for_masterdb": true
}
```

## GET /report/{dataset_id}

Returns the full persisted validation and certification artifact.

Response includes:

- Dataset profile
- Validation results
- Risk flags
- Integrity score
- Classification
- Recommendations
- Ingestion decision
- Audit trail

## Error Responses

Unknown dataset:

```json
{
  "detail": "No report found for dataset_id=unknown"
}
```

Invalid request or unreadable dataset package:

```json
{
  "detail": "error details"
}
```

---

# MASTERDB Registry API (Phase 4)

Knowledge Package Lifecycle, Provenance/Lineage, and Retrieval Readiness
endpoints. These are additive to the validation/certification endpoints
above and operate on `KnowledgePackage` records rather than raw dataset
reports.

## POST /packages/register

Registers a new `KnowledgePackage` in status `REGISTERED`.

Request:

```json
{
  "dataset_id": "sample-certified",
  "dataset_version": "1.0.0",
  "schema_version": "2",
  "board": "AI",
  "medium": "text",
  "language": "en",
  "owner": "kavy",
  "actor": "pipeline",
  "reason": "Initial package registration."
}
```

Response: the full `KnowledgePackage`, including `package_id` and a
one-entry `history` recording the `REGISTERED` transition.

## POST /packages/promote

Moves a package to the next lifecycle status. Rejects any edge not present
in the lifecycle graph (see `ARCHITECTURE.md`) with `400`.

Request:

```json
{
  "package_id": "pkg-...",
  "to_status": "INGESTED",
  "actor": "pipeline",
  "reason": "Ingestion pipeline completed."
}
```

Response: the updated `KnowledgePackage` with the new transition appended
to `history`.

## POST /packages/deprecate

Convenience endpoint that always transitions to `DEPRECATED`, valid from any
non-terminal, non-deprecated status.

Request:

```json
{
  "package_id": "pkg-...",
  "actor": "owner",
  "reason": "Superseded by a newer dataset version."
}
```

## GET /packages/{package_id}

Returns the current `KnowledgePackage` record, including its full `history`.

## GET /packages/{package_id}/history

Returns just the transition history:

```json
{
  "package_id": "pkg-...",
  "history": [
    {
      "transition_id": "txn-...",
      "from_status": null,
      "to_status": "REGISTERED",
      "reason": "Initial package registration.",
      "actor": "pipeline",
      "timestamp": "2026-07-06T00:00:00+00:00"
    }
  ]
}
```

## POST /packages/{package_id}/knowledge-object

Registers a `KnowledgeObject` (provenance/lineage pointer) for a package.
Not one of the seven endpoints named in the sprint spec, but required to
exercise `/lineage` and `/retrieval` meaningfully — it is the write side of
the Knowledge Object & Provenance Engine. `package_id` in the path and body
must match.

Request:

```json
{
  "package_id": "pkg-...",
  "parent_package": null,
  "source_reference": "s3://bucket/source.csv",
  "lineage_reference": null,
  "derivation_path": ["ingest", "clean"]
}
```

`400` if `parent_package` is set but does not exist, or if schema versions
are major-version incompatible with the declared parent.

## GET /packages/{package_id}/lineage

Returns ancestor chain and declared descendants for a package's Knowledge
Object, plus any `known_gaps` in the current MDU contract placeholder.

```json
{
  "package_id": "pkg-...",
  "knowledge_object_registered": true,
  "knowledge_object_id": "kobj-...",
  "knowledge_hash": "…",
  "source_reference": "s3://bucket/source.csv",
  "lineage_reference": null,
  "derivation_path": ["ingest", "clean"],
  "ancestors": [],
  "descendants": [],
  "known_gaps": ["source_reference: Placeholder: assumed to be a URI/path string..."]
}
```

## GET /packages/{package_id}/retrieval

Runs the Retrieval Readiness Engine and returns a `RetrievalEvidence`
artifact. Certification alone does not imply retrievability; see
`ARCHITECTURE.md` for the rule set.

```json
{
  "package_id": "pkg-...",
  "status": "PARTIALLY_RETRIEVABLE",
  "rules": [
    {"rule": "PACKAGE_CERTIFIED", "passed": true, "detail": "Package status is CERTIFIED."},
    {"rule": "NOT_DEPRECATED_OR_ARCHIVED", "passed": true, "detail": "Package is active."},
    {"rule": "METADATA_COMPLETE", "passed": true, "detail": "All required package metadata fields are present."},
    {"rule": "LINEAGE_REGISTERED", "passed": false, "detail": "No knowledge object with a source_reference is registered for this package."}
  ],
  "corrective_actions": [
    "Register a Knowledge Object with a source_reference for this package via the Knowledge Object & Provenance Engine."
  ],
  "generated_at": "2026-07-06T00:00:00+00:00"
}
```

## Registry Error Responses

Unknown package:

```json
{
  "detail": "No package found for package_id=unknown"
}
```

Illegal lifecycle transition:

```json
{
  "detail": "Cannot transition package pkg-... from REGISTERED to CERTIFIED. Allowed transitions from REGISTERED: ['INGESTED', 'DEPRECATED']."
}
```

