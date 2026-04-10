from __future__ import annotations

from types import SimpleNamespace

from crisp.models.runtime import Verdict
from crisp.reason_codes import (
    LEGACY_UNCLEAR_SAMPLING_BUDGET,
    UNCLEAR_EXPLORATION_LIMIT_REACHED,
    UNCLEAR_INSUFFICIENT_FEASIBLE_POSES,
    normalize_legacy_unclear_reason,
)
from crisp.scv.core import scv_anchoring, scv_offtarget
from crisp.staging.policy import scv_terminal_policy


def _config(*, confident_fail_threshold: int = 2):
    return SimpleNamespace(
        distance_threshold=2.2,
        anchoring=SimpleNamespace(epsilon=0.1),
        offtarget=SimpleNamespace(distance_threshold=2.2, epsilon=0.1),
        scv=SimpleNamespace(confident_fail_threshold=confident_fail_threshold),
        staging=SimpleNamespace(far_target_threshold=6.0),
    )


def test_scv_anchoring_uses_insufficient_feasible_pose_reason() -> None:
    verdict = scv_anchoring(
        SimpleNamespace(best_target_distance=3.0),
        SimpleNamespace(feasible_count=1),
        _config(confident_fail_threshold=2),
    )
    assert verdict.reason_or_meta == UNCLEAR_INSUFFICIENT_FEASIBLE_POSES


def test_scv_offtarget_uses_insufficient_feasible_pose_reason() -> None:
    verdict = scv_offtarget(
        SimpleNamespace(best_offtarget_distance=2.0),
        SimpleNamespace(feasible_count=1),
        _config(confident_fail_threshold=2),
    )
    assert verdict.reason_or_meta == UNCLEAR_INSUFFICIENT_FEASIBLE_POSES


def test_terminal_policy_uses_exploration_limit_reason() -> None:
    verdict, reason = scv_terminal_policy(
        v_core=Verdict.UNCLEAR,
        feasible_count=3,
        best_target_distance=3.2,
        config=_config(),
    )
    assert verdict == Verdict.UNCLEAR
    assert reason == UNCLEAR_EXPLORATION_LIMIT_REACHED


def test_normalize_legacy_unclear_reason_with_context() -> None:
    assert (
        normalize_legacy_unclear_reason(
            LEGACY_UNCLEAR_SAMPLING_BUDGET,
            feasible_count=0,
        ) == UNCLEAR_INSUFFICIENT_FEASIBLE_POSES
    )
    assert (
        normalize_legacy_unclear_reason(
            LEGACY_UNCLEAR_SAMPLING_BUDGET,
            feasible_count=4,
        ) == UNCLEAR_EXPLORATION_LIMIT_REACHED
    )
