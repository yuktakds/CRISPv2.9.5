from __future__ import annotations

from crisp.v3.readiness.consistency import (
    RC2_INVENTORY_SOURCE,
    SIDECAR_INVENTORY_SOURCE,
    build_inventory_authority_payload,
    find_truth_source_stage,
)


# ---------------------------------------------------------------------------
# build_inventory_authority_payload
# ---------------------------------------------------------------------------


def test_inventory_authority_payload_rc2_not_mutated() -> None:
    payload = build_inventory_authority_payload(rc2_output_inventory_mutated=False)

    assert payload["rc2_inventory_mutated"] is False
    assert payload["sidecar_inventory_source"] == SIDECAR_INVENTORY_SOURCE
    assert payload["rc2_inventory_source"] == RC2_INVENTORY_SOURCE


def test_inventory_authority_payload_rc2_mutated() -> None:
    payload = build_inventory_authority_payload(rc2_output_inventory_mutated=True)

    assert payload["rc2_inventory_mutated"] is True


def test_inventory_authority_payload_has_required_keys() -> None:
    payload = build_inventory_authority_payload(rc2_output_inventory_mutated=False)

    required_keys = {
        "sidecar_inventory_source",
        "sidecar_outputs_authority",
        "sidecar_truth_source_authority",
        "layer0_canonical_authority",
        "layer0_backward_compatibility_mirror",
        "operator_report_enumeration_authority",
        "rc2_inventory_source",
        "rc2_outputs_authority",
        "rc2_inventory_mutated",
    }
    assert required_keys <= set(payload.keys())


def test_inventory_authority_payload_layer0_canonical_is_verdict_record() -> None:
    payload = build_inventory_authority_payload(rc2_output_inventory_mutated=False)

    assert payload["layer0_canonical_authority"] == "verdict_record.json"
    assert payload["layer0_backward_compatibility_mirror"] == "sidecar_run_record.json"


# ---------------------------------------------------------------------------
# find_truth_source_stage
# ---------------------------------------------------------------------------


def test_find_truth_source_stage_returns_matching_item() -> None:
    chain = [
        {"stage": "input_snapshot", "path": "/data/input.json"},
        {"stage": "output_snapshot", "path": "/data/output.json"},
    ]
    result = find_truth_source_stage(chain, "input_snapshot")

    assert result["stage"] == "input_snapshot"
    assert result["path"] == "/data/input.json"


def test_find_truth_source_stage_returns_empty_dict_when_not_found() -> None:
    chain = [{"stage": "output_snapshot"}]
    result = find_truth_source_stage(chain, "input_snapshot")

    assert result == {}


def test_find_truth_source_stage_empty_chain_returns_empty_dict() -> None:
    result = find_truth_source_stage([], "input_snapshot")

    assert result == {}


def test_find_truth_source_stage_accepts_tuple_input() -> None:
    chain = ({"stage": "input_snapshot", "digest": "sha256:abc"},)
    result = find_truth_source_stage(chain, "input_snapshot")

    assert result["digest"] == "sha256:abc"


def test_find_truth_source_stage_returns_copy_not_reference() -> None:
    original = {"stage": "input_snapshot", "value": 1}
    chain = [original]
    result = find_truth_source_stage(chain, "input_snapshot")
    result["value"] = 999

    assert original["value"] == 1
