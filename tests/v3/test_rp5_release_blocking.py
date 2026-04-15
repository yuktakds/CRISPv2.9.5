from __future__ import annotations

import json
from dataclasses import replace

import pytest

import crisp.v3.runner as runner_module
from crisp.v3.contracts import BridgeComparatorOptions
from crisp.v3.operator_surface_state import (
    OPERATOR_SURFACE_STATE_ARTIFACT,
    PROMOTION_AUTHORITY_REFERENCE,
)
from crisp.v3.policy import parse_sidecar_options
from crisp.v3.release_blocking import (
    PROMOTION_STATUS_BLOCKING,
    SidecarReleaseGateError,
    evaluate_release_blocking,
)
from crisp.v3.runner import run_sidecar
from tests.v3.test_wp6_shadow_activation_readiness import _build_snapshot


def _base_operator_surface_state(*, promotion_gate_results: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "activation_decisions": {
            "v3_shadow_verdict": False,
            "numeric_verdict_rates": False,
        },
        "vn_gate_state": {
            "vn_01": False,
            "vn_02": False,
            "vn_03": False,
            "vn_04": False,
            "vn_05": False,
            "vn_06": False,
            "all_satisfied": False,
        },
        "full_verdict_computable": False,
        "denominator_contract_satisfied": False,
        "promotion_gate_results": promotion_gate_results or {},
    }


def _blocking_lane_result(*, status: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "lane_id": "path",
        "promotion_candidate": False,
        "failed_gate_ids": ["PR-02"],
        "authority_reference": PROMOTION_AUTHORITY_REFERENCE,
        "human_explicit_decision_required": True,
        "required_matrix_mutation_allowed": False,
    }
    if status is not None:
        payload["promotion_status"] = status
    return payload


def test_forbidden_surface_violation_fails_run(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    snapshot = _build_snapshot(tmp_path)
    original = runner_module.run_bridge_comparator

    def _tampered_run_bridge_comparator(*args, **kwargs):
        result = original(*args, **kwargs)
        return replace(
            result,
            comparable_channels=["path", "catalytic", "cap"],
        )

    monkeypatch.setattr(runner_module, "run_bridge_comparator", _tampered_run_bridge_comparator)

    with pytest.raises(SidecarReleaseGateError, match="forbidden_surface:cap_comparable_leak") as exc_info:
        run_sidecar(
            snapshot=snapshot,
            options=parse_sidecar_options({"v3_sidecar": {"enabled": True, "artifact_policy": "full"}}),
            comparator_options=BridgeComparatorOptions(enabled=True),
        )

    sidecar_root = tmp_path / "run" / "v3_sidecar"
    assert exc_info.value.evaluation.exit_code == 1
    assert exc_info.value.evaluation.run_failed is True
    assert exc_info.value.evaluation.artifact_failure is True
    assert (sidecar_root / OPERATOR_SURFACE_STATE_ARTIFACT).exists()
    assert (sidecar_root / "sidecar_run_record.json").exists()
    assert not (sidecar_root / "generator_manifest.json").exists()


def test_cross_artifact_mismatch_refuses_final_artifact_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    snapshot = _build_snapshot(tmp_path)
    original = runner_module.assemble_layer0_authority

    def _tampered_assemble_layer0_authority(*args, **kwargs):
        authority = original(*args, **kwargs)
        verdict_record_payload = {
            **authority.verdict_record_payload,
            "comparable_channels": ["path"],
        }
        return replace(authority, verdict_record_payload=verdict_record_payload)

    monkeypatch.setattr(runner_module, "assemble_layer0_authority", _tampered_assemble_layer0_authority)

    with pytest.raises(SidecarReleaseGateError, match="cross_artifact_mismatch") as exc_info:
        run_sidecar(
            snapshot=snapshot,
            options=parse_sidecar_options({"v3_sidecar": {"enabled": True, "artifact_policy": "full"}}),
            comparator_options=BridgeComparatorOptions(enabled=True),
        )

    sidecar_root = tmp_path / "run" / "v3_sidecar"
    assert exc_info.value.evaluation.exit_code == 1
    assert "cross_artifact_mismatch" in exc_info.value.evaluation.hard_block_failures[0]
    assert (sidecar_root / "sidecar_run_record.json").exists()
    assert not (sidecar_root / "verdict_record.json").exists()
    assert not (sidecar_root / "generator_manifest.json").exists()


def test_advisory_suppression_keeps_run_continuing(tmp_path) -> None:
    snapshot = _build_snapshot(tmp_path)

    result = run_sidecar(
        snapshot=snapshot,
        options=parse_sidecar_options({"v3_sidecar": {"enabled": True, "artifact_policy": "full"}}),
        comparator_options=BridgeComparatorOptions(enabled=True),
    )

    assert result is not None
    assert result.exit_code == 0
    assert result.artifact_failure is False
    assert result.release_blocked is False
    assert result.ci_blocked is False
    sidecar_root = tmp_path / "run" / "v3_sidecar"
    operator_state = json.loads((sidecar_root / OPERATOR_SURFACE_STATE_ARTIFACT).read_text(encoding="utf-8"))
    assert {
        item["surface"]: item["reason"]
        for item in operator_state["suppressed_surfaces"]
    } == {
        "v3_shadow_verdict": "activation_decision_not_accepted",
        "numeric_verdict_rates": "numeric_activation_decision_not_accepted",
    }
    assert (sidecar_root / "generator_manifest.json").exists()


def test_required_promotion_gate_failure_blocks_ci_without_forcing_run_failure() -> None:
    evaluation = evaluate_release_blocking(
        operator_surface_state=_base_operator_surface_state(
            promotion_gate_results={"path": _blocking_lane_result(status=PROMOTION_STATUS_BLOCKING)}
        ),
        comparable_channels=("path", "catalytic"),
        component_match_keys=("path", "catalytic_rule3a"),
        materialized_outputs=(OPERATOR_SURFACE_STATE_ARTIFACT,),
    )

    assert evaluation.exit_code == 0
    assert evaluation.run_failed is False
    assert evaluation.artifact_failure is False
    assert evaluation.ci_blocked is True
    assert evaluation.release_blocked is True
    assert evaluation.blocking_failures == ["promotion_gate_failure:path:PR-02"]


def test_exploratory_lane_failure_does_not_block_ci() -> None:
    evaluation = evaluate_release_blocking(
        operator_surface_state=_base_operator_surface_state(
            promotion_gate_results={"path": _blocking_lane_result()}
        ),
        comparable_channels=("path", "catalytic"),
        component_match_keys=("path", "catalytic_rule3a"),
        required_candidacy_payload={
            "channel_name": "path",
            "operator_surface": {"label": "[exploratory] required-CI candidacy"},
        },
        materialized_outputs=(OPERATOR_SURFACE_STATE_ARTIFACT,),
    )

    assert evaluation.exit_code == 0
    assert evaluation.run_failed is False
    assert evaluation.ci_blocked is False
    assert evaluation.release_blocked is False
    assert evaluation.blocking_failures == []
    assert evaluation.advisory_failures == ["promotion_gate_failure:path:PR-02"]
