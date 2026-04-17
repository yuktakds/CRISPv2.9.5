from __future__ import annotations

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    LAYER0_AUTHORITY_MODE,
    M1_LAYER0_AUTHORITY_MODE,
    SIDECAR_RUN_RECORD_ROLE,
    VERDICT_RECORD_ROLE,
)
from crisp.v3.vn06_authority import (
    VERDICT_RECORD_AUTHORITY_FIELD_MAP,
    VERDICT_RECORD_AUTHORITY_FIELDS,
    VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS,
    collect_verdict_record_dual_write_mismatches,
    collect_verdict_record_dual_write_source_gaps,
    determine_authority_phase,
    field_map_payload,
)


# ---------------------------------------------------------------------------
# determine_authority_phase
# ---------------------------------------------------------------------------


def _sidecar_with_mirror(fields: dict[str, object]) -> dict[str, object]:
    """Build a sidecar_run_record with a layer0_authority_mirror."""
    return {
        "bridge_diagnostics": {
            "layer0_authority_artifact": CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
            "layer0_authority_mode": LAYER0_AUTHORITY_MODE,
            "verdict_record_role": VERDICT_RECORD_ROLE,
            "sidecar_run_record_role": SIDECAR_RUN_RECORD_ROLE,
            "layer0_authority_mirror": fields,
        }
    }


def test_authority_phase_is_m2_when_verdict_record_transfer_complete() -> None:
    verdict_record = {"authority_transfer_complete": True}
    phase = determine_authority_phase(verdict_record=verdict_record, sidecar_run_record={})

    assert phase == LAYER0_AUTHORITY_MODE


def test_authority_phase_is_m2_when_sidecar_has_nonempty_mirror() -> None:
    sidecar = _sidecar_with_mirror({"comparator_scope": "path_and_catalytic_partial"})
    phase = determine_authority_phase(verdict_record=None, sidecar_run_record=sidecar)

    assert phase == LAYER0_AUTHORITY_MODE


def test_authority_phase_is_m2_when_sidecar_authority_mode_is_m2() -> None:
    sidecar = {
        "bridge_diagnostics": {
            "layer0_authority_mode": LAYER0_AUTHORITY_MODE,
            "layer0_authority_mirror": {},
        }
    }
    # empty mirror but mode tag is M2 → sidecar_layer0_authority_mode returns M2
    phase = determine_authority_phase(verdict_record=None, sidecar_run_record=sidecar)

    assert phase == LAYER0_AUTHORITY_MODE


def test_authority_phase_is_m1_when_no_transfer_signals() -> None:
    phase = determine_authority_phase(verdict_record=None, sidecar_run_record={})

    assert phase == M1_LAYER0_AUTHORITY_MODE


def test_authority_phase_m1_overrides_verdict_record_without_transfer_complete() -> None:
    # verdict_record exists but authority_transfer_complete is False
    verdict_record = {"authority_transfer_complete": False, "run_id": "x"}
    phase = determine_authority_phase(verdict_record=verdict_record, sidecar_run_record={})

    assert phase == M1_LAYER0_AUTHORITY_MODE


# ---------------------------------------------------------------------------
# field_map_payload
# ---------------------------------------------------------------------------


def test_field_map_payload_m2_uses_mirror_source_paths() -> None:
    rows = field_map_payload(authority_phase=LAYER0_AUTHORITY_MODE)

    for row in rows:
        assert row["source_field"].startswith(
            "bridge_diagnostics.layer0_authority_mirror."
        ), f"expected mirror path, got: {row['source_field']}"


def test_field_map_payload_m1_uses_legacy_source_fields() -> None:
    rows = field_map_payload(authority_phase=M1_LAYER0_AUTHORITY_MODE)

    # M1 rows preserve original spec source_field (mix of path-based and invariant text)
    source_fields = {row["source_field"] for row in rows}
    # M1 rows must NOT use the mirror prefix
    assert not any(
        sf.startswith("bridge_diagnostics.layer0_authority_mirror.") for sf in source_fields
    )


