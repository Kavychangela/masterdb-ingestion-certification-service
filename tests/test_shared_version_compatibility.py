from services.shared_version_compatibility import negotiate_version


def test_exact_match_is_compatible():
    result = negotiate_version("1.2", "1.2")
    assert result["compatible"] is True
    assert result["negotiation"] == "exact_match"


def test_minor_drift_is_compatible_with_warning():
    result = negotiate_version("1.2", "1.5")
    assert result["compatible"] is True
    assert result["negotiation"] == "minor_version_drift"
    assert "1" in result["reason"]


def test_major_mismatch_is_incompatible():
    result = negotiate_version("1.2", "2.0")
    assert result["compatible"] is False
    assert result["negotiation"] == "major_version_mismatch"


def test_missing_remote_version_is_unknown():
    result = negotiate_version("1.0", "")
    assert result["compatible"] is False
    assert result["negotiation"] == "unknown"
