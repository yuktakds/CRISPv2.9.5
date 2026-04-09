from __future__ import annotations

from dataclasses import asdict

from crisp.v3.contracts import ShadowStabilityCampaign, ShadowStabilityHistoryEntry
from crisp.v3.policy import SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION

SHADOW_STABILITY_CAMPAIGN_ARTIFACT = "shadow_stability_campaign.json"
SIDECAR_INVARIANT_HISTORY_ARTIFACT = "sidecar_invariant_history.json"
METRICS_DRIFT_HISTORY_ARTIFACT = "metrics_drift_history.json"
WINDOWS_STREAK_HISTORY_ARTIFACT = "windows_streak_history.json"


def _trim_history(entries: list[ShadowStabilityHistoryEntry], *, window_size: int) -> list[ShadowStabilityHistoryEntry]:
    return entries[-window_size:]


def build_shadow_stability_campaign(
    *,
    run_id: str,
    sidecar_invariant_history: list[bool],
    metrics_drift_history: list[int],
    windows_streak_history: list[bool],
    run_drift_report_digest_history: list[str],
    window_size: int = 30,
) -> ShadowStabilityCampaign:
    invariant_entries = _trim_history(
        [
            ShadowStabilityHistoryEntry(
                run_id=run_id,
                passed=bool(value),
                detail="sidecar invariant green",
                observed_value=bool(value),
            )
            for value in sidecar_invariant_history
        ],
        window_size=window_size,
    )
    metrics_entries = _trim_history(
        [
            ShadowStabilityHistoryEntry(
                run_id=run_id,
                passed=int(value) == 0,
                detail="metrics_drift must remain zero",
                observed_value=int(value),
            )
            for value in metrics_drift_history
        ],
        window_size=window_size,
    )
    windows_entries = _trim_history(
        [
            ShadowStabilityHistoryEntry(
                run_id=run_id,
                passed=bool(value),
                detail="Windows CI streak green",
                observed_value=bool(value),
            )
            for value in windows_streak_history
        ],
        window_size=window_size,
    )
    digest_history = run_drift_report_digest_history[-window_size:]
    digest_stable = bool(digest_history) and len(set(digest_history)) == 1
    sidecar_invariant_green = len(invariant_entries) >= window_size and all(entry.passed for entry in invariant_entries)
    metrics_drift_zero = len(metrics_entries) >= window_size and all(entry.passed for entry in metrics_entries)
    windows_streak_green = len(windows_entries) >= window_size and all(entry.passed for entry in windows_entries)
    return ShadowStabilityCampaign(
        schema_version=SHADOW_STABILITY_CAMPAIGN_SCHEMA_VERSION,
        run_id=run_id,
        required_window_size=window_size,
        sidecar_invariant_history=invariant_entries,
        metrics_drift_history=metrics_entries,
        windows_streak_history=windows_entries,
        run_drift_report_digest_history=digest_history,
        digest_stable=digest_stable,
        sidecar_invariant_green=sidecar_invariant_green,
        metrics_drift_zero=metrics_drift_zero,
        windows_streak_green=windows_streak_green,
        campaign_passed=(
            sidecar_invariant_green
            and metrics_drift_zero
            and windows_streak_green
            and digest_stable
        ),
    )


def shadow_stability_campaign_to_payload(campaign: ShadowStabilityCampaign) -> dict[str, object]:
    return asdict(campaign)
