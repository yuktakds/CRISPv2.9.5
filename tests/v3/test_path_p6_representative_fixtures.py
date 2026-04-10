from __future__ import annotations

import json
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "path_p6_representative"


def _load_case(case_name: str) -> tuple[dict[str, object], dict[str, object], str]:
    case_dir = FIXTURE_ROOT / case_name
    summary = json.loads((case_dir / "bridge_comparison_summary.json").read_text(encoding="utf-8"))
    run_record = json.loads((case_dir / "sidecar_run_record.json").read_text(encoding="utf-8"))
    operator_summary = (case_dir / "bridge_operator_summary.md").read_text(encoding="utf-8")
    return summary, run_record, operator_summary


def test_path_p6_representative_fixtures_keep_path_only_comparable_surface() -> None:
    for case_name in ("path_only_supported", "path_cap_catalytic_materialized"):
        summary, run_record, operator_summary = _load_case(case_name)
        summary_text = json.dumps(summary, sort_keys=True)

        assert summary["comparable_channels"] == ["path"]
        assert run_record["comparable_channels"] == ["path"]
        assert "channel_lifecycle_states" in run_record
        assert "v3_shadow_verdict" not in summary_text
        assert (
            run_record.get("bridge_diagnostics", {})
            .get("layer0_authority_mirror", {})
            .get("v3_shadow_verdict")
            is None
        )
        assert "\"verdict_match\": " not in summary_text
        assert "verdict_match_rate: `N/A`" in operator_summary
        assert "verdict_match_rate: `1/" not in operator_summary
        assert "verdict_match_rate: `0/" not in operator_summary


def test_path_p6_fixture_with_materialized_cap_and_catalytic_uses_comparable_subset_denominator() -> None:
    summary, run_record, operator_summary = _load_case("path_cap_catalytic_materialized")

    assert run_record["observation_count"] == 3
    assert run_record["enabled_channels"] == ["path", "cap", "catalytic"]
    assert summary["run_drift_report"]["comparable_subset_size"] == 1
    assert summary["run_drift_report"]["component_verdict_comparable_count"] == 1
    assert summary["run_drift_report"]["component_match_count"] == 1
    assert summary["run_drift_report"]["path_component_match_rate"] == 1.0
    assert run_record["channel_comparability"] == {
        "path": "component_verdict_comparable",
        "cap": None,
        "catalytic": None,
    }
    assert run_record["v3_only_evidence_channels"] == ["cap", "catalytic"]
    assert run_record["channel_lifecycle_states"] == {
        "path": "observation_materialized",
        "cap": "observation_materialized",
        "catalytic": "observation_materialized",
    }
    assert "path_component_match_rate: `1/1 (100.0%)`" in operator_summary
    assert "comparable_subset_size: `1`" in operator_summary
    assert "[v3-only] cap: `observation_materialized`" in operator_summary
