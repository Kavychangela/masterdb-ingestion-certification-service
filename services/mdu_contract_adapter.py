"""
Adapter interface for the MDU (Nupur) canonical contracts.

MASTERDB does NOT own Knowledge Object, Provenance, Lineage, or schema
contract semantics. Those are owned by MDU. Until MDU publishes a finalized
"MASTERDB <-> MDU Interface Contract v1", this adapter exists as an explicit
placeholder boundary: it documents exactly what MASTERDB currently assumes,
so that swapping in the real MDU contract later is a localized change to
this one file instead of a rewrite of KnowledgeObjectService.

Do NOT add new semantics here. If a field or rule is not confirmed by MDU,
mark it as a placeholder and keep the check permissive (log/flag rather than
hard-fail), so MASTERDB never silently invents ontology it doesn't own.
"""
from dataclasses import dataclass, field
from typing import List, Optional


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
    Knowledge Object contract, pending Phase 5 convergence with Nupur.
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


class MDUContractAdapter:
    """
    Consumption boundary for MDU-owned definitions.

    Every method here is a placeholder until Nupur's contract is finalized
    (Phase 5). Callers must not assume these are authoritative — they exist
    so MASTERDB code depends on *one* seam, not scattered hardcoded rules.
    """

    def __init__(self, snapshot: Optional[MDUContractSnapshot] = None) -> None:
        self.snapshot = snapshot or MDUContractSnapshot()

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
