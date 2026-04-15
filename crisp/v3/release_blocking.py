from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from crisp.v3.operator_surface_state import (
    OPERATOR_SURFACE_STATE_ARTIFACT,
    PROMOTION_AUTHORITY_REFERENCE,
    PROMOTION_GATE_IDS,
    build_runtime_activation_context,
)
from crisp.v3.report_guards import ReportGuardError, enforce_verdict_record_dual_write_guard
from crisp.v3.rp3_activation import check_forbidden_surfaces

PROMOTION_STATUS_ADVISORY = "advisory"
PROMOTION_STATUS_BLOCKING = "blocking"
RELEASE_GATE_STATE_SCHEMA_VERSION = "crisp.v3.release_gate_state/v1"

_NUMERIC_RATE_PATTERN = re.compile(r"verdict_match_rate:\s*`\d+/\d+")


@dataclass(frozen=True, slots=True)
class LanePromotionStatus:
    lane_id: str
    promotion_candidate: bool
    failed_gate_ids: tuple[str, ...]
    authority_reference: str
    promotion_status: str
    human_explicit_decision_required: bool
    required_matrix_mutation_allowed: bool


@dataclass(frozen=True, slots=True)
class ReleaseGateEvaluation:
    schema_version: str = RELEASE_GATE_STATE_SCHEMA_VERSION
    exit_code: int = 0
    run_failed: bool = False
    artifact_failure: bool = False
    release_blocked: bool = False
    ci_blocked: bool = False
    hard_block_failures: list[str] = field(default_factory=list)
    blocking_failures: list[str] = field(default_factory=list)
    advisory_failures: list[str] = field(default_factory=list)
    promotion_gate_results: dict[str, dict[str, Any]] = field(default_factory=dict)


class SidecarReleaseGateError(RuntimeError):
    def __init__(self, evaluation: ReleaseGateEvaluation) -> None:
        message = (
            evaluation.hard_block_failures[0]
            if evaluation.hard_block_failures
            else "sidecar release gate blocked artifact finalization"
        )
        super().__init__(message)
        self.evaluation = evaluation


def evaluate_release_blocking(
    *,
    operator_surface_state: Mapping[str, Any] | None,
    comparable_channels: Iterable[str],
    component_match_keys: Iterable[str],
    required_candidacy_payload: Mapping[str, Any] | None = None,
    operator_summary_text: str | None = None,
    numeric_rates_present: bool | None = None,
    mixed_summary_requested: bool | None = None,
    verdict_record: Mapping[str, Any] | None = None,
    sidecar_run_record: Mapping[str, Any] | None = None,
    materialized_outputs: Iterable[str] = (),
) -> ReleaseGateEvaluation:
    hard_block_failures: list[str] = []
    blocking_failures: list[str] = []
    advisory_failures: list[str] = []
    normalized_promotion_gate_results: dict[str, dict[str, Any]] = {}

    if not isinstance(operator_surface_state, Mapping):
        hard_block_failures.append("operator_surface_state_missing")
    else:
        if OPERATOR_SURFACE_STATE_ARTIFACT not in {
            str(relative_path) for relative_path in materialized_outputs
        }:
            hard_block_failures.append("operator_surface_state_unmaterialized")
        try:
            normalized_promotion_gate_results = normalize_promotion_gate_results(
                promotion_gate_results=operator_surface_state.get("promotion_gate_results", {}),
                required_candidacy_payload=required_candidacy_payload,
            )
        except ValueError as exc:
            hard_block_failures.append(f"promotion_gate_results_invalid:{exc}")

        try:
            ctx = build_runtime_activation_context(
                activation_decisions=operator_surface_state.get("activation_decisions"),
                vn_gate_state=operator_surface_state.get("vn_gate_state"),
                full_verdict_computable=operator_surface_state.get("full_verdict_computable", False),
                denominator_contract_satisfied=operator_surface_state.get(
                    "denominator_contract_satisfied",
                    False,
                ),
            )
        except (TypeError, ValueError) as exc:
            hard_block_failures.append(f"operator_surface_state_invalid:{exc}")
        else:
            forbidden_surface_errors = check_forbidden_surfaces(
                ctx=ctx,
                comparable_channels=[str(channel_name) for channel_name in comparable_channels],
                component_match_keys=[str(key) for key in component_match_keys],
                mixed_summary_requested=_mixed_summary_requested(
                    operator_summary_text=operator_summary_text,
                    explicit_value=mixed_summary_requested,
                ),
                numeric_rates_present=_numeric_rates_present(
                    operator_summary_text=operator_summary_text,
                    verdict_record=verdict_record,
                    explicit_value=numeric_rates_present,
                ),
            )
            hard_block_failures.extend(_translate_forbidden_surface_errors(forbidden_surface_errors))

    if isinstance(verdict_record, Mapping) and isinstance(sidecar_run_record, Mapping):
        try:
            enforce_verdict_record_dual_write_guard(
                verdict_record=verdict_record,
                sidecar_run_record=sidecar_run_record,
            )
        except ReportGuardError as exc:
            hard_block_failures.append(f"cross_artifact_mismatch:{exc}")

    for lane_id, lane_payload in normalized_promotion_gate_results.items():
        failed_gate_ids = tuple(str(gate_id) for gate_id in lane_payload.get("failed_gate_ids", ()))
        if not failed_gate_ids:
            continue
        failure = f"promotion_gate_failure:{lane_id}:{','.join(failed_gate_ids)}"
        if lane_payload.get("promotion_status") == PROMOTION_STATUS_BLOCKING:
            blocking_failures.append(failure)
        else:
            advisory_failures.append(failure)

    hard_block_failures = sorted(set(hard_block_failures))
    blocking_failures = sorted(set(blocking_failures))
    advisory_failures = sorted(set(advisory_failures))
    run_failed = bool(hard_block_failures)
    ci_blocked = bool(blocking_failures)
    release_blocked = run_failed or ci_blocked
    return ReleaseGateEvaluation(
        exit_code=1 if run_failed else 0,
        run_failed=run_failed,
        artifact_failure=run_failed,
        release_blocked=release_blocked,
        ci_blocked=ci_blocked,
        hard_block_failures=hard_block_failures,
        blocking_failures=blocking_failures,
        advisory_failures=advisory_failures,
        promotion_gate_results=normalized_promotion_gate_results,
    )


