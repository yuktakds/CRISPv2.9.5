from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from crisp.v3.promotion_gates import (
    PROMOTION_GATE_AUTHORITY_DOCUMENT,
    PROMOTION_GATE_AUTHORITY_MODE,
    PROMOTION_GATE_AUTHORITY_SECTION,
)
from crisp.v3.rp3_activation import (
    ActivationDecisionState,
    ActivationUnit,
    RuntimeActivationContext,
    VNGateState,
    may_render_numeric_verdict_rates,
    may_render_v3_shadow_verdict,
)

OPERATOR_SURFACE_STATE_ARTIFACT = "operator_surface_state.json"
PROMOTION_AUTHORITY_REFERENCE = (
    f"{PROMOTION_GATE_AUTHORITY_DOCUMENT}#{PROMOTION_GATE_AUTHORITY_SECTION}"
)
PROMOTION_GATE_IDS = ("PR-01", "PR-02", "PR-03", "PR-04", "PR-05", "PR-06")


@dataclass(frozen=True, slots=True)
class SuppressedSurface:
    surface: str
    reason: str


@dataclass(frozen=True, slots=True)
class PromotionGateResult:
    lane_id: str
    promotion_candidate: bool
    failed_gate_ids: tuple[str, ...]
    authority_reference: str
    human_explicit_decision_required: bool
    required_matrix_mutation_allowed: bool


@dataclass(frozen=True, slots=True)
class OperatorSurfaceState:
    activation_decisions: dict[str, bool]
    vn_gate_state: dict[str, bool]
    full_verdict_computable: bool
    denominator_contract_satisfied: bool
    v3_shadow_verdict_renderable: bool
    numeric_verdict_rates_renderable: bool
    suppressed_surfaces: list[SuppressedSurface] = field(default_factory=list)
    promotion_gate_results: dict[str, dict[str, Any]] = field(default_factory=dict)


def build_runtime_activation_context(
    *,
    activation_decisions: Mapping[str, Any] | None = None,
    vn_gates: Mapping[str, Mapping[str, Any]] | None = None,
    vn_gate_state: Mapping[str, Any] | None = None,
    full_verdict_computable: bool,
    denominator_contract_satisfied: bool,
) -> RuntimeActivationContext:
    normalized_activation_decisions = _normalize_activation_decisions(activation_decisions)
    normalized_vn_gate_state = _normalize_vn_gate_state(vn_gates=vn_gates, vn_gate_state=vn_gate_state)
    return RuntimeActivationContext(
        decision=ActivationDecisionState(
            v3_shadow_verdict_accepted=normalized_activation_decisions[ActivationUnit.V3_SHADOW_VERDICT.value],
            numeric_verdict_rates_accepted=normalized_activation_decisions[
                ActivationUnit.NUMERIC_VERDICT_RATES.value
            ],
        ),
        vn_gate=VNGateState(
            vn_01=normalized_vn_gate_state["vn_01"],
            vn_02=normalized_vn_gate_state["vn_02"],
            vn_03=normalized_vn_gate_state["vn_03"],
            vn_04=normalized_vn_gate_state["vn_04"],
            vn_05=normalized_vn_gate_state["vn_05"],
            vn_06=normalized_vn_gate_state["vn_06"],
        ),
        full_verdict_computable=bool(full_verdict_computable),
        denominator_contract_satisfied=bool(denominator_contract_satisfied),
    )


