from __future__ import annotations

from crisp.v3.current_public_scope import (
    CATALYTIC_PUBLIC_COMPARABLE_COMPONENT,
    CURRENT_PUBLIC_COMPARABLE_CHANNELS,
    CURRENT_PUBLIC_COMPARABLE_COMPONENTS,
    CURRENT_PUBLIC_COMPARATOR_SCOPE,
    CURRENT_PUBLIC_V3_ONLY_CHANNELS,
    derive_v3_only_evidence_channels,
)
from crisp.v3.policy import CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME, PATH_CHANNEL_NAME


# ---------------------------------------------------------------------------
# Boundary constants — these are frozen for v0.1.0
# ---------------------------------------------------------------------------


def test_comparator_scope_is_path_and_catalytic_partial() -> None:
    assert CURRENT_PUBLIC_COMPARATOR_SCOPE == "path_and_catalytic_partial"


def test_comparable_channels_are_path_and_catalytic() -> None:
    assert set(CURRENT_PUBLIC_COMPARABLE_CHANNELS) == {PATH_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME}


def test_comparable_components_include_path_and_catalytic_rule3a() -> None:
    assert PATH_CHANNEL_NAME in CURRENT_PUBLIC_COMPARABLE_COMPONENTS
    assert "catalytic_rule3a" in CURRENT_PUBLIC_COMPARABLE_COMPONENTS


def test_catalytic_public_comparable_component_is_rule3a() -> None:
    assert CATALYTIC_PUBLIC_COMPARABLE_COMPONENT == "catalytic_rule3a"


def test_v3_only_channels_contains_cap() -> None:
    assert CAP_CHANNEL_NAME in CURRENT_PUBLIC_V3_ONLY_CHANNELS


def test_v3_only_channels_does_not_contain_path_or_catalytic() -> None:
    assert PATH_CHANNEL_NAME not in CURRENT_PUBLIC_V3_ONLY_CHANNELS
    assert CATALYTIC_CHANNEL_NAME not in CURRENT_PUBLIC_V3_ONLY_CHANNELS


# ---------------------------------------------------------------------------
# derive_v3_only_evidence_channels
# ---------------------------------------------------------------------------


def test_derive_returns_cap_when_observation_materialized() -> None:
    result = derive_v3_only_evidence_channels(
        {CAP_CHANNEL_NAME: "observation_materialized"}
    )

    assert CAP_CHANNEL_NAME in result


def test_derive_returns_empty_when_cap_not_materialized() -> None:
    result = derive_v3_only_evidence_channels(
        {CAP_CHANNEL_NAME: "pending"}
    )

    assert result == ()


def test_derive_returns_empty_for_empty_lifecycle_states() -> None:
    result = derive_v3_only_evidence_channels({})

    assert result == ()


def test_derive_ignores_path_and_catalytic_even_if_materialized() -> None:
    result = derive_v3_only_evidence_channels(
        {
            PATH_CHANNEL_NAME: "observation_materialized",
            CATALYTIC_CHANNEL_NAME: "observation_materialized",
        }
    )

    assert result == ()


def test_derive_caps_to_v3_only_channels_only() -> None:
    result = derive_v3_only_evidence_channels(
        {
            CAP_CHANNEL_NAME: "observation_materialized",
            PATH_CHANNEL_NAME: "observation_materialized",
        }
    )

    assert set(result) == {CAP_CHANNEL_NAME}
