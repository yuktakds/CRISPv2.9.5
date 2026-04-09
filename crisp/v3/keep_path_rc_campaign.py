from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from crisp.v3.keep_path_rc_gate import (
    RC_GATE_KEEP_PATH_REPORT_ARTIFACT,
    evaluate_keep_path_rc_gate,
    write_keep_path_rc_gate_report,
)

KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT = "campaign_index.json"
KEEP_PATH_RC_CAMPAIGN_RUNS_DIRNAME = "campaign_runs"


def _display_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_zero(value: Any) -> bool:
    return value == 0 or value == 0.0


def _build_run_entry(
    *,
    run_name: str,
    report_path: Path,
    output_root: Path,
    gate_payload: Mapping[str, Any],
) -> dict[str, Any]:
    run_facts = gate_payload.get("run_facts", {})
    ops_bundle = gate_payload.get("ops_bundle", {})
    rollback = ops_bundle.get("rollback", {}) if isinstance(ops_bundle, Mapping) else {}
    rehearsal = ops_bundle.get("rehearsal", {}) if isinstance(ops_bundle, Mapping) else {}
    monitoring = ops_bundle.get("monitoring", {}) if isinstance(ops_bundle, Mapping) else {}

    gate_conditions = {
        "comparator_scope_path_only_partial": run_facts.get("comparator_scope") == "path_only_partial",
        "comparable_channels_path_only": run_facts.get("comparable_channels") == ["path"],
        "v3_shadow_verdict_inactive": bool(run_facts.get("v3_shadow_verdict_inactive")),
        "numeric_verdict_match_rate_absent": bool(run_facts.get("numeric_verdict_match_rate_absent")),
        "operator_surface_exploratory": bool(run_facts.get("operator_surface_exploratory")),
        "operator_surface_semantic_policy_version_present": bool(
            run_facts.get("operator_surface_semantic_policy_version_present")
        ),
        "operator_surface_verdict_match_rate_na": bool(
            run_facts.get("operator_surface_verdict_match_rate_na")
        ),
        "output_inventory_unchanged": bool(run_facts.get("output_inventory_unchanged")),
        "rollback_report_passed": rollback.get("drill_passed") is True,
        "rehearsal_report_passed": rehearsal.get("rehearsal_passed") is True,
        "monitoring_report_passed": monitoring.get("window_passed") is True,
    }
    return {
        "run_name": run_name,
        "run_dir": gate_payload.get("run_dir"),
        "report_relative_path": _display_relative_path(report_path, root=output_root),
        "gate_passed": bool(gate_payload.get("gate_passed")),
        "findings": list(gate_payload.get("findings", [])),
        "semantic_policy_version": run_facts.get("semantic_policy_version"),
        "comparator_scope": run_facts.get("comparator_scope"),
        "comparable_channels": list(run_facts.get("comparable_channels", [])),
        "path_component_match_rate": run_facts.get("path_component_match_rate"),
        "coverage_drift_count": run_facts.get("coverage_drift_count"),
        "applicability_drift_count": run_facts.get("applicability_drift_count"),
        "metrics_drift_count": run_facts.get("metrics_drift_count"),
        "gate_conditions": gate_conditions,
    }