def build_operator_surface_state(
    *,
    activation_decisions: Mapping[str, Any] | None = None,
    vn_gates: Mapping[str, Mapping[str, Any]] | None = None,
    vn_gate_state: Mapping[str, Any] | None = None,
    full_verdict_computable: bool,
    denominator_contract_satisfied: bool,
    required_candidacy_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_activation_decisions = _normalize_activation_decisions(activation_decisions)
    normalized_vn_gate_state = _normalize_vn_gate_state(vn_gates=vn_gates, vn_gate_state=vn_gate_state)
    ctx = build_runtime_activation_context(
        activation_decisions=normalized_activation_decisions,
        vn_gate_state=normalized_vn_gate_state,
        full_verdict_computable=full_verdict_computable,
        denominator_contract_satisfied=denominator_contract_satisfied,
    )

    suppressed_surfaces: list[SuppressedSurface] = []
    shadow_reason = _shadow_suppression_reason(ctx=ctx, vn_gate_state=normalized_vn_gate_state)
    if shadow_reason is not None:
        suppressed_surfaces.append(
            SuppressedSurface(surface=ActivationUnit.V3_SHADOW_VERDICT.value, reason=shadow_reason)
        )
    numeric_reason = _numeric_suppression_reason(ctx=ctx, vn_gate_state=normalized_vn_gate_state)
    if numeric_reason is not None:
        suppressed_surfaces.append(
            SuppressedSurface(surface=ActivationUnit.NUMERIC_VERDICT_RATES.value, reason=numeric_reason)
        )

    promotion_gate_results: dict[str, dict[str, Any]] = {}
    if isinstance(required_candidacy_payload, Mapping):
        pr_gates = required_candidacy_payload.get("pr_gates", {})
        if not isinstance(pr_gates, Mapping):
            pr_gates = {}
        _validate_pr_gate_authority(pr_gates)
        failed_gate_ids = tuple(
            sorted(
                gate_id
                for gate_id, gate in pr_gates.items()
                if not (isinstance(gate, Mapping) and bool(gate.get("passed", False)))
            )
        )
        lane_id = str(required_candidacy_payload.get("channel_name", "path"))
        promotion_gate_results[lane_id] = asdict(
            PromotionGateResult(
                lane_id=lane_id,
                promotion_candidate=bool(required_candidacy_payload.get("promotion_candidate", False)),
                failed_gate_ids=failed_gate_ids,
                authority_reference=PROMOTION_AUTHORITY_REFERENCE,
                human_explicit_decision_required=bool(
                    required_candidacy_payload.get("human_explicit_decision_required", True)
                ),
                required_matrix_mutation_allowed=bool(
                    required_candidacy_payload.get("required_matrix_mutation_allowed", False)
                ),
            )
        )

    return asdict(
        OperatorSurfaceState(
            activation_decisions=normalized_activation_decisions,
            vn_gate_state={
                **normalized_vn_gate_state,
                "all_satisfied": ctx.vn_gate.all_satisfied,
            },
            full_verdict_computable=ctx.full_verdict_computable,
            denominator_contract_satisfied=ctx.denominator_contract_satisfied,
            v3_shadow_verdict_renderable=may_render_v3_shadow_verdict(ctx),
            numeric_verdict_rates_renderable=may_render_numeric_verdict_rates(ctx),
            suppressed_surfaces=suppressed_surfaces,
            promotion_gate_results=promotion_gate_results,
        )
    )


def suppression_reason_by_surface(
    operator_surface_state: Mapping[str, Any] | None,
) -> dict[str, str]:
    if not isinstance(operator_surface_state, Mapping):
        return {}
    suppressed_surfaces = operator_surface_state.get("suppressed_surfaces", ())
    if not isinstance(suppressed_surfaces, list):
        return {}
    reasons: dict[str, str] = {}
    for item in suppressed_surfaces:
        if not isinstance(item, Mapping):
            continue
        surface = item.get("surface")
        reason = item.get("reason")
        if isinstance(surface, str) and isinstance(reason, str):
            reasons[surface] = reason
    return reasons


def _normalize_activation_decisions(
    activation_decisions: Mapping[str, Any] | None,
) -> dict[str, bool]:
    source = activation_decisions if isinstance(activation_decisions, Mapping) else {}
    return {
        ActivationUnit.V3_SHADOW_VERDICT.value: bool(
            source.get(ActivationUnit.V3_SHADOW_VERDICT.value, False)
        ),
        ActivationUnit.NUMERIC_VERDICT_RATES.value: bool(
            source.get(ActivationUnit.NUMERIC_VERDICT_RATES.value, False)
        ),
    }


def _normalize_vn_gate_state(
    *,
    vn_gates: Mapping[str, Mapping[str, Any]] | None,
    vn_gate_state: Mapping[str, Any] | None,
) -> dict[str, bool]:
    flat = vn_gate_state if isinstance(vn_gate_state, Mapping) else {}
    gates = vn_gates if isinstance(vn_gates, Mapping) else {}

    def _vn_flag(flat_key: str, legacy_key: str) -> bool:
        if flat_key in flat:
            return bool(flat.get(flat_key))
        legacy_gate = gates.get(legacy_key)
        if isinstance(legacy_gate, Mapping):
            return bool(legacy_gate.get("passed", False))
        return False

    return {
        "vn_01": _vn_flag("vn_01", "VN-01"),
        "vn_02": _vn_flag("vn_02", "VN-02"),
        "vn_03": _vn_flag("vn_03", "VN-03"),
        "vn_04": _vn_flag("vn_04", "VN-04"),
        "vn_05": _vn_flag("vn_05", "VN-05"),
        "vn_06": _vn_flag("vn_06", "VN-06"),
    }


def _first_unmet_vn(vn_gate_state: Mapping[str, bool]) -> str | None:
    for key in ("vn_01", "vn_02", "vn_03", "vn_04", "vn_05", "vn_06"):
        if not bool(vn_gate_state.get(key, False)):
            return key
    return None


def _shadow_suppression_reason(
    *,
    ctx: RuntimeActivationContext,
    vn_gate_state: Mapping[str, bool],
) -> str | None:
    if may_render_v3_shadow_verdict(ctx):
        return None
    if not ctx.decision.v3_shadow_verdict_accepted:
        return "activation_decision_not_accepted"
    if not ctx.vn_gate.all_satisfied:
        first_unmet = _first_unmet_vn(vn_gate_state)
        return (
            "vn_gate_unmet"
            if first_unmet is None
            else f"vn_gate_unmet:{first_unmet}"
        )
    if not ctx.full_verdict_computable:
        return "full_verdict_not_computable"
    return "shadow_verdict_not_renderable"


def _numeric_suppression_reason(
    *,
    ctx: RuntimeActivationContext,
    vn_gate_state: Mapping[str, bool],
) -> str | None:
    if may_render_numeric_verdict_rates(ctx):
        return None
    if not ctx.decision.numeric_verdict_rates_accepted:
        return "numeric_activation_decision_not_accepted"
    if not may_render_v3_shadow_verdict(ctx):
        shadow_reason = _shadow_suppression_reason(ctx=ctx, vn_gate_state=vn_gate_state)
        return (
            "shadow_verdict_inactive"
            if shadow_reason is None
            else f"shadow_verdict_inactive:{shadow_reason}"
        )
    if not ctx.denominator_contract_satisfied:
        return "denominator_contract_unsatisfied"
    return "numeric_verdict_rates_not_renderable"


def _validate_pr_gate_authority(pr_gates: Mapping[str, Any]) -> None:
    for gate_id, gate in pr_gates.items():
        if gate_id not in PROMOTION_GATE_IDS:
            raise ValueError(f"unsupported promotion gate id in operator surface: {gate_id}")
        if not isinstance(gate, Mapping):
            raise ValueError(f"promotion gate payload must be an object: {gate_id}")
        authority_reference = gate.get("authority_reference")
        if not isinstance(authority_reference, Mapping):
            raise ValueError(f"promotion gate authority_reference is required: {gate_id}")
        if authority_reference.get("document") != PROMOTION_GATE_AUTHORITY_DOCUMENT:
            raise ValueError(f"promotion gate authority document mismatch: {gate_id}")
        if authority_reference.get("section") != PROMOTION_GATE_AUTHORITY_SECTION:
            raise ValueError(f"promotion gate authority section mismatch: {gate_id}")
        if authority_reference.get("evaluation_mode") != PROMOTION_GATE_AUTHORITY_MODE:
            raise ValueError(f"promotion gate authority mode mismatch: {gate_id}")
        if authority_reference.get("gate_id") != gate_id:
            raise ValueError(f"promotion gate authority gate_id mismatch: {gate_id}")
