from __future__ import annotations

import pytest

from crisp.v3.report_guards import ReportGuardError, enforce_shadow_stability_campaign_guard


def _passing_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "required_window_size": 30,
        "campaign_passed": True,
        "sidecar_invariant_green": True,
        "metrics_drift_zero": True,
        "windows_streak_green": True,
        "digest_stable": True,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# valid payloads — must not raise
# ---------------------------------------------------------------------------


def test_valid_passing_campaign_does_not_raise() -> None:
    enforce_shadow_stability_campaign_guard(payload=_passing_payload())


def test_campaign_not_passed_does_not_raise_even_with_false_sub_fields() -> None:
    # campaign_passed=False → sub-field checks are skipped
    enforce_shadow_stability_campaign_guard(
        payload=_passing_payload(
            campaign_passed=False,
            sidecar_invariant_green=False,
            metrics_drift_zero=False,
        )
    )


# ---------------------------------------------------------------------------
# window_size violations
# ---------------------------------------------------------------------------


def test_raises_when_window_size_is_not_30() -> None:
    with pytest.raises(ReportGuardError, match="30-run window"):
        enforce_shadow_stability_campaign_guard(payload=_passing_payload(required_window_size=20))


def test_raises_when_window_size_is_missing() -> None:
    payload = dict(_passing_payload())
    del payload["required_window_size"]
    with pytest.raises(ReportGuardError, match="30-run window"):
        enforce_shadow_stability_campaign_guard(payload=payload)


# ---------------------------------------------------------------------------
# sub-field violations when campaign_passed=True
# ---------------------------------------------------------------------------


def test_raises_when_sidecar_invariant_green_is_false() -> None:
    with pytest.raises(ReportGuardError, match="sidecar_invariant_green"):
        enforce_shadow_stability_campaign_guard(
            payload=_passing_payload(sidecar_invariant_green=False)
        )


def test_raises_when_metrics_drift_zero_is_false() -> None:
    with pytest.raises(ReportGuardError, match="metrics_drift_zero"):
        enforce_shadow_stability_campaign_guard(
            payload=_passing_payload(metrics_drift_zero=False)
        )


def test_raises_when_windows_streak_green_is_false() -> None:
    with pytest.raises(ReportGuardError, match="windows_streak_green"):
        enforce_shadow_stability_campaign_guard(
            payload=_passing_payload(windows_streak_green=False)
        )


def test_raises_when_digest_stable_is_false() -> None:
    with pytest.raises(ReportGuardError, match="digest_stable"):
        enforce_shadow_stability_campaign_guard(
            payload=_passing_payload(digest_stable=False)
        )
