from __future__ import annotations

import pytest

from crisp.config.models import (
    EXECUTABLE_COMPARISON_TYPES,
    SUPPORTED_COMPARISON_TYPES,
    SUPPORTED_CONFIG_ROLES,
    SUPPORTED_PATH_MODELS,
    SUPPORTED_PATHWAYS,
    ComparisonType,
    normalize_comparison_type,
)


# ---------------------------------------------------------------------------
# Constant invariants
# ---------------------------------------------------------------------------


def test_supported_pathways_are_expected_set() -> None:
    assert SUPPORTED_PATHWAYS == {"covalent", "noncovalent"}


def test_supported_path_models_are_expected_set() -> None:
    assert SUPPORTED_PATH_MODELS == {"TUNNEL", "SURFACE_LIKE"}


def test_supported_config_roles_are_expected_set() -> None:
    assert SUPPORTED_CONFIG_ROLES == {"lowsampling", "benchmark", "smoke", "production"}


def test_supported_comparison_types_covers_all_enum_members() -> None:
    enum_values = {member.value for member in ComparisonType}
    assert SUPPORTED_COMPARISON_TYPES == enum_values


def test_executable_comparison_types_excludes_none() -> None:
    assert ComparisonType.NONE.value not in EXECUTABLE_COMPARISON_TYPES
    assert ComparisonType.SAME_CONFIG.value in EXECUTABLE_COMPARISON_TYPES
    assert ComparisonType.CROSS_REGIME.value in EXECUTABLE_COMPARISON_TYPES


# ---------------------------------------------------------------------------
# normalize_comparison_type
# ---------------------------------------------------------------------------


def test_normalize_comparison_type_accepts_string() -> None:
    result = normalize_comparison_type("same-config")

    assert result == ComparisonType.SAME_CONFIG


def test_normalize_comparison_type_accepts_enum_member() -> None:
    result = normalize_comparison_type(ComparisonType.CROSS_REGIME)

    assert result == ComparisonType.CROSS_REGIME
    assert isinstance(result, ComparisonType)


def test_normalize_comparison_type_accepts_none_string() -> None:
    result = normalize_comparison_type("none")

    assert result == ComparisonType.NONE


def test_normalize_comparison_type_raises_for_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unsupported comparison_type"):
        normalize_comparison_type("unsupported-type")
