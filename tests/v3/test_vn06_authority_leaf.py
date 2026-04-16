from __future__ import annotations

from crisp.v3.operator_surface_state import suppression_reason_by_surface
from crisp.v3.policy import VERDICT_RECORD_SCHEMA_VERSION
from crisp.v3.vn06_authority import (
    VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS,
    verdict_record_operator_surface_inactive,
    verdict_record_schema_missing_fields,
)


def _full_verdict_record() -> dict[str, object]:
    return {
        "schema_version": VERDICT_RECORD_SCHEMA_VERSION,
        "run_id": "run-001",
        "output_root": "/out",
        "semantic_policy_version": "crisp.v3.semantic_policy/rev3-sidecar-first",
        "comparator_scope": "path_and_catalytic_partial",
        "comparable_channels": ["path", "catalytic"],
        "v3_only_evidence_channels": [],
        "channel_lifecycle_states": {},
        "full_verdict_computable": False,
        "full_verdict_comparable_count": 0,
        "verdict_match_rate": None,
        "verdict_mismatch_rate": None,
        "path_component_match_rate": None,
        "v3_shadow_verdict": None,
        "authority_transfer_complete": True,
        "sidecar_run_record_artifact": "sidecar_run_record.json",
        "generator_manifest_artifact": "generator_manifest.json",
    }


# ---------------------------------------------------------------------------
# verdict_record_schema_missing_fields
# ---------------------------------------------------------------------------


def test_no_missing_fields_for_complete_record() -> None:
    result = verdict_record_schema_missing_fields(_full_verdict_record())

    assert result == ()


def test_missing_single_required_field() -> None:
    record = _full_verdict_record()
    del record["run_id"]

    result = verdict_record_schema_missing_fields(record)

    assert "run_id" in result


def test_wrong_schema_version_adds_mismatch_marker() -> None:
    record = _full_verdict_record()
    record["schema_version"] = "crisp.v3.verdict_record/v0"

    result = verdict_record_schema_missing_fields(record)

    assert "schema_version_mismatch" in result


def test_correct_schema_version_does_not_add_mismatch_marker() -> None:
    result = verdict_record_schema_missing_fields(_full_verdict_record())

    assert "schema_version_mismatch" not in result


def test_required_schema_fields_covers_all_expected_keys() -> None:
    assert "schema_version" in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS
    assert "run_id" in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS
    assert "sidecar_run_record_artifact" in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS
    assert "generator_manifest_artifact" in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS


def test_missing_multiple_fields_reported() -> None:
    record = _full_verdict_record()
    del record["run_id"]
    del record["output_root"]

    result = verdict_record_schema_missing_fields(record)

    assert "run_id" in result
    assert "output_root" in result


# ---------------------------------------------------------------------------
# verdict_record_operator_surface_inactive
# ---------------------------------------------------------------------------


def test_operator_surface_inactive_when_all_null() -> None:
    record = _full_verdict_record()

    assert verdict_record_operator_surface_inactive(record) is True


def test_operator_surface_active_when_shadow_verdict_set() -> None:
    record = _full_verdict_record()
    record["v3_shadow_verdict"] = "PASS"

    assert verdict_record_operator_surface_inactive(record) is False


def test_operator_surface_active_when_verdict_match_rate_set() -> None:
    record = _full_verdict_record()
    record["verdict_match_rate"] = 0.95

    assert verdict_record_operator_surface_inactive(record) is False


def test_operator_surface_active_when_verdict_mismatch_rate_set() -> None:
    record = _full_verdict_record()
    record["verdict_mismatch_rate"] = 0.05

    assert verdict_record_operator_surface_inactive(record) is False


# ---------------------------------------------------------------------------
# suppression_reason_by_surface
# ---------------------------------------------------------------------------


def test_suppression_reason_empty_for_none_input() -> None:
    assert suppression_reason_by_surface(None) == {}


def test_suppression_reason_empty_for_non_mapping_input() -> None:
    assert suppression_reason_by_surface("not-a-mapping") == {}  # type: ignore[arg-type]


def test_suppression_reason_empty_when_no_suppressed_surfaces() -> None:
    assert suppression_reason_by_surface({"suppressed_surfaces": []}) == {}


def test_suppression_reason_maps_surface_to_reason() -> None:
    state = {
        "suppressed_surfaces": [
            {"surface": "v3_shadow_verdict", "reason": "activation_decision_not_accepted"},
        ]
    }

    result = suppression_reason_by_surface(state)

    assert result == {"v3_shadow_verdict": "activation_decision_not_accepted"}


def test_suppression_reason_maps_multiple_surfaces() -> None:
    state = {
        "suppressed_surfaces": [
            {"surface": "v3_shadow_verdict", "reason": "vn_gate_unmet:vn_01"},
            {"surface": "numeric_verdict_rates", "reason": "shadow_verdict_inactive:vn_gate_unmet:vn_01"},
        ]
    }

    result = suppression_reason_by_surface(state)

    assert result["v3_shadow_verdict"] == "vn_gate_unmet:vn_01"
    assert result["numeric_verdict_rates"] == "shadow_verdict_inactive:vn_gate_unmet:vn_01"


def test_suppression_reason_ignores_non_mapping_entries() -> None:
    state = {
        "suppressed_surfaces": [
            "not-a-mapping",
            {"surface": "v3_shadow_verdict", "reason": "some_reason"},
        ]
    }

    result = suppression_reason_by_surface(state)

    assert result == {"v3_shadow_verdict": "some_reason"}
