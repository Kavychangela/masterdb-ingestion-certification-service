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

