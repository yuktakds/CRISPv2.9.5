from __future__ import annotations

from crisp.v3.preconditions_types import (
    ALLOWED_INPUT_SOURCE_KINDS,
    ALLOWED_TRUTH_SOURCE_KINDS,
    ARTIFACT_GENERATOR_IDS,
    GATE_EVIDENCE_SCHEMA_VERSION,
    ArtifactSectionReference,
    ChannelState,
    GateRecord,
    GateStatus,
    TruthSourceAudit,
)


# ---------------------------------------------------------------------------
# GateStatus enum
# ---------------------------------------------------------------------------


def test_gate_status_values_are_stable() -> None:
    assert GateStatus.PASS.value == "pass"
    assert GateStatus.BLOCKED.value == "blocked"
    assert GateStatus.OPEN.value == "open"
    assert GateStatus.NA.value == "na"


def test_gate_status_is_string_comparable() -> None:
    assert GateStatus.PASS == "pass"
    assert GateStatus.BLOCKED == "blocked"


# ---------------------------------------------------------------------------
# ChannelState enum
# ---------------------------------------------------------------------------


def test_channel_state_values_are_stable() -> None:
    assert ChannelState.DISABLED.value == "disabled"
    assert ChannelState.APPLICABILITY_ONLY.value == "applicability_only"
    assert ChannelState.OBSERVATION_MATERIALIZED.value == "observation_materialized"
    assert ChannelState.NOT_COMPARABLE.value == "not_comparable"


def test_channel_state_is_string_comparable() -> None:
    assert ChannelState.OBSERVATION_MATERIALIZED == "observation_materialized"


# ---------------------------------------------------------------------------
# GATE_EVIDENCE_SCHEMA_VERSION
# ---------------------------------------------------------------------------


def test_gate_evidence_schema_version_is_stable() -> None:
    assert GATE_EVIDENCE_SCHEMA_VERSION == "crisp.v3.readiness_gate_evidence/v1"


# ---------------------------------------------------------------------------
# ARTIFACT_GENERATOR_IDS
# ---------------------------------------------------------------------------


def test_artifact_generator_ids_covers_key_artifacts() -> None:
    key_artifacts = (
        "verdict_record.json",
        "sidecar_run_record.json",
        "generator_manifest.json",
        "observation_bundle.json",
        "preconditions_readiness.json",
        "shadow_stability_campaign.json",
    )
    for artifact in key_artifacts:
        assert artifact in ARTIFACT_GENERATOR_IDS, f"missing: {artifact}"


def test_artifact_generator_ids_all_values_are_versioned() -> None:
    for artifact, generator_id in ARTIFACT_GENERATOR_IDS.items():
        assert generator_id.startswith("v3."), f"{artifact}: {generator_id}"
        assert "/v1" in generator_id, f"{artifact}: {generator_id}"


# ---------------------------------------------------------------------------
# ALLOWED_INPUT_SOURCE_KINDS / ALLOWED_TRUTH_SOURCE_KINDS
# ---------------------------------------------------------------------------


def test_allowed_input_source_kinds_covers_three_channels() -> None:
    assert set(ALLOWED_INPUT_SOURCE_KINDS.keys()) == {"path", "cap", "catalytic"}


def test_allowed_truth_source_kinds_covers_three_channels() -> None:
    assert set(ALLOWED_TRUTH_SOURCE_KINDS.keys()) == {"path", "cap", "catalytic"}


def test_path_input_and_truth_source_use_pat_diagnostics() -> None:
    assert "pat_diagnostics_json" in ALLOWED_INPUT_SOURCE_KINDS["path"]
    assert "pat_diagnostics_json" in ALLOWED_TRUTH_SOURCE_KINDS["path"]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_gate_record_stores_all_fields() -> None:
    record = GateRecord(gate_id="P2", status=GateStatus.PASS, detail="all checks pass")

    assert record.gate_id == "P2"
    assert record.status == GateStatus.PASS
    assert record.detail == "all checks pass"


def test_artifact_section_reference_stores_all_fields() -> None:
    ref = ArtifactSectionReference(
        artifact_name="verdict_record.json",
        generator_id="v3.verdict_record/v1",
        section_id="authority-transfer",
    )

    assert ref.artifact_name == "verdict_record.json"
    assert ref.generator_id == "v3.verdict_record/v1"
    assert ref.section_id == "authority-transfer"


def test_truth_source_audit_defaults_to_empty_record() -> None:
    audit = TruthSourceAudit(
        channel_id="path",
        status=GateStatus.PASS,
        missing_fields=(),
    )

    assert audit.record == {}
    assert audit.missing_fields == ()
