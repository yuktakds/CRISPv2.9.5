from __future__ import annotations

from crisp.v3.contracts.bridge_header import BridgeHeader


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _header(**overrides: object) -> BridgeHeader:
    defaults: dict = {
        "semantic_policy_version": "v3.path_only_partial/v1",
        "comparator_scope": "path_only_partial",
        "verdict_comparability": "not_comparable",
        "comparable_channels": ("path",),
    }
    defaults.update(overrides)
    return BridgeHeader(**defaults)


# ---------------------------------------------------------------------------
# construction and defaults
# ---------------------------------------------------------------------------


def test_bridge_header_rc2_policy_version_defaults_to_none() -> None:
    header = _header()

    assert header.rc2_policy_version is None


def test_bridge_header_rc2_policy_version_can_be_set() -> None:
    header = _header(rc2_policy_version="v2.9.5-rc2")

    assert header.rc2_policy_version == "v2.9.5-rc2"


def test_bridge_header_stores_comparable_channels_tuple() -> None:
    header = _header(comparable_channels=("path", "cap"))

    assert header.comparable_channels == ("path", "cap")


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


def test_to_dict_returns_all_required_keys() -> None:
    result = _header().to_dict()

    expected_keys = {
        "semantic_policy_version",
        "comparator_scope",
        "verdict_comparability",
        "comparable_channels",
        "rc2_policy_version",
    }
    assert expected_keys <= set(result.keys())


def test_to_dict_comparable_channels_preserved() -> None:
    header = _header(comparable_channels=("path", "cap"))
    result = header.to_dict()

    assert result["comparable_channels"] == ("path", "cap")


def test_to_dict_preserves_semantic_policy_version() -> None:
    header = _header(semantic_policy_version="v3.path_only_partial/v1")
    result = header.to_dict()

    assert result["semantic_policy_version"] == "v3.path_only_partial/v1"


def test_to_dict_preserves_comparator_scope() -> None:
    header = _header(comparator_scope="full_channel_bundle")
    result = header.to_dict()

    assert result["comparator_scope"] == "full_channel_bundle"


def test_to_dict_preserves_verdict_comparability() -> None:
    header = _header(verdict_comparability="fully_comparable")
    result = header.to_dict()

    assert result["verdict_comparability"] == "fully_comparable"


def test_to_dict_rc2_policy_version_none_included() -> None:
    result = _header(rc2_policy_version=None).to_dict()

    assert "rc2_policy_version" in result
    assert result["rc2_policy_version"] is None


def test_to_dict_rc2_policy_version_string_preserved() -> None:
    result = _header(rc2_policy_version="v2.9.5-rc2").to_dict()

    assert result["rc2_policy_version"] == "v2.9.5-rc2"


def test_to_dict_returns_plain_dict() -> None:
    assert isinstance(_header().to_dict(), dict)
