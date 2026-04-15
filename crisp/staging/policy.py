from __future__ import annotations

from crisp.models.runtime import SearchControlAction, Verdict
from crisp.reason_codes import UNCLEAR_EXPLORATION_LIMIT_REACHED


def decide_action(
    v_core: Verdict,
    feasible_count: int,
    best_target_distance: float,
    config,
    stage_id: int,
) -> SearchControlAction:
    max_stage = int(config.staging.max_stage)
    near_lower = float(config.staging.retry_distance_lower)
    near_upper = float(config.staging.retry_distance_upper)

    if stage_id < max_stage:
        if v_core == Verdict.PASS:
            return SearchControlAction.FINALIZE_PASS
        if v_core == Verdict.FAIL:
            return SearchControlAction.FINALIZE_FAIL
        if feasible_count == 0:
            return SearchControlAction.CONTINUE
        if near_lower <= float(best_target_distance) <= near_upper:
            return SearchControlAction.CONTINUE
        return SearchControlAction.FINALIZE_BY_TERMINAL_POLICY

    if v_core == Verdict.PASS:
        return SearchControlAction.FINALIZE_PASS
    if v_core == Verdict.FAIL:
        return SearchControlAction.FINALIZE_FAIL
    return SearchControlAction.FINALIZE_BY_TERMINAL_POLICY


def scv_terminal_policy(
    v_core: Verdict,
    feasible_count: int,
    best_target_distance: float | None,
    config,
):
    far = float(config.staging.far_target_threshold)

    if feasible_count == 0:
        return Verdict.FAIL, "FAIL_NO_FEASIBLE"
    if best_target_distance is not None and float(best_target_distance) > far:
        return Verdict.FAIL, "FAIL_LOW_PRIORITY_FAR_TARGET"
    return Verdict.UNCLEAR, UNCLEAR_EXPLORATION_LIMIT_REACHED


def should_stop(anchoring_obs, offtarget_obs, config) -> bool:
    threshold = float(config.distance_threshold) - float(config.anchoring.epsilon)
    if float(anchoring_obs.best_target_distance) <= threshold:
        if config.pathway == "noncovalent":
            return True
        if offtarget_obs is None:
            return False
        far_offtarget = float(config.offtarget.distance_threshold) + float(
            config.offtarget.epsilon
        )
        if float(offtarget_obs.best_offtarget_distance) > far_offtarget:
            return True
    return False
