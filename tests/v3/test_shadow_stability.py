from __future__ import annotations

from crisp.v3.policy import SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION
from crisp.v3.shadow_stability import (
    METRICS_DRIFT_HISTORY_ARTIFACT,
    SHADOW_STABILITY_CAMPAIGN_ARTIFACT,
    SIDECAR_INVARIANT_HISTORY_ARTIFACT,
    WINDOWS_STREAK_HISTORY_ARTIFACT,
    build_shadow_stability_campaign,
    shadow_stability_campaign_to_payload,
)

WINDOW = 3


def _passing_campaign(window_size: int = WINDOW) -> dict[str, object]:
    return dict(
        run_id="run-001",
        sidecar_invariant_history=[True] * window_size,
        metrics_drift_history=[0] * window_size,
        windows_streak_history=[True] * window_size,
        run_drift_report_digest_history=["abc123"] * window_size,
        window_size=window_size,
    )


# ---------------------------------------------------------------------------
# Artifact name constants
# ---------------------------------------------------------------------------


def test_artifact_name_constants_are_stable() -> None:
    assert SHADOW_STABILITY_CAMPAIGN_ARTIFACT == "shadow_stability_campaign.json"
    assert SIDECAR_INVARIANT_HISTORY_ARTIFACT == "sidecar_invariant_history.json"
    assert METRICS_DRIFT_HISTORY_ARTIFACT == "metrics_drift_history.json"
    assert WINDOWS_STREAK_HISTORY_ARTIFACT == "windows_streak_history.json"


# ---------------------------------------------------------------------------
# campaign_passed — all-green path
# ---------------------------------------------------------------------------


def test_campaign_passed_when_all_histories_satisfy_window() -> None:
    campaign = build_shadow_stability_campaign(**_passing_campaign())  # type: ignore[arg-type]

    assert campaign.campaign_passed is True
    assert campaign.sidecar_invariant_green is True
    assert campaign.metrics_drift_zero is True
    assert campaign.windows_streak_green is True
    assert campaign.digest_stable is True


def test_campaign_schema_version_matches_policy() -> None:
    campaign = build_shadow_stability_campaign(**_passing_campaign())  # type: ignore[arg-type]

    assert campaign.schema_version == SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# campaign_passed = False — insufficient history
# ---------------------------------------------------------------------------


def test_campaign_fails_when_history_shorter_than_window() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["sidecar_invariant_history"] = [True] * (WINDOW - 1)  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.sidecar_invariant_green is False
    assert campaign.campaign_passed is False


def test_campaign_fails_when_metrics_history_shorter_than_window() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["metrics_drift_history"] = [0] * (WINDOW - 1)  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.metrics_drift_zero is False
    assert campaign.campaign_passed is False


def test_campaign_fails_when_windows_history_shorter_than_window() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["windows_streak_history"] = [True] * (WINDOW - 1)  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.windows_streak_green is False
    assert campaign.campaign_passed is False


# ---------------------------------------------------------------------------
# campaign_passed = False — single failure in window
# ---------------------------------------------------------------------------


def test_campaign_fails_on_single_sidecar_invariant_failure() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["sidecar_invariant_history"] = [True, False, True]  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.sidecar_invariant_green is False
    assert campaign.campaign_passed is False


def test_campaign_fails_on_nonzero_metrics_drift() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["metrics_drift_history"] = [0, 1, 0]  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.metrics_drift_zero is False
    assert campaign.campaign_passed is False


def test_campaign_fails_on_single_windows_streak_failure() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["windows_streak_history"] = [True, True, False]  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.windows_streak_green is False
    assert campaign.campaign_passed is False


# ---------------------------------------------------------------------------
# digest_stable
# ---------------------------------------------------------------------------


def test_digest_stable_false_when_digests_differ() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["run_drift_report_digest_history"] = ["aaa", "bbb", "aaa"]  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.digest_stable is False
    assert campaign.campaign_passed is False


def test_digest_stable_false_when_digest_history_empty() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["run_drift_report_digest_history"] = []  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.digest_stable is False
    assert campaign.campaign_passed is False


# ---------------------------------------------------------------------------
# Window trimming
# ---------------------------------------------------------------------------


def test_history_trimmed_to_window_size() -> None:
    excess = WINDOW + 2
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["sidecar_invariant_history"] = [False] * 2 + [True] * WINDOW  # type: ignore[index]
    assert len(kwargs["sidecar_invariant_history"]) == excess  # type: ignore[arg-type]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert len(campaign.sidecar_invariant_history) == WINDOW
    assert campaign.sidecar_invariant_green is True


def test_digest_trimmed_to_window_size() -> None:
    kwargs = _passing_campaign(window_size=WINDOW)
    kwargs["run_drift_report_digest_history"] = ["old"] * 2 + ["new"] * WINDOW  # type: ignore[index]
    campaign = build_shadow_stability_campaign(**kwargs)  # type: ignore[arg-type]

    assert campaign.run_drift_report_digest_history == ["new"] * WINDOW
    assert campaign.digest_stable is True


# ---------------------------------------------------------------------------
# shadow_stability_campaign_to_payload
# ---------------------------------------------------------------------------


def test_to_payload_returns_plain_dict() -> None:
    campaign = build_shadow_stability_campaign(**_passing_campaign())  # type: ignore[arg-type]
    payload = shadow_stability_campaign_to_payload(campaign)

    assert isinstance(payload, dict)
    assert payload["run_id"] == "run-001"
    assert payload["campaign_passed"] is True
    assert payload["schema_version"] == SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION


def test_to_payload_includes_all_history_lists() -> None:
    campaign = build_shadow_stability_campaign(**_passing_campaign())  # type: ignore[arg-type]
    payload = shadow_stability_campaign_to_payload(campaign)

    assert isinstance(payload["sidecar_invariant_history"], list)
    assert isinstance(payload["metrics_drift_history"], list)
    assert isinstance(payload["windows_streak_history"], list)
    assert isinstance(payload["run_drift_report_digest_history"], list)