def normalize_promotion_gate_results(
    *,
    promotion_gate_results: Mapping[str, Any] | None,
    required_candidacy_payload: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    source = promotion_gate_results if isinstance(promotion_gate_results, Mapping) else {}
    normalized: dict[str, dict[str, Any]] = {}
    for lane_id, payload in source.items():
        if not isinstance(payload, Mapping):
            raise ValueError(f"lane payload must be an object: {lane_id}")
        normalized_lane_id = str(lane_id)
        normalized_status = _normalize_promotion_status(
            payload.get("promotion_status"),
            fallback=_default_promotion_status(
                lane_id=normalized_lane_id,
                required_candidacy_payload=required_candidacy_payload,
            ),
        )
        authority_reference = str(
            payload.get("authority_reference", PROMOTION_AUTHORITY_REFERENCE)
        )
        if authority_reference != PROMOTION_AUTHORITY_REFERENCE:
            raise ValueError(f"authority_reference mismatch for {normalized_lane_id}")
        failed_gate_ids = _normalize_failed_gate_ids(
            payload.get("failed_gate_ids", ()),
            lane_id=normalized_lane_id,
        )
        normalized[normalized_lane_id] = asdict(
            LanePromotionStatus(
                lane_id=normalized_lane_id,
                promotion_candidate=bool(payload.get("promotion_candidate", False)),
                failed_gate_ids=failed_gate_ids,
                authority_reference=authority_reference,
                promotion_status=normalized_status,
                human_explicit_decision_required=bool(
                    payload.get("human_explicit_decision_required", True)
                ),
                required_matrix_mutation_allowed=bool(
                    payload.get("required_matrix_mutation_allowed", False)
                ),
            )
        )
    return normalized


def release_gate_state_payload(evaluation: ReleaseGateEvaluation) -> dict[str, Any]:
    return asdict(evaluation)


def _default_promotion_status(
    *,
    lane_id: str,
    required_candidacy_payload: Mapping[str, Any] | None,
) -> str:
    if not isinstance(required_candidacy_payload, Mapping):
        return PROMOTION_STATUS_ADVISORY
    if str(required_candidacy_payload.get("channel_name", "")) != lane_id:
        return PROMOTION_STATUS_ADVISORY
    explicit_status = required_candidacy_payload.get("promotion_status")
    if isinstance(explicit_status, str):
        return explicit_status
    return PROMOTION_STATUS_ADVISORY


def _normalize_promotion_status(value: Any, *, fallback: str) -> str:
    normalized = str(fallback if value is None else value)
    if normalized not in {PROMOTION_STATUS_ADVISORY, PROMOTION_STATUS_BLOCKING}:
        raise ValueError(f"unsupported promotion_status: {normalized}")
    return normalized


def _normalize_failed_gate_ids(value: Any, *, lane_id: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"failed_gate_ids must be a list or tuple for {lane_id}")
    normalized = tuple(sorted(str(gate_id) for gate_id in value))
    unsupported_gate_ids = sorted(set(normalized) - set(PROMOTION_GATE_IDS))
    if unsupported_gate_ids:
        raise ValueError(
            f"unsupported promotion gate ids for {lane_id}: {', '.join(unsupported_gate_ids)}"
        )
    return normalized


def _mixed_summary_requested(
    *,
    operator_summary_text: str | None,
    explicit_value: bool | None,
) -> bool:
    if explicit_value is not None:
        return bool(explicit_value)
    if not isinstance(operator_summary_text, str):
        return False
    return "mixed summary" in operator_summary_text.lower()


def _numeric_rates_present(
    *,
    operator_summary_text: str | None,
    verdict_record: Mapping[str, Any] | None,
    explicit_value: bool | None,
) -> bool:
    if explicit_value is not None:
        return bool(explicit_value)
    if isinstance(verdict_record, Mapping):
        if verdict_record.get("verdict_match_rate") is not None:
            return True
        if verdict_record.get("verdict_mismatch_rate") is not None:
            return True
    return isinstance(operator_summary_text, str) and bool(
        _NUMERIC_RATE_PATTERN.search(operator_summary_text)
    )


def _translate_forbidden_surface_errors(errors: Iterable[str]) -> list[str]:
    translated: list[str] = []
    for error in errors:
        if error == "numeric verdict rates present while runtime activation conditions are unmet":
            translated.append("forbidden_surface:numeric_verdict_rates_leak")
        elif error == "catalytic_rule3b must not appear in component_matches":
            translated.append("forbidden_surface:catalytic_rule3b_component_match_leak")
        elif error == "cap must not appear in comparable_channels":
            translated.append("forbidden_surface:cap_comparable_leak")
        elif error == "mixed rc2/v3 aggregate summaries are forbidden":
            translated.append("forbidden_surface:mixed_summary_requested")
        else:
            translated.append(f"forbidden_surface:{error}")
    return translated
