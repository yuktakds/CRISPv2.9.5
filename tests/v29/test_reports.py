from __future__ import annotations

from pathlib import Path
import json

from crisp.v3.readiness.consistency import build_inventory_authority_payload
from crisp.v29.cap_truth import build_cap_truth_source_provenance
from crisp.v29.contracts import Layer2Result
from crisp.v29.reports import build_collapse_figure_spec, build_eval_report, build_qc_report, run_replay_audit
from crisp.v29.writers import write_collapse_figure_spec, write_eval_report, write_qc_report, write_integrated_manifest
from crisp.v29.contracts import IntegratedRunManifest


def test_reports_build_and_write(tmp_path: Path) -> None:
    provenance = build_cap_truth_source_provenance({
        'run_id': 'r1',
        'status': 'OK',
        'source_of_truth': True,
        'diagnostics_json': {},
        'reason_codes': [],
        'cap_batch_verdict': 'PASS',
        'cap_batch_reason_code': None,
        'verdict_layer0': 'PASS',
        'verdict_layer1': 'PASS',
        'verdict_layer2': None,
        'verdict_final': 'PASS',
    })
    qc = build_qc_report(
        run_id='r1',
        conditions_run=['native'],
        excluded_rows_count=0,
        warnings=[],
        result='PASS',
        comparison_type='cross-regime',
        comparison_type_source='explicit_override',
        skip_reason_codes=['SKIP_EXAMPLE'],
        inventory_json_errors=[],
        cap_truth_source_provenance=provenance,
    )
    er = build_eval_report(
        run_id='r1',
        cap_batch_eval_path='cap_batch_eval.json',
        layer2_result=None,
        comparison_type='cross-regime',
        comparison_type_source='explicit_override',
        skip_reason_codes=['SKIP_EXAMPLE'],
        inventory_json_errors=[],
        cap_truth_source_provenance=provenance,
    )
    cf = build_collapse_figure_spec(
        run_id='r1',
        resource_profile='smoke',
        conditions=['native'],
        cap_metrics={},
        comparison_type='cross-regime',
        comparison_type_source='explicit_override',
        skip_reason_codes=['SKIP_EXAMPLE'],
        inventory_json_errors=[],
        cap_truth_source_provenance=provenance,
    )
    write_qc_report(tmp_path / 'qc_report.json', qc)
    write_eval_report(tmp_path / 'eval_report.json', er)
    write_collapse_figure_spec(tmp_path / 'collapse_figure_spec.json', cf)
    qc_payload = json.loads((tmp_path / 'qc_report.json').read_text(encoding='utf-8'))
    eval_payload = json.loads((tmp_path / 'eval_report.json').read_text(encoding='utf-8'))
    collapse_payload = json.loads((tmp_path / 'collapse_figure_spec.json').read_text(encoding='utf-8'))
    assert qc_payload['run_id'] == 'r1'
    assert qc_payload['comparison_type'] == 'cross-regime'
    assert qc_payload['comparison_type_source'] == 'explicit_override'
    assert qc_payload['skip_reason_codes'] == ['SKIP_EXAMPLE']
    assert qc_payload['inventory_json_errors'] == []
    assert qc_payload['cap_truth_source_status'] == 'verified'
    assert eval_payload['run_id'] == 'r1'
    assert eval_payload['comparison_type'] == 'cross-regime'
    assert eval_payload['comparison_type_source'] == 'explicit_override'
    assert eval_payload['skip_reason_codes'] == ['SKIP_EXAMPLE']
    assert eval_payload['inventory_json_errors'] == []
    assert eval_payload['cap_truth_source_digest'].startswith('sha256:')
    assert collapse_payload['run_id'] == 'r1'
    assert collapse_payload['comparison_type'] == 'cross-regime'
    assert collapse_payload['comparison_type_source'] == 'explicit_override'
    assert collapse_payload['skip_reason_codes'] == ['SKIP_EXAMPLE']
    assert collapse_payload['inventory_json_errors'] == []
    assert collapse_payload['cap_truth_source_keys']


def test_reports_preserve_current_payload_when_no_exploratory_sections_are_requested() -> None:
    eval_payload = build_eval_report(
        run_id="r1",
        cap_batch_eval_path=None,
        layer2_result=None,
    )
    qc_payload = build_qc_report(
        run_id="r1",
        conditions_run=["native"],
        excluded_rows_count=0,
        warnings=[],
        result="PASS",
    )
    collapse_payload = build_collapse_figure_spec(
        run_id="r1",
        resource_profile="smoke",
        conditions=["native"],
        cap_metrics={},
    )

    assert "exploratory_sections" not in eval_payload
    assert "operator_surface_contract" not in qc_payload
    assert "semantic_policy_version" not in collapse_payload


def test_reports_attach_guarded_exploratory_sections_only_when_requested() -> None:
    metadata = {
        "semantic_policy_version": "v3.test",
        "verdict_comparability": "not_comparable",
        "verdict_match_rate": "N/A",
        "inventory_authority": build_inventory_authority_payload(
            rc2_output_inventory_mutated=False,
        ),
    }
    sections = [
        {"semantic_source": "rc2", "label": "rc2 primary reference"},
        {"semantic_source": "v3", "label": "[exploratory] v3 secondary summary"},
    ]

    eval_payload = build_eval_report(
        run_id="r1",
        cap_batch_eval_path=None,
        layer2_result=None,
        exploratory_metadata=metadata,
        exploratory_sections=sections,
    )
    qc_payload = build_qc_report(
        run_id="r1",
        conditions_run=["native"],
        excluded_rows_count=0,
        warnings=[],
        result="PASS",
        exploratory_metadata=metadata,
        exploratory_sections=sections,
    )
    collapse_payload = build_collapse_figure_spec(
        run_id="r1",
        resource_profile="smoke",
        conditions=["native"],
        cap_metrics={},
        exploratory_metadata=metadata,
        exploratory_sections=sections,
    )

    assert eval_payload["operator_surface_contract"]["artifact_name"] == "eval_report.json"
    assert qc_payload["operator_surface_contract"]["artifact_name"] == "qc_report.json"
    assert collapse_payload["operator_surface_contract"]["artifact_name"] == "collapse_figure_spec.json"
    assert eval_payload["exploratory_sections"][0]["label"] == "rc2 primary reference"
    assert qc_payload["semantic_policy_version"] == "v3.test"
    assert collapse_payload["verdict_match_rate"] == "N/A"
