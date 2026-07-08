"""
One-off diagnostic: confirm MDU's live response field shapes against the
placeholder assumptions in services/mdu_contract_adapter.py.

This does NOT change any adapter behavior. It only reports what MDU
actually returns, side by side with what MASTERDB currently assumes, so
you can update MDUFieldRequirement(confirmed_by_mdu=...) entries with
real information instead of guesses.

Usage:
    python scripts/confirm_mdu_contract.py <dataset_id> [<dataset_id> ...]

Requires MDU_BASE_URL and MDU_API_KEY to be set (via .env or environment).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from services.mdu_client import MDUClient, MDUUnavailableError  # noqa: E402
from services.mdu_contract_adapter import MDUContractSnapshot  # noqa: E402


def flatten_keys(obj, prefix=""):
    """Return a sorted list of dotted key paths present in a JSON-like object."""
    keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            keys.append(path)
            keys.extend(flatten_keys(v, path))
    elif isinstance(obj, list) and obj:
        keys.extend(flatten_keys(obj[0], f"{prefix}[0]"))
    return keys


def report_for_endpoint(label, fetch_fn, dataset_id, assumed_fields):
    print(f"\n--- {label} (dataset_id={dataset_id}) ---")
    try:
        data = fetch_fn(dataset_id)
    except MDUUnavailableError as exc:
        print(f"  UNREACHABLE: {exc}")
        return

    print("  Raw response:")
    print(json.dumps(data, indent=2)[:2000])

    actual_keys = set(flatten_keys(data))
    print(f"\n  Fields MDU actually returned: {sorted(actual_keys) or '(none / empty)'}")

    missing = [f for f in assumed_fields if f not in actual_keys]
    extra = sorted(actual_keys - set(assumed_fields))

    if missing:
        print(f"  ASSUMED but NOT present in live response: {missing}")
    if extra:
        print(f"  PRESENT in live response but NOT in current assumptions: {extra}")
    if not missing and not extra:
        print("  Field names match current assumptions exactly.")


def main():
    dataset_ids = sys.argv[1:] or ["BHIV-DS-MARITIME-AIS-LIVE-001"]

    client = MDUClient()
    if not client.is_configured():
        print("MDU_BASE_URL / MDU_API_KEY not set. Set them in .env and re-run.")
        sys.exit(1)

    snapshot = MDUContractSnapshot()
    assumed_field_names = [f.field_name for f in snapshot.required_fields]

    print(f"MDU base URL: {client.base_url}")
    print(f"Currently assumed knowledge-object fields: {assumed_field_names}")
    print("(Each is marked confirmed_by_mdu=False until verified here.)")

    for dataset_id in dataset_ids:
        report_for_endpoint(
            "GET /api/v1/schemas/dataset/{id}",
            client.get_dataset_schema,
            dataset_id,
            ["schema_version", "version"],
        )
        report_for_endpoint(
            "GET /api/v1/datasets/{id}/provenance",
            client.get_dataset_provenance,
            dataset_id,
            assumed_field_names,
        )
        report_for_endpoint(
            "GET /api/v1/datasets/canonical/{id}",
            client.get_canonical_dataset,
            dataset_id,
            assumed_field_names,
        )

    print("\n--- GET /api/v1/discovery/summary ---")
    try:
        summary = client.get_discovery_summary()
        print(json.dumps(summary, indent=2)[:2000])
    except MDUUnavailableError as exc:
        print(f"  UNREACHABLE: {exc}")

    print(
        "\nNext step: for every field confirmed present/shaped as expected above, "
        "update the matching MDUFieldRequirement(confirmed_by_mdu=...) in "
        "services/mdu_contract_adapter.py from False to True, and add a short "
        "note pointing at this script's output as evidence."
    )


if __name__ == "__main__":
    main()