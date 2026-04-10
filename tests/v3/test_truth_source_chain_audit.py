from __future__ import annotations

from crisp.v3.preconditions import ChannelState, GateStatus, audit_truth_source_chain, derive_truth_source_record


def test_truth_source_record_derives_required_fields_from_builder_provenance_channel_record() -> None:
    record = derive_truth_source_record(
        {
            "truth_source_chain": [
                {
                    "stage": "input_snapshot",
                    "source_label": "pat.json",
                    "source_digest": "sha256:1",
                    "source_location_kind": "run_output_snapshot",
                },
                {
                    "stage": "channel_builder",
                    "builder": "crisp.v3.path_channel.PathEvidenceChannel.evaluate",
                    "projector": "crisp.v3.path_channel.project_path_payload",
                    "channel_evidence_artifact": "channel_evidence_path.jsonl",
                },
                {
                    "stage": "bridge_route",
                    "bridge": "crisp.v3.scv_bridge.SCVBridge.route",
                    "observation_artifact": "observation_bundle.json",
                },
            ],
        }
    )

    assert record["source_label"] == "pat.json"
    assert record["source_digest"] == "sha256:1"
    assert record["source_location_kind"] == "run_output_snapshot"
    assert record["builder_identity"] == "crisp.v3.path_channel.PathEvidenceChannel.evaluate"
    assert record["projector_identity"] == "crisp.v3.path_channel.project_path_payload"
    assert record["observation_artifact_pointer"] == "observation_bundle.json"
    assert record["channel_evidence_artifact_pointer"] == "channel_evidence_path.jsonl"


def test_truth_source_audit_returns_na_for_disabled_channel() -> None:
    audit = audit_truth_source_chain(
        "cap",
        {"truth_source_chain": [{"stage": "channel_toggle", "status": "disabled"}]},
        channel_state=ChannelState.DISABLED,
    )

    assert audit.status is GateStatus.NA
    assert audit.missing_fields == ()


def test_truth_source_audit_blocks_missing_builder_fields() -> None:
    audit = audit_truth_source_chain(
        "catalytic",
        {
            "truth_source_chain": [
                {
                    "stage": "input_snapshot",
                    "source_label": "evidence_core.parquet",
                    "source_digest": "sha256:2",
                    "source_location_kind": "run_output_snapshot",
                },
                {
                    "stage": "channel_builder",
                    "builder": "crisp.v3.channels.catalytic.CatalyticEvidenceChannel.evaluate",
                },
            ],
        },
        channel_state=ChannelState.OBSERVATION_MATERIALIZED,
    )

    assert audit.status is GateStatus.BLOCKED
    assert set(audit.missing_fields) == {"projector_identity", "observation_artifact_pointer"}