def _aggregate_campaign(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    run_entries = list(entries)
    semantic_policy_versions = sorted(
        {
            str(entry.get("semantic_policy_version"))
            for entry in run_entries
            if entry.get("semantic_policy_version")
        }
    )
    path_component_match_rate_values = sorted(
        {
            float(entry.get("path_component_match_rate"))
            for entry in run_entries
            if isinstance(entry.get("path_component_match_rate"), int | float)
            and not isinstance(entry.get("path_component_match_rate"), bool)
        }
    )
    gate_condition_names = (
        "comparator_scope_path_only_partial",
        "comparable_channels_path_only",
        "v3_shadow_verdict_inactive",
        "numeric_verdict_match_rate_absent",
        "operator_surface_exploratory",
        "operator_surface_semantic_policy_version_present",
        "operator_surface_verdict_match_rate_na",
        "output_inventory_unchanged",
        "rollback_report_passed",
        "rehearsal_report_passed",
        "monitoring_report_passed",
    )
    aggregate = {
        "run_count": len(run_entries),
        "gate_pass_count": sum(1 for entry in run_entries if bool(entry.get("gate_passed"))),
        "gate_failed_count": sum(1 for entry in run_entries if not bool(entry.get("gate_passed"))),
        "semantic_policy_versions": semantic_policy_versions,
        "same_semantic_policy_version": len(semantic_policy_versions) == 1,
        "path_component_match_rate_values": path_component_match_rate_values,
        "path_component_match_rate_min": min(path_component_match_rate_values) if path_component_match_rate_values else None,
        "path_component_match_rate_max": max(path_component_match_rate_values) if path_component_match_rate_values else None,
        "coverage_drift_zero_all_runs": all(_is_zero(entry.get("coverage_drift_count")) for entry in run_entries),
        "applicability_drift_zero_all_runs": all(
            _is_zero(entry.get("applicability_drift_count")) for entry in run_entries
        ),
        "metrics_drift_zero_all_runs": all(_is_zero(entry.get("metrics_drift_count")) for entry in run_entries),
        "metric_contract_note": (
            "path_component_match_rate is a Path-only metric. "
            "It is not a full verdict proxy and does not replace verdict_match_rate."
        ),
    }
    for condition_name in gate_condition_names:
        aggregate[f"{condition_name}_all_runs"] = all(
            bool(entry.get("gate_conditions", {}).get(condition_name))
            for entry in run_entries
        )
    aggregate["campaign_passed"] = (
        bool(run_entries)
        and aggregate["gate_failed_count"] == 0
        and aggregate["same_semantic_policy_version"]
        and aggregate["coverage_drift_zero_all_runs"]
        and aggregate["applicability_drift_zero_all_runs"]
        and aggregate["metrics_drift_zero_all_runs"]
        and all(
            aggregate[f"{condition_name}_all_runs"]
            for condition_name in gate_condition_names
        )
    )
    return aggregate


def materialize_keep_path_rc_campaign(
    *,
    run_dirs: Sequence[str | Path],
    docs_root: str | Path,
    evidence_dir: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    docs_path = Path(docs_root)
    evidence_path = Path(evidence_dir)
    output_path = Path(output_dir) if output_dir is not None else evidence_path
    output_path.mkdir(parents=True, exist_ok=True)
    run_reports_root = output_path / KEEP_PATH_RC_CAMPAIGN_RUNS_DIRNAME

    entries: list[dict[str, Any]] = []
    run_paths = sorted((Path(run_dir) for run_dir in run_dirs), key=lambda item: item.name)
    for run_path in run_paths:
        run_output_dir = run_reports_root / run_path.name
        gate_payload = evaluate_keep_path_rc_gate(
            run_dir=run_path,
            docs_root=docs_path,
            evidence_dir=evidence_path,
        )
        report_path = write_keep_path_rc_gate_report(
            output_dir=run_output_dir,
            payload=gate_payload,
        )
        entries.append(
            _build_run_entry(
                run_name=run_path.name,
                report_path=report_path,
                output_root=output_path,
                gate_payload=gate_payload,
            )
        )

    payload = {
        "schema_version": "crisp.v3.keep_path_rc_campaign/v1",
        "docs_root": str(docs_path.resolve()),
        "evidence_dir": str(evidence_path.resolve()),
        "output_dir": str(output_path.resolve()),
        "run_reports_dir": _display_relative_path(run_reports_root, root=output_path),
        "runs": entries,
        "aggregate": _aggregate_campaign(entries),
    }
    return payload


def write_keep_path_rc_campaign_index(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    index_path = output_path / KEEP_PATH_RC_CAMPAIGN_INDEX_ARTIFACT
    index_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return index_path
