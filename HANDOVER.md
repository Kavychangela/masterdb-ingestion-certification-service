# Handover

## Owner Role

Data Integrity & Certification Engineer for MASTERDB ingestion readiness.

## What This Service Does

This service validates dataset packages and returns whether a dataset is eligible to enter MASTERDB. The output is deterministic and replayable through persisted JSON reports.

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

## Files To Know

- `main.py`: REST entrypoint only.
- `services/validation_service.py`: Validation orchestration.
- `services/certification_service.py`: State transition rules.
- `services/report_service.py`: Status and report lookup.
- `services/artifact_store.py`: File-based report persistence.
- `config/validation_rules.json`: Scoring and threshold rules.
- `config/schema.json`: Dataset schema expectations.

## Sample Artifacts

- `reports/sample-certified.json`
- `reports/sample-rejected.json`

## Extension Points

- Replace `ArtifactStore` with platform storage.
- Add upload endpoints while keeping `ValidationService` unchanged.
- Add new validators under `validators/` and include them in `ValidationService`.
- Adjust thresholds in `config/validation_rules.json`.

## Non-Goals

Do not add vector search, RAG, embeddings, registries, knowledge graphs, or UI logic to this service.

