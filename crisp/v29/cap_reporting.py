from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crisp.v29.contracts import Layer2Result
from crisp.v29.reports import build_collapse_figure_spec, build_eval_report, build_qc_report
from crisp.v29.validators import (
    validate_cap_truth_source_reconciliation,
    validate_eval_report_no_verdict,
)
from crisp.v29.writers import (
    write_collapse_figure_spec,
    write_eval_report,
    write_qc_report,
)


@dataclass(frozen=True, slots=True)
class CapReportBundle:
    eval_report: dict[str, Any]
    qc_report: dict[str, Any]
    collapse_figure_spec: dict[str, Any]


def build_cap_report_bundle(
    *,
    run_id: str,
    cap_batch_eval_path: str | None,
    cap_truth_source_provenance: dict[str, Any] | None,
    layer2_result: Layer2Result | None,
    comparison_type: str | None,
    comparison_type_source: str | None,
    skip_reason_codes: list[str],
    inventory_json_errors: list[dict[str, Any]] | list[Any],
    pathyes_metadata: dict[str, Any],
    eval_notes: list[str],
    qc_conditions_run: list[str],
    qc_excluded_rows_count: int,
    qc_warnings: list[str],
    qc_result: str,
    qc_extra: dict[str, Any] | None,
    resource_profile: str,
    collapse_conditions: list[str],
    collapse_cap_metrics: dict[str, Any],
) -> CapReportBundle:
    eval_report = build_eval_report(
        run_id=run_id,
        cap_batch_eval_path=cap_batch_eval_path,
        layer2_result=layer2_result,
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
        cap_truth_source_provenance=cap_truth_source_provenance,
        notes=eval_notes,
        **pathyes_metadata,
    )
    qc_report = build_qc_report(
        run_id=run_id,
        conditions_run=qc_conditions_run,
        excluded_rows_count=qc_excluded_rows_count,
        warnings=qc_warnings,
        result=qc_result,
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
        cap_truth_source_provenance=cap_truth_source_provenance,
        extra=qc_extra,
        **pathyes_metadata,
    )
    collapse_figure_spec = build_collapse_figure_spec(
        run_id=run_id,
        resource_profile=resource_profile,
        conditions=collapse_conditions,
        cap_metrics=collapse_cap_metrics,
        comparison_type=comparison_type,
        comparison_type_source=comparison_type_source,
        skip_reason_codes=skip_reason_codes,
        inventory_json_errors=inventory_json_errors,
        cap_truth_source_provenance=cap_truth_source_provenance,
        **pathyes_metadata,
    )
    return CapReportBundle(
        eval_report=eval_report,
        qc_report=qc_report,
        collapse_figure_spec=collapse_figure_spec,
    )


def validate_cap_report_bundle(
    bundle: CapReportBundle,
    *,
    cap_batch_eval_source: str | Path | dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    eval_errors, eval_warnings = validate_eval_report_no_verdict(bundle.eval_report)
    errors.extend(eval_errors)
    warnings.extend(eval_warnings)
    truth_errors, truth_warnings = validate_cap_truth_source_reconciliation(
        cap_batch_eval_source=cap_batch_eval_source,
        eval_report_source=bundle.eval_report,
        qc_report_source=bundle.qc_report,
        collapse_figure_spec_source=bundle.collapse_figure_spec,
    )
    errors.extend(truth_errors)
    warnings.extend(truth_warnings)
    return sorted(set(errors)), sorted(set(warnings))


def write_cap_report_bundle(
    out_dir: str | Path,
    bundle: CapReportBundle,
) -> dict[str, Path]:
    out_path = Path(out_dir)
    return {
        "eval_report.json": write_eval_report(out_path / "eval_report.json", bundle.eval_report),
        "qc_report.json": write_qc_report(out_path / "qc_report.json", bundle.qc_report),
        "collapse_figure_spec.json": write_collapse_figure_spec(
            out_path / "collapse_figure_spec.json",
            bundle.collapse_figure_spec,
        ),
    }
