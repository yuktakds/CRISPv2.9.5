from __future__ import annotations

import json
from pathlib import Path

import pytest

from crisp.repro.hashing import sha256_json
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.policy import SEMANTIC_POLICY_VERSION


def test_artifact_sink_writes_manifest_without_self_enumeration(tmp_path: Path) -> None:
    sink = ArtifactSink(tmp_path / "v3_sidecar", semantic_policy_version=SEMANTIC_POLICY_VERSION)
    sink.write_json("semantic_policy_version.json", {"semantic_policy_version": SEMANTIC_POLICY_VERSION}, layer="layer0")
    sink.write_json("sidecar_run_record.json", {"run_id": "run-1"}, layer="layer0")
    sink.write_jsonl("channel_evidence_path.jsonl", [{"channel_name": "path"}], layer="layer1")

    manifest_path, expected_output_digest = sink.write_generator_manifest(run_id="run-1")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["expected_output_digest"] == expected_output_digest
    assert {item["relative_path"] for item in manifest["outputs"]} == {
        "semantic_policy_version.json",
        "sidecar_run_record.json",
        "channel_evidence_path.jsonl",
    }
    assert "generator_manifest.json" not in {item["relative_path"] for item in manifest["outputs"]}
    assert expected_output_digest == sha256_json({"outputs": manifest["outputs"]})


def test_artifact_sink_rejects_duplicate_relative_paths(tmp_path: Path) -> None:
    sink = ArtifactSink(tmp_path / "v3_sidecar", semantic_policy_version=SEMANTIC_POLICY_VERSION)
    sink.write_json("semantic_policy_version.json", {"semantic_policy_version": SEMANTIC_POLICY_VERSION}, layer="layer0")

    with pytest.raises(ValueError, match="artifact already materialized"):
        sink.write_json("semantic_policy_version.json", {"semantic_policy_version": "other"}, layer="layer0")
