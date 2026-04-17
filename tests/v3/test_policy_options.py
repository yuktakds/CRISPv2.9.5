from __future__ import annotations

import pytest

from crisp.v3.policy import (
    DEFAULT_BRIDGE_COMPARATOR_OPTIONS,
    DEFAULT_SIDECAR_OPTIONS,
    expected_output_digest_payload,
    parse_bridge_comparator_options,
    parse_sidecar_options,
)


# ---------------------------------------------------------------------------
# parse_bridge_comparator_options
# ---------------------------------------------------------------------------


def test_parse_bridge_comparator_options_absent_key_returns_default() -> None:
    result = parse_bridge_comparator_options({})

    assert result == DEFAULT_BRIDGE_COMPARATOR_OPTIONS
    assert result.enabled is False


def test_parse_bridge_comparator_options_bool_true_enables() -> None:
    result = parse_bridge_comparator_options({"v3_bridge_comparator": True})

    assert result.enabled is True


def test_parse_bridge_comparator_options_bool_false_disables() -> None:
    result = parse_bridge_comparator_options({"v3_bridge_comparator": False})

    assert result.enabled is False


def test_parse_bridge_comparator_options_dict_with_enabled_true() -> None:
    result = parse_bridge_comparator_options(
        {"v3_bridge_comparator": {"enabled": True}}
    )

    assert result.enabled is True


def test_parse_bridge_comparator_options_dict_with_enabled_false() -> None:
    result = parse_bridge_comparator_options(
        {"v3_bridge_comparator": {"enabled": False}}
    )

    assert result.enabled is False


def test_parse_bridge_comparator_options_raises_for_non_mapping_non_bool() -> None:
    with pytest.raises(TypeError, match="must be a mapping or bool"):
        parse_bridge_comparator_options({"v3_bridge_comparator": "yes"})


def test_parse_bridge_comparator_options_raises_for_non_bool_enabled() -> None:
    with pytest.raises(TypeError, match="enabled must be a boolean"):
        parse_bridge_comparator_options(
            {"v3_bridge_comparator": {"enabled": "true"}}
        )


# ---------------------------------------------------------------------------
# parse_sidecar_options — default path (no v3_sidecar key)
# ---------------------------------------------------------------------------


def test_parse_sidecar_options_absent_key_returns_default() -> None:
    result = parse_sidecar_options({})

    assert result == DEFAULT_SIDECAR_OPTIONS


# ---------------------------------------------------------------------------
# expected_output_digest_payload
# ---------------------------------------------------------------------------


def test_expected_output_digest_payload_returns_sha256_prefixed_string() -> None:
    result = expected_output_digest_payload([{"path": "output.json"}])

    assert isinstance(result, str)
    assert result.startswith("sha256:")


def test_expected_output_digest_payload_is_deterministic() -> None:
    outputs = [{"path": "a.json"}, {"path": "b.json"}]
    assert expected_output_digest_payload(outputs) == expected_output_digest_payload(outputs)


def test_expected_output_digest_payload_differs_for_different_outputs() -> None:
    d1 = expected_output_digest_payload([{"path": "a.json"}])
    d2 = expected_output_digest_payload([{"path": "b.json"}])

    assert d1 != d2


def test_expected_output_digest_payload_empty_list_is_stable() -> None:
    result = expected_output_digest_payload([])

    assert result.startswith("sha256:")
