from __future__ import annotations

LEGACY_UNCLEAR_SAMPLING_BUDGET = "UNCLEAR_SAMPLING_BUDGET"
UNCLEAR_INSUFFICIENT_FEASIBLE_POSES = "UNCLEAR_INSUFFICIENT_FEASIBLE_POSES"
UNCLEAR_EXPLORATION_LIMIT_REACHED = "UNCLEAR_EXPLORATION_LIMIT_REACHED"


def normalize_legacy_unclear_reason(
    reason: object,
    *,
    feasible_count: int | None = None,
    confident_fail_threshold: int = 1,
) -> object:
    """Map legacy ambiguous unclear reasons to context-specific replacements.

    Old artifacts used ``UNCLEAR_SAMPLING_BUDGET`` both when the search produced
    too few feasible poses to support a confident fail and when the configured
    exploration limit was reached without a decisive terminal verdict.
    """
    if reason != LEGACY_UNCLEAR_SAMPLING_BUDGET:
        return reason
    if feasible_count is not None and feasible_count < confident_fail_threshold:
        return UNCLEAR_INSUFFICIENT_FEASIBLE_POSES
    return UNCLEAR_EXPLORATION_LIMIT_REACHED
