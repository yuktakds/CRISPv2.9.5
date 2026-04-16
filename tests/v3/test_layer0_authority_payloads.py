from __future__ import annotations

from crisp.v3.layer0_authority import (
    CANONICAL_LAYER0_AUTHORITY_ARTIFACT,
    GENERATOR_MANIFEST_ARTIFACT,
    LAYER0_AUTHORITY_MODE,
    SIDECAR_RUN_RECORD_ARTIFACT,
    SIDECAR_RUN_RECORD_ROLE,
    TRANSFERRED_AUTHORITY_FIELDS,
    VERDICT_RECORD_ROLE,
    build_sidecar_layer0_authority_metadata,
    build_verdict_record_authority_fields,
    build_verdict_record_payload,
    extract_sidecar_layer0_authority_mirror,
    sidecar_layer0_authority_artifact,
    sidecar_layer0_authority_mode,
    sidecar_run_record_role,
)


def _authority_fields(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "run_id": "run-001",
        "output_root": "/output",
        "semantic_policy_version": "v1",
        "comparator_scope": "path_and_catalytic_partial",
        "comparable_channels": ["path", "catalytic"],
        "v3_only_evidence_channels": ["cap", "catalytic_rule3b"],
        "channel_lifecycle_states": {"path": "OBSERVATION_MATERIALIZED"},
        "full_verdict_computable": False,
        "full_verdict_comparable_count": 0,
        "verdict_match_rate": None,
        "verdict_mismatch_rate": None,
        "path_component_match_rate": 0.97,
        "v3_shadow_verdict": None,
        "authority_transfer_complete": True,
    }
    defaults.update(overrides)
    return defaults  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# build_verdict_record_authority_fields
# ---------------------------------------------------------------------------


def test_authority_fields_round_trips_all_values() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]

    assert fields["run_id"] == "run-001"
    assert fields["comparator_scope"] == "path_and_catalytic_partial"
    assert fields["comparable_channels"] == ["path", "catalytic"]
    assert fields["verdict_match_rate"] is None
    assert fields["path_component_match_rate"] == 0.97
    assert fields["v3_shadow_verdict"] is None
    assert fields["authority_transfer_complete"] is True


def test_authority_fields_copies_lists_not_references() -> None:
    channels = ["path"]
    fields = build_verdict_record_authority_fields(**_authority_fields(comparable_channels=channels))  # type: ignore[arg-type]
    channels.append("mutated")
    assert fields["comparable_channels"] == ["path"]


def test_authority_fields_casts_bool_and_int() -> None:
    fields = build_verdict_record_authority_fields(
        **_authority_fields(full_verdict_computable=1, full_verdict_comparable_count=2.0, authority_transfer_complete=0),  # type: ignore[arg-type]
    )
    assert fields["full_verdict_computable"] is True
    assert fields["full_verdict_comparable_count"] == 2
    assert fields["authority_transfer_complete"] is False


# ---------------------------------------------------------------------------
# build_verdict_record_payload — transfers exactly TRANSFERRED_AUTHORITY_FIELDS
# ---------------------------------------------------------------------------


def test_verdict_record_payload_contains_all_transferred_fields() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(authority_fields=fields)

    for field in TRANSFERRED_AUTHORITY_FIELDS:
        assert field in payload, f"missing field: {field}"


def test_verdict_record_payload_includes_artifact_names() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(authority_fields=fields)

    assert payload["sidecar_run_record_artifact"] == SIDECAR_RUN_RECORD_ARTIFACT
    assert payload["generator_manifest_artifact"] == GENERATOR_MANIFEST_ARTIFACT


def test_verdict_record_payload_custom_artifact_names() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(
        authority_fields=fields,
        sidecar_run_record_artifact="custom_sidecar.json",
        generator_manifest_artifact="custom_manifest.json",
    )

    assert payload["sidecar_run_record_artifact"] == "custom_sidecar.json"
    assert payload["generator_manifest_artifact"] == "custom_manifest.json"


# ---------------------------------------------------------------------------
# build_sidecar_layer0_authority_metadata — authority mode and mirror
# ---------------------------------------------------------------------------


def test_sidecar_authority_metadata_mode_and_artifact() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(authority_fields=fields)
    metadata = build_sidecar_layer0_authority_metadata(verdict_record_payload=payload)

    assert metadata["layer0_authority_artifact"] == CANONICAL_LAYER0_AUTHORITY_ARTIFACT
    assert metadata["layer0_authority_mode"] == LAYER0_AUTHORITY_MODE
    assert metadata["verdict_record_role"] == VERDICT_RECORD_ROLE
    assert metadata["sidecar_run_record_role"] == SIDECAR_RUN_RECORD_ROLE


def test_sidecar_authority_metadata_mirror_matches_authority_fields() -> None:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(authority_fields=fields)
    metadata = build_sidecar_layer0_authority_metadata(verdict_record_payload=payload)

    mirror = metadata["layer0_authority_mirror"]
    assert isinstance(mirror, dict)
    assert mirror["comparator_scope"] == "path_and_catalytic_partial"
    assert mirror["v3_shadow_verdict"] is None
    assert mirror["verdict_match_rate"] is None


# ---------------------------------------------------------------------------
# extract / accessor functions on sidecar_run_record
# ---------------------------------------------------------------------------


def _make_sidecar_run_record(mode: str = LAYER0_AUTHORITY_MODE) -> dict[str, object]:
    fields = build_verdict_record_authority_fields(**_authority_fields())  # type: ignore[arg-type]
    payload = build_verdict_record_payload(authority_fields=fields)
    metadata = build_sidecar_layer0_authority_metadata(verdict_record_payload=payload)
    return {"bridge_diagnostics": {**metadata}}


def test_extract_mirror_returns_transferred_fields() -> None:
    record = _make_sidecar_run_record()
    mirror = extract_sidecar_layer0_authority_mirror(record)

    for field in TRANSFERRED_AUTHORITY_FIELDS:
        assert field in mirror, f"mirror missing: {field}"


def test_sidecar_authority_artifact_returns_artifact_name() -> None:
    record = _make_sidecar_run_record()
    assert sidecar_layer0_authority_artifact(record) == CANONICAL_LAYER0_AUTHORITY_ARTIFACT


def test_sidecar_authority_mode_returns_m2() -> None:
    record = _make_sidecar_run_record()
    assert sidecar_layer0_authority_mode(record) == LAYER0_AUTHORITY_MODE


def test_sidecar_run_record_role_returns_mirror_role() -> None:
    record = _make_sidecar_run_record()
    assert sidecar_run_record_role(record) == SIDECAR_RUN_RECORD_ROLE


def test_accessors_return_none_for_missing_bridge_diagnostics() -> None:
    record: dict[str, object] = {}
    assert extract_sidecar_layer0_authority_mirror(record) == {}
    assert sidecar_layer0_authority_artifact(record) is None
    assert sidecar_layer0_authority_mode(record) is None
    assert sidecar_run_record_role(record) is None


def test_accessors_return_none_for_non_mapping_bridge_diagnostics() -> None:
    record = {"bridge_diagnostics": "not_a_dict"}
    assert extract_sidecar_layer0_authority_mirror(record) == {}
    assert sidecar_layer0_authority_artifact(record) is None
    assert sidecar_layer0_authority_mode(record) is None
    assert sidecar_run_record_role(record) is None
