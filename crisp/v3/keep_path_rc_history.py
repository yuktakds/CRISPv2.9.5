from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT = "keep_path_rc_history_report.json"
KEEP_PATH_RC_HISTORY_SUMMARY_ARTIFACT = "keep_path_rc_history_summary.md"


def _load_json_object(path: Path, *, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"{label}_READ_ERROR:{exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label}_JSON_DECODE_ERROR:{exc.msg}@line{exc.lineno}:col{exc.colno}"]
    if not isinstance(payload, dict):
        return None, [f"{label}_NOT_OBJECT:{type(payload).__name__}"]
    return payload, []


def _display_relative_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_zero(value: Any) -> bool:
    return value == 0 or value == 0.0


def _load_hosted_run_bundle(run_dir: Path) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    metadata, issues = _load_json_object(
        run_dir / "hosted_run_metadata.json",
        label="KEEP_PATH_RC_HOSTED_RUN_METADATA",
    )
    findings.extend(issues)
    gate_report, issues = _load_json_object(
        run_dir / "gate" / "rc_gate_keep_path_report.json",
        label="KEEP_PATH_RC_HOSTED_GATE_REPORT",
    )
    findings.extend(issues)
    campaign_index, issues = _load_json_object(
        run_dir / "campaign" / "campaign_index.json",
        label="KEEP_PATH_RC_HOSTED_CAMPAIGN_INDEX",
    )
    findings.extend(issues)
    smoke_report, issues = _load_json_object(
        run_dir / "release_packet" / "release_packet_smoke_report.json",
        label="KEEP_PATH_RC_HOSTED_SMOKE_REPORT",
    )
    findings.extend(issues)
    return {
        "metadata": metadata,
        "gate_report": gate_report,
        "campaign_index": campaign_index,
        "smoke_report": smoke_report,
    }, findings


def _extract_history_run(
    *,
    run_dir: Path,
    history_root: Path,
    bundle: Mapping[str, Any],
    findings: Sequence[str],
) -> dict[str, Any]:
    metadata = bundle.get("metadata") or {}
    gate_report = bundle.get("gate_report") or {}
    campaign_index = bundle.get("campaign_index") or {}
    smoke_report = bundle.get("smoke_report") or {}
    run_facts = gate_report.get("run_facts", {}) if isinstance(gate_report, Mapping) else {}
    campaign_aggregate = campaign_index.get("aggregate", {}) if isinstance(campaign_index, Mapping) else {}

    windows_hosted_success = (
        metadata.get("runner_os") == "Windows"
        and gate_report.get("gate_passed") is True
        and campaign_aggregate.get("campaign_passed") is True
        and smoke_report.get("smoke_passed") is True
    )
    return {
        "history_run": run_dir.name,
        "history_run_relative_path": _display_relative_path(run_dir, root=history_root),
        "workflow_name": metadata.get("workflow_name"),
        "workflow_path": metadata.get("workflow_path"),
        "runner_os": metadata.get("runner_os"),
        "runner_label": metadata.get("runner_label"),
        "exploratory_lane": metadata.get("exploratory_lane"),
        "required_matrix_touched": metadata.get("required_matrix_touched"),
        "public_scope_widening_authorized": metadata.get("public_scope_widening_authorized"),
        "required_promotion_authorized": metadata.get("required_promotion_authorized"),
        "gate_passed": bool(gate_report.get("gate_passed")),
        "campaign_passed": bool(campaign_aggregate.get("campaign_passed")),
        "smoke_passed": bool(smoke_report.get("smoke_passed")),
        "semantic_policy_version": run_facts.get("semantic_policy_version"),
        "path_component_match_rate": run_facts.get("path_component_match_rate"),
        "coverage_drift_count": run_facts.get("coverage_drift_count"),
        "applicability_drift_count": run_facts.get("applicability_drift_count"),
        "metrics_drift_count": run_facts.get("metrics_drift_count"),
        "exploratory_label_maintained": bool(run_facts.get("operator_surface_exploratory")),
        "output_inventory_unchanged": bool(run_facts.get("output_inventory_unchanged")),
        "windows_hosted_success": windows_hosted_success,
        "campaign_metric_contract_note": campaign_aggregate.get("metric_contract_note"),
        "findings": list(findings),
    }


