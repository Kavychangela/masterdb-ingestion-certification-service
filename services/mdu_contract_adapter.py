"""
Adapter interface for the MDU (Nupur) canonical contracts.

MASTERDB does NOT own Knowledge Object, Provenance, Lineage, or schema
contract semantics. Those are owned by MDU. This adapter is the single seam
MASTERDB code depends on for MDU-owned data, in two modes:

  - LIVE mode: an MDUClient is configured (MDU_BASE_URL / MDU_API_KEY) and
    reachable. The adapter fetches real schema/provenance contracts from
    MDU and reports back what MDU actually said — it does not reinterpret
    or "improve" that data.
  - PLACEHOLDER mode: no live MDU connection. The adapter falls back to the
    documented placeholder snapshot below so the rest of MASTERDB keeps
    working, and every response is tagged so callers know it is not
    MDU-confirmed.

Do NOT add new semantics here. If a field or rule is not confirmed by MDU,
mark it as a placeholder and keep the check permissive (log/flag rather than
hard-fail), so MASTERDB never silently invents ontology it doesn't own.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.mdu_client import MDUClient, MDUUnavailableError


@dataclass
class MDUFieldRequirement:
    field_name: str
    required: bool
    confirmed_by_mdu: bool
    note: str = ""


@dataclass
class MDUContractSnapshot:
    """
    Placeholder snapshot of what MASTERDB currently believes about the MDU
    Knowledge Object contract, used only when live MDU is unreachable.
    """

    contract_version: str = "PLACEHOLDER-v0"
    required_fields: List[MDUFieldRequirement] = field(
        default_factory=lambda: [
            MDUFieldRequirement(
                "knowledge_object_id", True, confirmed_by_mdu=False,
                note="MASTERDB-generated identity; pending MDU confirmation "
                "of canonical ID format.",
            ),
            MDUFieldRequirement(
                "source_reference", True, confirmed_by_mdu=False,
                note="Placeholder: assumed to be a URI/path string until MDU "
                "publishes the canonical provenance schema.",
            ),
            MDUFieldRequirement(
                "lineage_reference", False, confirmed_by_mdu=False,
                note="Placeholder: optional pointer into MDU's lineage graph.",
            ),
            MDUFieldRequirement(
                "derivation_path", False, confirmed_by_mdu=False,
                note="Placeholder: ordered list of transformation steps; "
                "shape not yet ratified by MDU.",
            ),
        ]
    )


def _major_minor(version: str) -> tuple:
    """
    Best-effort semantic-version split. Never raises: a version string that
    doesn't parse cleanly degrades to (raw_string, "0") so negotiation can
    still report an explicit mismatch instead of crashing the caller.
    """
    parts = version.split(".")
    major = parts[0] if parts else version
    minor = parts[1] if len(parts) > 1 else "0"
    return major, minor


class MDUContractAdapter:
    """
    Consumption boundary for MDU-owned definitions.

    Callers must not assume placeholder-mode responses are authoritative —
    check `source` on returned dicts ("mdu-live" vs "placeholder") if that
    distinction matters to the caller.
    """

    def __init__(
        self,
        snapshot: Optional[MDUContractSnapshot] = None,
        client: Optional[MDUClient] = None,
    ) -> None:
        self.snapshot = snapshot or MDUContractSnapshot()
        self.client = client or MDUClient()

    # -- placeholder-mode surface (unchanged behavior) -----------------------

    def is_contract_finalized(self) -> bool:
        return all(f.confirmed_by_mdu for f in self.snapshot.required_fields)

    def required_field_names(self) -> List[str]:
        return [f.field_name for f in self.snapshot.required_fields if f.required]

    def known_gaps(self) -> List[str]:
        return [
            f"{f.field_name}: {f.note}"
            for f in self.snapshot.required_fields
            if not f.confirmed_by_mdu
        ]

    # -- Phase 1: live contract consumption -----------------------------------

    def is_live(self) -> bool:
        return self.client.is_configured()

    def fetch_schema_contract(self, dataset_id: str) -> Dict[str, Any]:
        """
        Fetch MDU's canonical schema for a dataset. Raises MDUUnavailableError
        if MDU is unconfigured/unreachable — callers decide whether that's
        fatal for their operation; this adapter never fabricates a schema.
        """
        return self.client.get_dataset_schema(dataset_id)

    def fetch_provenance_contract(self, dataset_id: str) -> Dict[str, Any]:
        """Fetch MDU's provenance/lineage chain for a dataset, verbatim."""
        return self.client.get_dataset_provenance(dataset_id)

    def fetch_canonical_dataset(self, dataset_id: str) -> Dict[str, Any]:
        return self.client.get_canonical_dataset(dataset_id)

    def validate_schema_compatibility(
        self, dataset_id: str, local_schema_version: str
    ) -> Dict[str, Any]:
        """
        Compare MASTERDB's locally-declared schema_version for a package
        against MDU's canonical schema for that dataset_id.

        Falls back to placeholder-mode (major-version-only, unconfirmed) if
        live MDU is unreachable, so package registration never hard-fails
        purely because MDU is down — it degrades to a flagged gap instead.
        """
        if not self.client.is_configured():
            return {
                "source": "placeholder",
                "compatible": True,
                "reason": "MDU not configured; falling back to permissive "
                "placeholder check (no hard-fail on unconfirmed contract).",
                "known_gaps": self.known_gaps(),
            }
        try:
            schema = self.client.get_dataset_schema(dataset_id)
        except MDUUnavailableError as exc:
            return {
                "source": "placeholder",
                "compatible": True,
                "reason": f"MDU unreachable ({exc}); falling back to permissive "
                "placeholder check.",
                "known_gaps": self.known_gaps(),
            }

        mdu_schema_version = str(
            schema.get("schema_version") or schema.get("version") or ""
        )
        negotiation = self.negotiate_version(local_schema_version, mdu_schema_version)
        return {
            "source": "mdu-live",
            "dataset_id": dataset_id,
            "mdu_schema_version": mdu_schema_version,
            "local_schema_version": local_schema_version,
            **negotiation,
        }

    @staticmethod
    def negotiate_version(local_version: str, remote_version: str) -> Dict[str, Any]:
        """
        Deterministic, MASTERDB-side version-negotiation rule:
          - equal strings              -> compatible, exact match
          - equal major, differing minor -> compatible, with a warning
          - differing major             -> incompatible

        This rule is MASTERDB's own negotiation policy (how MASTERDB decides
        whether to proceed), not a claim about what MDU's versioning scheme
        means semantically — that meaning stays MDU's to define.
        """
        if not remote_version:
            return {
                "compatible": False,
                "negotiation": "unknown",
                "reason": "MDU did not report a schema_version for this dataset.",
            }
        if local_version == remote_version:
            return {"compatible": True, "negotiation": "exact_match", "reason": ""}

        local_major, _ = _major_minor(local_version)
        remote_major, _ = _major_minor(remote_version)
        if local_major == remote_major:
            return {
                "compatible": True,
                "negotiation": "minor_version_drift",
                "reason": f"Major version {local_major} matches; minor versions "
                f"differ ({local_version} vs {remote_version}).",
            }
        return {
            "compatible": False,
            "negotiation": "major_version_mismatch",
            "reason": f"Major version mismatch: local={local_version} "
            f"mdu={remote_version}.",
        }
