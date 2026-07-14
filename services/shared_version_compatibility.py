"""
Phase 4 — generic version-compatibility check reused across shared
services (Task 4).

Mirrors MDUContractAdapter.negotiate_version's policy (services/
mdu_contract_adapter.py) but is kept as its own standalone utility so the
shared-platform code has no import dependency on the MDU-specific adapter.
Both implement the same MASTERDB-side negotiation rule; if that rule ever
changes, update both call sites deliberately rather than silently
re-coupling them.
"""
from typing import Any, Dict, Tuple


def _major_minor(version: str) -> Tuple[str, str]:
    parts = version.split(".")
    major = parts[0] if parts else version
    minor = parts[1] if len(parts) > 1 else "0"
    return major, minor


def negotiate_version(local_version: str, remote_version: str) -> Dict[str, Any]:
    """
    Deterministic version-negotiation rule:
      - equal strings                -> compatible, exact match
      - equal major, differing minor -> compatible, with a warning
      - differing major               -> incompatible
      - no remote version supplied    -> unknown / incompatible
    """
    if not remote_version:
        return {
            "compatible": False,
            "negotiation": "unknown",
            "reason": "No remote version supplied.",
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
        "reason": f"Major version mismatch: local={local_version} remote={remote_version}.",
    }