def _aggregate_history_runs(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
    return {
        "observed_run_count": len(run_entries),
        "gate_pass_count": sum(1 for entry in run_entries if bool(entry.get("gate_passed"))),
        "campaign_pass_count": sum(1 for entry in run_entries if bool(entry.get("campaign_passed"))),
        "smoke_pass_count": sum(1 for entry in run_entries if bool(entry.get("smoke_passed"))),
        "all_gate_passed": all(bool(entry.get("gate_passed")) for entry in run_entries),
        "all_campaign_passed": all(bool(entry.get("campaign_passed")) for entry in run_entries),
        "all_smoke_passed": all(bool(entry.get("smoke_passed")) for entry in run_entries),
        "semantic_policy_versions": semantic_policy_versions,
        "same_semantic_policy_version": len(semantic_policy_versions) == 1,
        "path_component_match_rate_values": path_component_match_rate_values,
        "path_component_match_rate_min": min(path_component_match_rate_values) if path_component_match_rate_values else None,
        "path_component_match_rate_max": max(path_component_match_rate_values) if path_component_match_rate_values else None,
        "coverage_drift_zero_all_runs": all(_is_zero(entry.get("coverage_drift_count")) for entry in run_entries),
        "applicability_drift_zero_all_runs": all(
            _is_zero(entry.get("applicability_drift_count"))
            for entry in run_entries
        ),
        "metrics_drift_zero_all_runs": all(_is_zero(entry.get("metrics_drift_count")) for entry in run_entries),
        "exploratory_label_maintained_all_runs": all(
            bool(entry.get("exploratory_label_maintained"))
            for entry in run_entries
        ),
        "output_inventory_unchanged_all_runs": all(
            bool(entry.get("output_inventory_unchanged"))
            for entry in run_entries
        ),
        "windows_hosted_success_all_runs": all(
            bool(entry.get("windows_hosted_success"))
            for entry in run_entries
        ),
        "required_matrix_untouched_all_runs": all(
            entry.get("required_matrix_touched") is False
            for entry in run_entries
        ),
        "public_scope_widening_authorized_any_run": any(
            bool(entry.get("public_scope_widening_authorized"))
            for entry in run_entries
        ),
        "required_promotion_authorized_any_run": any(
            bool(entry.get("required_promotion_authorized"))
            for entry in run_entries
        ),
        "metric_contract_note": (
            "path_component_match_rate is a Path-only component metric. "
            "It is not a full verdict proxy and does not replace verdict_match_rate."
        ),
        "non_authorizing_statement": (
            "This history report is readiness evidence only. "
            "It does not authorize required promotion or public scope widening."
        ),
    }


def harvest_keep_path_rc_history(
    *,
    history_root: str | Path,
    run_glob: str = "hosted-run-*",
) -> dict[str, Any]:
    root = Path(history_root)
    run_dirs = sorted(
        [path for path in root.glob(run_glob) if path.is_dir()],
        key=lambda item: item.name,
    )
    entries: list[dict[str, Any]] = []
    history_findings: list[str] = []
    for run_dir in run_dirs:
        bundle, findings = _load_hosted_run_bundle(run_dir)
        entries.append(
            _extract_history_run(
                run_dir=run_dir,
                history_root=root,
                bundle=bundle,
                findings=findings,
            )
        )
        history_findings.extend(
            f"{run_dir.name}:{finding}"
            for finding in findings
        )

    aggregate = _aggregate_history_runs(entries)
    payload = {
        "schema_version": "crisp.v3.keep_path_rc_history/v1",
        "history_root": str(root.resolve()),
        "run_glob": run_glob,
        "runs": entries,
        "aggregate": aggregate,
        "findings": history_findings,
        "history_passed": (
            bool(entries)
            and not history_findings
            and aggregate["all_gate_passed"]
            and aggregate["all_campaign_passed"]
            and aggregate["all_smoke_passed"]
            and aggregate["same_semantic_policy_version"]
            and aggregate["coverage_drift_zero_all_runs"]
            and aggregate["applicability_drift_zero_all_runs"]
            and aggregate["metrics_drift_zero_all_runs"]
            and aggregate["exploratory_label_maintained_all_runs"]
            and aggregate["output_inventory_unchanged_all_runs"]
            and aggregate["windows_hosted_success_all_runs"]
            and aggregate["required_matrix_untouched_all_runs"]
            and not aggregate["public_scope_widening_authorized_any_run"]
            and not aggregate["required_promotion_authorized_any_run"]
        ),
    }
    return payload


def render_keep_path_rc_history_summary(payload: Mapping[str, Any]) -> str:
    aggregate = payload.get("aggregate", {})
    semantic_policy_versions = aggregate.get("semantic_policy_versions", [])
    path_component_match_rate_values = aggregate.get("path_component_match_rate_values", [])
    lines = [
        "# Keep-Path RC Hosted History Summary",
        "",
        f"- history_passed: `{str(bool(payload.get('history_passed'))).lower()}`",
        f"- observed_run_count: `{aggregate.get('observed_run_count', 0)}`",
        f"- gate_pass_count: `{aggregate.get('gate_pass_count', 0)}`",
        f"- campaign_pass_count: `{aggregate.get('campaign_pass_count', 0)}`",
        f"- smoke_pass_count: `{aggregate.get('smoke_pass_count', 0)}`",
        f"- semantic_policy_versions: `{', '.join(str(item) for item in semantic_policy_versions) or 'none'}`",
        f"- path_component_match_rate_values: `{', '.join(str(item) for item in path_component_match_rate_values) or 'none'}`",
        f"- coverage_drift_zero_all_runs: `{str(bool(aggregate.get('coverage_drift_zero_all_runs'))).lower()}`",
        f"- applicability_drift_zero_all_runs: `{str(bool(aggregate.get('applicability_drift_zero_all_runs'))).lower()}`",
        f"- metrics_drift_zero_all_runs: `{str(bool(aggregate.get('metrics_drift_zero_all_runs'))).lower()}`",
        f"- exploratory_label_maintained_all_runs: `{str(bool(aggregate.get('exploratory_label_maintained_all_runs'))).lower()}`",
        f"- output_inventory_unchanged_all_runs: `{str(bool(aggregate.get('output_inventory_unchanged_all_runs'))).lower()}`",
        f"- windows_hosted_success_all_runs: `{str(bool(aggregate.get('windows_hosted_success_all_runs'))).lower()}`",
        "",
        "This is non-authorizing readiness evidence only.",
        "It does not authorize required promotion or public scope widening.",
        "path_component_match_rate remains a Path-only component metric and is not a full verdict proxy.",
    ]
    return "\n".join(lines) + "\n"


def write_keep_path_rc_history_report(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / KEEP_PATH_RC_HISTORY_REPORT_ARTIFACT
    report_path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path


def write_keep_path_rc_history_summary(
    *,
    output_dir: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_path = output_path / KEEP_PATH_RC_HISTORY_SUMMARY_ARTIFACT
    summary_path.write_text(
        render_keep_path_rc_history_summary(payload),
        encoding="utf-8",
    )
    return summary_path
