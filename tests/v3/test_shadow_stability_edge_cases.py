from __future__ import annotations

from crisp.v3.shadow_stability import build_shadow_stability_campaign


def _green_campaign(window_size: int = 30) -> object:
    return build_shadow_stability_campaign(
        run_id="run-test",
        sidecar_invariant_history=[True] * window_size,
        metrics_drift_history=[0] * window_size,
        windows_streak_history=[True] * window_size,
        run_drift_report_digest_history=["abc123"] * window_size,
        window_size=window_size,
    )


# ---------------------------------------------------------------------------
# Empty history — all gates must be False; campaign must not pass
# ---------------------------------------------------------------------------


def test_empty_history_campaign_does_not_pass() -> None:
    campaign = build_shadow_stability_campaign(
        run_id="run-empty",
        sidecar_invariant_history=[],
        metrics_drift_history=[],
        windows_streak_history=[],
        run_drift_report_digest_history=[],
    )

    assert campaign.campaign_passed is False
    assert campaign.sidecar_invariant_green is False
    assert campaign.metrics_drift_zero is False
    assert campaign.windows_streak_green is False
    assert campaign.digest_stable is False


# ---------------------------------------------------------------------------
# Under-full window — 29 entries with window_size=30
# ---------------------------------------------------------------------------


def test_under_full_window_campaign_does_not_pass() -> None:
    campaign = build_shadow_stability_campaign(
        run_id="run-29",
        sidecar_invariant_history=[True] * 29,
        metrics_drift_history=[0] * 29,
        windows_streak_history=[True] * 29,
        run_drift_report_digest_history=["abc123"] * 29,
        window_size=30,
    )

    assert campaign.campaign_passed is False
    assert campaign.sidecar_invariant_green is False
    assert campaign.metrics_drift_zero is False
    assert campaign.windows_streak_green is False


# ---------------------------------------------------------------------------
# Exactly full window — 30 green entries
# ---------------------------------------------------------------------------


def test_full_green_window_campaign_passes() -> None:
    campaign = _green_campaign(window_size=30)

    assert campaign.campaign_passed is True
    assert campaign.sidecar_invariant_green is True
    assert campaign.metrics_drift_zero is True
    assert campaign.windows_streak_green is True
    assert campaign.digest_stable is True
    assert len(campaign.sidecar_invariant_history) == 30
    assert len(campaign.metrics_drift_history) == 30
    assert len(campaign.windows_streak_history) == 30


# ---------------------------------------------------------------------------
# Over-full input — window_size trims to last N entries
# ---------------------------------------------------------------------------


def test_over_full_input_trims_to_window() -> None:
    # 35 entries provided; only the last 30 should be kept
    invariant_history = [False] * 5 + [True] * 30
    drift_history = [1] * 5 + [0] * 30
    streak_history = [False] * 5 + [True] * 30
    digest_history = ["stale"] * 5 + ["stable_digest"] * 30

    campaign = build_shadow_stability_campaign(
        run_id="run-35",
        sidecar_invariant_history=invariant_history,
        metrics_drift_history=drift_history,
        windows_streak_history=streak_history,
        run_drift_report_digest_history=digest_history,
        window_size=30,
    )

    assert len(campaign.sidecar_invariant_history) == 30
    assert len(campaign.metrics_drift_history) == 30
    assert len(campaign.windows_streak_history) == 30
    assert len(campaign.run_drift_report_digest_history) == 30
    # The trimmed window is all green
    assert campaign.campaign_passed is True
    assert campaign.sidecar_invariant_green is True


# ---------------------------------------------------------------------------
# Single failing entry resets gate
# ---------------------------------------------------------------------------


def test_one_failed_invariant_fails_sidecar_green() -> None:
    invariant_history = [True] * 29 + [False]

    campaign = build_shadow_stability_campaign(
        run_id="run-fail-invariant",
        sidecar_invariant_history=invariant_history,
        metrics_drift_history=[0] * 30,
        windows_streak_history=[True] * 30,
        run_drift_report_digest_history=["digest"] * 30,
        window_size=30,
    )

    assert campaign.sidecar_invariant_green is False
    assert campaign.campaign_passed is False


def test_one_nonzero_drift_fails_metrics_zero() -> None:
    drift_history = [0] * 29 + [1]

    campaign = build_shadow_stability_campaign(
        run_id="run-fail-drift",
        sidecar_invariant_history=[True] * 30,
        metrics_drift_history=drift_history,
        windows_streak_history=[True] * 30,
        run_drift_report_digest_history=["digest"] * 30,
        window_size=30,
    )

    assert campaign.metrics_drift_zero is False
    assert campaign.campaign_passed is False


def test_mixed_digests_fails_digest_stable() -> None:
    digest_history = ["digest_a"] * 29 + ["digest_b"]

    campaign = build_shadow_stability_campaign(
        run_id="run-fail-digest",
        sidecar_invariant_history=[True] * 30,
        metrics_drift_history=[0] * 30,
        windows_streak_history=[True] * 30,
        run_drift_report_digest_history=digest_history,
        window_size=30,
    )

    assert campaign.digest_stable is False
    assert campaign.campaign_passed is False


# ---------------------------------------------------------------------------
# Schema fields are present
# ---------------------------------------------------------------------------


def test_campaign_records_window_size() -> None:
    campaign = _green_campaign(window_size=30)
    assert campaign.required_window_size == 30


def test_campaign_records_run_id() -> None:
    campaign = build_shadow_stability_campaign(
        run_id="test-run-id",
        sidecar_invariant_history=[True] * 30,
        metrics_drift_history=[0] * 30,
        windows_streak_history=[True] * 30,
        run_drift_report_digest_history=["d"] * 30,
    )
    assert campaign.run_id == "test-run-id"
