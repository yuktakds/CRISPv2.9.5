from __future__ import annotations

from crisp.v3.operator_surface_state import (
    OPERATOR_SURFACE_STATE_ARTIFACT,
    PROMOTION_AUTHORITY_REFERENCE,
    PROMOTION_GATE_IDS,
    _first_unmet_vn,
    _normalize_activation_decisions,
    _normalize_vn_gate_state,
    suppression_reason_by_surface,
)
from crisp.v3.promotion_gates import (
    PROMOTION_GATE_AUTHORITY_DOCUMENT,
    PROMOTION_GATE_AUTHORITY_SECTION,
)
from crisp.v3.rp3_activation import ActivationUnit


# ---------------------------------------------------------------------------
# PROMOTION_GATE_IDS constant
# ---------------------------------------------------------------------------


def test_promotion_gate_ids_has_six_gates() -> None:
    assert len(PROMOTION_GATE_IDS) == 6


def test_promotion_gate_ids_includes_pr05() -> None:
    assert "PR-05" in PROMOTION_GATE_IDS


def test_promotion_gate_ids_all_start_with_pr() -> None:
    assert all(g.startswith("PR-") for g in PROMOTION_GATE_IDS)


# ---------------------------------------------------------------------------
# PROMOTION_AUTHORITY_REFERENCE constant
# ---------------------------------------------------------------------------


def test_promotion_authority_reference_contains_document_and_section() -> None:
    assert PROMOTION_GATE_AUTHORITY_DOCUMENT in PROMOTION_AUTHORITY_REFERENCE
    assert PROMOTION_GATE_AUTHORITY_SECTION in PROMOTION_AUTHORITY_REFERENCE
    assert "#" in PROMOTION_AUTHORITY_REFERENCE


# ---------------------------------------------------------------------------
# suppression_reason_by_surface
# ---------------------------------------------------------------------------


def test_suppression_reason_none_input_returns_empty_dict() -> None:
    assert suppression_reason_by_surface(None) == {}


def test_suppression_reason_empty_mapping_returns_empty_dict() -> None:
    assert suppression_reason_by_surface({}) == {}


def test_suppression_reason_single_entry_extracted() -> None:
    state = {
        "suppressed_surfaces": [
            {"surface": "v3_shadow_verdict", "reason": "activation_decision_not_accepted"}
        ]
    }
    result = suppression_reason_by_surface(state)

    assert result == {"v3_shadow_verdict": "activation_decision_not_accepted"}


def test_suppression_reason_multiple_entries_extracted() -> None:
    state = {
        "suppressed_surfaces": [
            {"surface": "v3_shadow_verdict", "reason": "reason_a"},
            {"surface": "numeric_verdict_rates", "reason": "reason_b"},
        ]
    }
    result = suppression_reason_by_surface(state)

    assert result["v3_shadow_verdict"] == "reason_a"
    assert result["numeric_verdict_rates"] == "reason_b"


def test_suppression_reason_non_list_suppressed_surfaces_returns_empty() -> None:
    assert suppression_reason_by_surface({"suppressed_surfaces": "not_a_list"}) == {}


def test_suppression_reason_non_string_surface_skipped() -> None:
    state = {"suppressed_surfaces": [{"surface": 123, "reason": "something"}]}
    assert suppression_reason_by_surface(state) == {}


def test_suppression_reason_missing_reason_skipped() -> None:
    state = {"suppressed_surfaces": [{"surface": "v3_shadow_verdict"}]}
    assert suppression_reason_by_surface(state) == {}


# ---------------------------------------------------------------------------
# _normalize_activation_decisions
# ---------------------------------------------------------------------------


def test_normalize_activation_decisions_none_input_returns_all_false() -> None:
    result = _normalize_activation_decisions(None)

    assert result[ActivationUnit.V3_SHADOW_VERDICT.value] is False
    assert result[ActivationUnit.NUMERIC_VERDICT_RATES.value] is False


def test_normalize_activation_decisions_empty_mapping_returns_all_false() -> None:
    result = _normalize_activation_decisions({})

    assert all(v is False for v in result.values())


def test_normalize_activation_decisions_true_values_preserved() -> None:
    source = {
        ActivationUnit.V3_SHADOW_VERDICT.value: True,
        ActivationUnit.NUMERIC_VERDICT_RATES.value: True,
    }
    result = _normalize_activation_decisions(source)

    assert result[ActivationUnit.V3_SHADOW_VERDICT.value] is True
    assert result[ActivationUnit.NUMERIC_VERDICT_RATES.value] is True


def test_normalize_activation_decisions_has_exactly_two_keys() -> None:
    result = _normalize_activation_decisions(None)

    assert len(result) == 2


# ---------------------------------------------------------------------------
# _first_unmet_vn
# ---------------------------------------------------------------------------


def test_first_unmet_vn_all_satisfied_returns_none() -> None:
    state = {f"vn_0{i}": True for i in range(1, 7)}
    assert _first_unmet_vn(state) == None


def test_first_unmet_vn_returns_first_false() -> None:
    state = {f"vn_0{i}": True for i in range(1, 7)}
    state["vn_02"] = False
    assert _first_unmet_vn(state) == "vn_02"


def test_first_unmet_vn_missing_key_treated_as_false() -> None:
    assert _first_unmet_vn({}) == "vn_01"


def test_first_unmet_vn_only_first_unmet_returned() -> None:
    state = {"vn_01": False, "vn_02": False, "vn_03": True, "vn_04": True, "vn_05": True, "vn_06": True}
    assert _first_unmet_vn(state) == "vn_01"


# ---------------------------------------------------------------------------
# _normalize_vn_gate_state
# ---------------------------------------------------------------------------


def test_normalize_vn_gate_state_none_inputs_returns_all_false() -> None:
    result = _normalize_vn_gate_state(vn_gates=None, vn_gate_state=None)

    assert all(v is False for v in result.values())
    assert len(result) == 6


def test_normalize_vn_gate_state_flat_state_used_directly() -> None:
    flat = {"vn_01": True, "vn_02": True, "vn_03": True, "vn_04": True, "vn_05": True, "vn_06": True}
    result = _normalize_vn_gate_state(vn_gates=None, vn_gate_state=flat)

    assert all(v is True for v in result.values())
