from __future__ import annotations

from crisp.v3.rp3_activation import (
    ActivationDecisionState,
    ActivationUnit,
    RuntimeActivationContext,
    VNGateState,
    check_forbidden_surfaces,
    may_render_numeric_verdict_rates,
    may_render_v3_shadow_verdict,
)


def _all_gates_met() -> VNGateState:
    return VNGateState(
        vn_01=True, vn_02=True, vn_03=True, vn_04=True, vn_05=True, vn_06=True
    )


def _ctx(
    *,
    shadow_verdict_accepted: bool = False,
    numeric_rates_accepted: bool = False,
    vn_gate: VNGateState | None = None,
    full_verdict_computable: bool = True,
    denominator_contract_satisfied: bool = True,
) -> RuntimeActivationContext:
    return RuntimeActivationContext(
        decision=ActivationDecisionState(
            v3_shadow_verdict_accepted=shadow_verdict_accepted,
            numeric_verdict_rates_accepted=numeric_rates_accepted,
        ),
        vn_gate=vn_gate or _all_gates_met(),
        full_verdict_computable=full_verdict_computable,
        denominator_contract_satisfied=denominator_contract_satisfied,
    )


# ---------------------------------------------------------------------------
# ActivationUnit enum values
# ---------------------------------------------------------------------------


def test_activation_unit_values_are_stable() -> None:
    assert ActivationUnit.V3_SHADOW_VERDICT.value == "v3_shadow_verdict"
    assert ActivationUnit.NUMERIC_VERDICT_RATES.value == "numeric_verdict_rates"


# ---------------------------------------------------------------------------
# VNGateState.all_satisfied
# ---------------------------------------------------------------------------


def test_vn_gate_all_satisfied_when_all_true() -> None:
    assert _all_gates_met().all_satisfied is True


def test_vn_gate_not_satisfied_when_any_false() -> None:
    cases = [
        VNGateState(vn_01=False, vn_02=True, vn_03=True, vn_04=True, vn_05=True, vn_06=True),
        VNGateState(vn_01=True, vn_02=False, vn_03=True, vn_04=True, vn_05=True, vn_06=True),
        VNGateState(vn_01=True, vn_02=True, vn_03=False, vn_04=True, vn_05=True, vn_06=True),
        VNGateState(vn_01=True, vn_02=True, vn_03=True, vn_04=False, vn_05=True, vn_06=True),
        VNGateState(vn_01=True, vn_02=True, vn_03=True, vn_04=True, vn_05=False, vn_06=True),
        VNGateState(vn_01=True, vn_02=True, vn_03=True, vn_04=True, vn_05=True, vn_06=False),
    ]
    for gate in cases:
        assert gate.all_satisfied is False


# ---------------------------------------------------------------------------
# may_render_v3_shadow_verdict
# ---------------------------------------------------------------------------


def test_shadow_verdict_renderable_when_all_conditions_met() -> None:
    ctx = _ctx(shadow_verdict_accepted=True, full_verdict_computable=True)

    assert may_render_v3_shadow_verdict(ctx) is True


def test_shadow_verdict_not_renderable_without_decision_acceptance() -> None:
    ctx = _ctx(shadow_verdict_accepted=False, full_verdict_computable=True)

    assert may_render_v3_shadow_verdict(ctx) is False


def test_shadow_verdict_not_renderable_when_vn_gate_unmet() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=True,
        vn_gate=VNGateState(vn_01=True, vn_02=True, vn_03=False, vn_04=True, vn_05=True, vn_06=True),
        full_verdict_computable=True,
    )

    assert may_render_v3_shadow_verdict(ctx) is False


def test_shadow_verdict_not_renderable_when_full_verdict_not_computable() -> None:
    ctx = _ctx(shadow_verdict_accepted=True, full_verdict_computable=False)

    assert may_render_v3_shadow_verdict(ctx) is False


# ---------------------------------------------------------------------------
# may_render_numeric_verdict_rates
# ---------------------------------------------------------------------------


