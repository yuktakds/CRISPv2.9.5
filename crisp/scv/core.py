from __future__ import annotations

from crisp.models.runtime import SensorVerdict, Verdict


def scv_integrate(verdicts: list[Verdict]) -> Verdict:
    if any(v == Verdict.FAIL for v in verdicts):
        return Verdict.FAIL
    if any(v == Verdict.UNCLEAR for v in verdicts):
        return Verdict.UNCLEAR
    return Verdict.PASS


def scv_anchoring(anchoring_obs, exploration_log, config) -> SensorVerdict:
    d = float(anchoring_obs.best_target_distance)
    theta = float(config.distance_threshold)
    eps = float(config.anchoring.epsilon)
    feasible_count = exploration_log.feasible_count
    f_min = int(config.scv.confident_fail_threshold)

    if d <= theta:
        return SensorVerdict(Verdict.PASS, {"borderline": d > theta - eps})
    if feasible_count is None:
        return SensorVerdict(Verdict.UNCLEAR, "UNCLEAR_INPUT_MISSING")
    if feasible_count < f_min:
        return SensorVerdict(Verdict.UNCLEAR, "UNCLEAR_SAMPLING_BUDGET")
    if d <= theta + eps:
        return SensorVerdict(Verdict.UNCLEAR, "UNCLEAR_BORDERLINE_EPS")
    return SensorVerdict(Verdict.FAIL, "FAIL_ANCHORING_DISTANCE")


def scv_offtarget(offtarget_obs, exploration_log, config) -> SensorVerdict:
    d_off = float(offtarget_obs.best_offtarget_distance)
    theta = float(config.offtarget.distance_threshold)
    eps = float(config.offtarget.epsilon)
    feasible_count = exploration_log.feasible_count
    f_min = int(config.scv.confident_fail_threshold)

    if d_off > theta + eps:
        return SensorVerdict(Verdict.PASS, "OFFTARGET_SAFE")
    if d_off > theta:
        return SensorVerdict(Verdict.PASS, {"borderline": True})
    if feasible_count < f_min:
        return SensorVerdict(Verdict.UNCLEAR, "UNCLEAR_SAMPLING_BUDGET")
    if d_off >= theta - eps:
        return SensorVerdict(Verdict.UNCLEAR, "UNCLEAR_BORDERLINE_EPS")
    return SensorVerdict(Verdict.FAIL, "FAIL_OFFTARGET_CYS")