def test_field_map_payload_length_matches_authority_field_map() -> None:
    m2_rows = field_map_payload(authority_phase=LAYER0_AUTHORITY_MODE)
    m1_rows = field_map_payload(authority_phase=M1_LAYER0_AUTHORITY_MODE)

    assert len(m2_rows) == len(VERDICT_RECORD_AUTHORITY_FIELD_MAP)
    assert len(m1_rows) == len(VERDICT_RECORD_AUTHORITY_FIELD_MAP)


def test_field_map_payload_target_fields_are_stable() -> None:
    rows = field_map_payload(authority_phase=LAYER0_AUTHORITY_MODE)
    target_fields = tuple(row["target_field"] for row in rows)

    assert target_fields == VERDICT_RECORD_AUTHORITY_FIELDS


# ---------------------------------------------------------------------------
# VERDICT_RECORD_AUTHORITY_FIELD_MAP structure
# ---------------------------------------------------------------------------


def test_authority_field_map_entries_have_required_keys() -> None:
    for spec in VERDICT_RECORD_AUTHORITY_FIELD_MAP:
        assert spec.target_field
        assert spec.comparison_mode in {"exact", "nullable-exact", "set-equal"}
        assert spec.mismatch_severity == "hard-block"


def test_required_schema_fields_covers_all_authority_fields() -> None:
    # every authority field must appear in the required schema fields list
    for field_name in VERDICT_RECORD_AUTHORITY_FIELDS:
        assert field_name in VERDICT_RECORD_REQUIRED_SCHEMA_FIELDS, (
            f"{field_name} is in VERDICT_RECORD_AUTHORITY_FIELDS but not in REQUIRED_SCHEMA_FIELDS"
        )


# ---------------------------------------------------------------------------
# collect_verdict_record_dual_write_source_gaps (M2 path)
# ---------------------------------------------------------------------------


def test_source_gaps_empty_when_mirror_has_all_fields() -> None:
    sidecar = _sidecar_with_mirror(
        {field: None for field in VERDICT_RECORD_AUTHORITY_FIELDS}
    )
    gaps = collect_verdict_record_dual_write_source_gaps(sidecar_run_record=sidecar)

    assert gaps == ()


def test_source_gaps_reports_missing_mirror_fields() -> None:
    # mirror with only one field
    sidecar = _sidecar_with_mirror({"comparator_scope": "path_and_catalytic_partial"})
    gaps = collect_verdict_record_dual_write_source_gaps(sidecar_run_record=sidecar)

    assert "run_id" in gaps
    assert "comparable_channels" in gaps


# ---------------------------------------------------------------------------
# collect_verdict_record_dual_write_mismatches (M2 path)
# ---------------------------------------------------------------------------


def _complete_verdict_record(overrides: dict[str, object] | None = None) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": "crisp.v3.verdict_record/v1",
        "run_id": "run-001",
        "output_root": "/output",
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
    if overrides:
        record.update(overrides)
    return record


def test_no_mismatches_when_verdict_record_matches_mirror() -> None:
    vr = _complete_verdict_record()
    mirror_fields = {k: vr[k] for k in VERDICT_RECORD_AUTHORITY_FIELDS}
    sidecar = _sidecar_with_mirror(mirror_fields)

    mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=vr, sidecar_run_record=sidecar
    )

    assert mismatches == ()


def test_mismatch_reported_for_differing_comparator_scope() -> None:
    vr = _complete_verdict_record({"comparator_scope": "path_only_partial"})
    mirror_fields = {k: vr[k] for k in VERDICT_RECORD_AUTHORITY_FIELDS}
    mirror_fields["comparator_scope"] = "path_and_catalytic_partial"  # differs
    sidecar = _sidecar_with_mirror(mirror_fields)

    mismatches = collect_verdict_record_dual_write_mismatches(
        verdict_record=vr, sidecar_run_record=sidecar
    )

    assert "comparator_scope" in mismatches
