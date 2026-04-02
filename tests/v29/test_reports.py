from __future__ import annotations

from pathlib import Path
import json

from crisp.v29.contracts import Layer2Result
from crisp.v29.reports import build_collapse_figure_spec, build_eval_report, build_qc_report, run_replay_audit
from crisp.v29.writers import write_collapse_figure_spec, write_eval_report, write_qc_report, write_integrated_manifest
from crisp.v29.contracts import IntegratedRunManifest


def test_reports_build_and_write(tmp_path: Path) -> None:
    qc = build_qc_report(run_id='r1', conditions_run=['native'], excluded_rows_count=0, warnings=[], result='PASS')
    er = build_eval_report(run_id='r1', cap_batch_eval_path='cap_batch_eval.json', layer2_result=None)
    cf = build_collapse_figure_spec(run_id='r1', resource_profile='smoke', conditions=['native'], cap_metrics={})
    write_qc_report(tmp_path / 'qc_report.json', qc)
    write_eval_report(tmp_path / 'eval_report.json', er)
    write_collapse_figure_spec(tmp_path / 'collapse_figure_spec.json', cf)
    assert json.loads((tmp_path / 'qc_report.json').read_text(encoding='utf-8'))['run_id'] == 'r1'
    assert json.loads((tmp_path / 'eval_report.json').read_text(encoding='utf-8'))['run_id'] == 'r1'
    assert json.loads((tmp_path / 'collapse_figure_spec.json').read_text(encoding='utf-8'))['run_id'] == 'r1'
