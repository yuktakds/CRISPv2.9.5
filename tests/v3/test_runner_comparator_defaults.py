from __future__ import annotations

from crisp.v3.policy import CAP_CHANNEL_NAME, CATALYTIC_CHANNEL_NAME, PATH_CHANNEL_NAME
from crisp.v3.rp3_activation import ActivationUnit
from crisp.v3.runner_comparator import (
    ComparatorExecutionState,
    _default_activation_decisions,
    empty_comparator_execution,
)


# ---------------------------------------------------------------------------
# empty_comparator_execution — default field values
# ---------------------------------------------------------------------------


def test_empty_comparator_execution_returns_comparator_execution_state() -> None:
    state = empty_comparator_execution()

    assert isinstance(state, ComparatorExecutionState)


def test_empty_comparator_execution_comparison_summary_is_none() -> None:
    state = empty_comparator_execution()

    assert state.comparison_summary_payload is None


def test_empty_comparator_execution_run_drift_report_is_none() -> None:
    state = empty_comparator_execution()

    assert state.run_drift_report_payload is None


def test_empty_comparator_execution_activation_decisions_is_empty() -> None:
    state = empty_comparator_execution()

    assert state.activation_decisions == {}


def test_empty_comparator_execution_vn_gates_is_empty() -> None:
    state = empty_comparator_execution()

    assert state.vn_gates == {}


def test_empty_comparator_execution_denominator_contract_satisfied_is_false() -> None:
    state = empty_comparator_execution()

    assert state.denominator_contract_satisfied is False


def test_empty_comparator_execution_required_candidacy_payload_is_none() -> None:
    state = empty_comparator_execution()

    assert state.required_candidacy_payload is None


def test_empty_comparator_execution_channel_comparability_has_all_three_channels() -> None:
    state = empty_comparator_execution()

    assert set(state.channel_comparability.keys()) == {
        PATH_CHANNEL_NAME,
        CAP_CHANNEL_NAME,
        CATALYTIC_CHANNEL_NAME,
    }


def test_empty_comparator_execution_channel_comparability_all_none() -> None:
    state = empty_comparator_execution()

    assert all(v is None for v in state.channel_comparability.values())


def test_empty_comparator_execution_path_component_match_is_none() -> None:
    state = empty_comparator_execution()

    assert state.path_component_match is None


def test_empty_comparator_execution_comparable_channels_is_empty() -> None:
    state = empty_comparator_execution()

    assert state.comparable_channels == []


def test_empty_comparator_execution_v3_only_evidence_channels_is_empty() -> None:
    state = empty_comparator_execution()

    assert state.v3_only_evidence_channels == []


# ---------------------------------------------------------------------------
# _default_activation_decisions
# ---------------------------------------------------------------------------


def test_default_activation_decisions_has_two_keys() -> None:
    decisions = _default_activation_decisions()

    assert len(decisions) == 2


def test_default_activation_decisions_keys_match_activation_unit_values() -> None:
    decisions = _default_activation_decisions()

    assert ActivationUnit.V3_SHADOW_VERDICT.value in decisions
    assert ActivationUnit.NUMERIC_VERDICT_RATES.value in decisions


def test_default_activation_decisions_all_false() -> None:
    decisions = _default_activation_decisions()

    assert all(v is False for v in decisions.values())