def test_numeric_rates_renderable_when_all_conditions_met() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=True,
        numeric_rates_accepted=True,
        full_verdict_computable=True,
        denominator_contract_satisfied=True,
    )

    assert may_render_numeric_verdict_rates(ctx) is True


def test_numeric_rates_not_renderable_without_numeric_acceptance() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=True,
        numeric_rates_accepted=False,
        full_verdict_computable=True,
        denominator_contract_satisfied=True,
    )

    assert may_render_numeric_verdict_rates(ctx) is False


def test_numeric_rates_not_renderable_when_shadow_verdict_inactive() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=False,
        numeric_rates_accepted=True,
        full_verdict_computable=True,
        denominator_contract_satisfied=True,
    )

    assert may_render_numeric_verdict_rates(ctx) is False


def test_numeric_rates_not_renderable_when_denominator_unsatisfied() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=True,
        numeric_rates_accepted=True,
        full_verdict_computable=True,
        denominator_contract_satisfied=False,
    )

    assert may_render_numeric_verdict_rates(ctx) is False


# ---------------------------------------------------------------------------
# check_forbidden_surfaces
# ---------------------------------------------------------------------------


def _passing_ctx() -> RuntimeActivationContext:
    return _ctx(
        shadow_verdict_accepted=True,
        numeric_rates_accepted=True,
        full_verdict_computable=True,
        denominator_contract_satisfied=True,
    )


def test_check_forbidden_surfaces_clean_when_no_violations() -> None:
    errors = check_forbidden_surfaces(
        ctx=_passing_ctx(),
        comparable_channels=["path", "catalytic"],
        component_match_keys=["path", "catalytic_rule3a"],
        mixed_summary_requested=False,
        numeric_rates_present=False,
    )

    assert errors == []


def test_check_forbidden_surfaces_blocks_cap_in_comparable_channels() -> None:
    errors = check_forbidden_surfaces(
        ctx=_passing_ctx(),
        comparable_channels=["path", "catalytic", "cap"],
        component_match_keys=["path"],
        mixed_summary_requested=False,
        numeric_rates_present=False,
    )

    assert any("cap must not appear in comparable_channels" in e for e in errors)


def test_check_forbidden_surfaces_blocks_rule3b_in_component_keys() -> None:
    errors = check_forbidden_surfaces(
        ctx=_passing_ctx(),
        comparable_channels=["path", "catalytic"],
        component_match_keys=["path", "catalytic_rule3b"],
        mixed_summary_requested=False,
        numeric_rates_present=False,
    )

    assert any("catalytic_rule3b must not appear in component_matches" in e for e in errors)


def test_check_forbidden_surfaces_blocks_mixed_summary() -> None:
    errors = check_forbidden_surfaces(
        ctx=_passing_ctx(),
        comparable_channels=["path"],
        component_match_keys=["path"],
        mixed_summary_requested=True,
        numeric_rates_present=False,
    )

    assert any("mixed rc2/v3 aggregate summaries are forbidden" in e for e in errors)


def test_check_forbidden_surfaces_blocks_numeric_rates_when_context_inactive() -> None:
    ctx = _ctx(
        shadow_verdict_accepted=False,
        numeric_rates_accepted=True,
        full_verdict_computable=True,
        denominator_contract_satisfied=True,
    )
    errors = check_forbidden_surfaces(
        ctx=ctx,
        comparable_channels=["path"],
        component_match_keys=["path"],
        mixed_summary_requested=False,
        numeric_rates_present=True,
    )

    assert any("numeric verdict rates present" in e for e in errors)


def test_check_forbidden_surfaces_allows_numeric_rates_when_context_active() -> None:
    errors = check_forbidden_surfaces(
        ctx=_passing_ctx(),
        comparable_channels=["path"],
        component_match_keys=["path"],
        mixed_summary_requested=False,
        numeric_rates_present=True,
    )

    assert not any("numeric verdict rates" in e for e in errors)
