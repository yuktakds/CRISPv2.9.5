from __future__ import annotations

from crisp.v29.cli import _required_outputs_for_mode


def test_required_outputs_for_cap_mode_include_cap_reports() -> None:
    required = _required_outputs_for_mode("core+rule1+cap")
    assert "cap_batch_eval.json" in required
    assert "qc_report.json" in required
    assert "eval_report.json" in required
    assert "collapse_figure_spec.json" in required


def test_required_outputs_for_full_mode_include_validation_reports() -> None:
    required = _required_outputs_for_mode("full")
    assert "mapping_table.parquet" in required
    assert "falsification_table.parquet" in required
    assert "cap_batch_eval.json" in required
    assert "qc_report.json" in required
    assert "eval_report.json" in required
    assert "collapse_figure_spec.json" in required
