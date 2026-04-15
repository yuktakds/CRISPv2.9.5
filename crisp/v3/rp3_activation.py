from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActivationUnit(str, Enum):
    V3_SHADOW_VERDICT = "v3_shadow_verdict"
    NUMERIC_VERDICT_RATES = "numeric_verdict_rates"


@dataclass(frozen=True)
class ActivationDecisionState:
    v3_shadow_verdict_accepted: bool
    numeric_verdict_rates_accepted: bool


@dataclass(frozen=True)
class VNGateState:
    vn_01: bool
    vn_02: bool
    vn_03: bool
    vn_04: bool
    vn_05: bool
    vn_06: bool

    @property
    def all_satisfied(self) -> bool:
        return (
            self.vn_01
            and self.vn_02
            and self.vn_03
            and self.vn_04
            and self.vn_05
            and self.vn_06
        )


@dataclass(frozen=True)
class RuntimeActivationContext:
    decision: ActivationDecisionState
    vn_gate: VNGateState
    full_verdict_computable: bool
    denominator_contract_satisfied: bool


def may_render_v3_shadow_verdict(ctx: RuntimeActivationContext) -> bool:
    return (
        ctx.decision.v3_shadow_verdict_accepted
        and ctx.vn_gate.all_satisfied
        and ctx.full_verdict_computable
    )


def may_render_numeric_verdict_rates(ctx: RuntimeActivationContext) -> bool:
    return (
        ctx.decision.numeric_verdict_rates_accepted
        and may_render_v3_shadow_verdict(ctx)
        and ctx.denominator_contract_satisfied
    )


def check_forbidden_surfaces(
    *,
    ctx: RuntimeActivationContext,
    comparable_channels: list[str],
    component_match_keys: list[str],
    mixed_summary_requested: bool,
    numeric_rates_present: bool,
) -> list[str]:
    errors: list[str] = []

    if "cap" in comparable_channels:
        errors.append("cap must not appear in comparable_channels")

    if "catalytic_rule3b" in component_match_keys:
        errors.append("catalytic_rule3b must not appear in component_matches")

    if mixed_summary_requested:
        errors.append("mixed rc2/v3 aggregate summaries are forbidden")

    if numeric_rates_present and not may_render_numeric_verdict_rates(ctx):
        errors.append(
            "numeric verdict rates present while runtime activation conditions are unmet"
        )

    return errors
