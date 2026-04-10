from __future__ import annotations

import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.utils.jsonx import canonical_json_bytes
from crisp.v3.preconditions import audit_readiness_consistency
from tests.v29.test_v3_sidecar_hook import _normalize_json_value, _snapshot_rc2_files, _write_fixture_config
from tests.v29_smoke_helpers import (
    make_stub_core_bridge,
    write_managed_theta_table,
    write_minimal_caps_fixture,
    write_pat_diagnostics,
)


def _run_cap_sidecar(
    *,
    repo_root: Path,
    tmp_root: Path,
    config_path: Path,
    library_path: Path,
    stageplan_path: Path,
    caps_path: Path,
    pat_diagnostics_path: Path,
    theta_table_path: Path,
    out_dir: Path,
    monkeypatch,
    cap_enabled: bool,
) -> dict[str, object]:
    monkeypatch.setattr(
        "crisp.v29.cli.run_core_bridge",
        make_stub_core_bridge(library_path=library_path, target_id="tgt"),
    )
    integrated_path = tmp_root / f"{out_dir.parent.name}-{out_dir.name}.yaml"
    lines = [
        "pathyes_mode: pat-backed",
        f"pat_diagnostics_path: {pat_diagnostics_path}",
        f"theta_rule1_table: {theta_table_path}",
        "v3_sidecar:",
        "  enabled: true",
    ]
    if cap_enabled:
        lines.extend(
            [
                "  channels:",
                "    cap:",
                "      enabled: true",
            ]
        )
    integrated_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_integrated_v29(
        repo_root=repo_root,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        out_dir=out_dir,
        integrated_config_path=integrated_path,
        run_mode="core+rule1+cap",
        caps_path=caps_path,
    )


def _normalized_sidecar_file(path: Path, *, run_dir: Path) -> bytes:
    raw_run_dir = str(run_dir)
    escaped_run_dir = raw_run_dir.replace("\\", "\\\\")
    posix_run_dir = run_dir.as_posix()
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(text)
        normalized_payload = _normalize_json_value(
            payload,
            raw_run_dir=raw_run_dir,
            escaped_run_dir=escaped_run_dir,
            posix_run_dir=posix_run_dir,
        )
        return canonical_json_bytes(normalized_payload)
    rows = [
        _normalize_json_value(
            json.loads(line),
            raw_run_dir=raw_run_dir,
            escaped_run_dir=escaped_run_dir,
            posix_run_dir=posix_run_dir,
        )
        for line in text.splitlines()
        if line.strip()
    ]
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _normalized_run_record(path: Path, *, run_dir: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized = _normalize_json_value(
        payload,
        raw_run_dir=str(run_dir),
        escaped_run_dir=str(run_dir).replace("\\", "\\\\"),
        posix_run_dir=run_dir.as_posix(),
    )
    assert isinstance(normalized, dict)
    normalized.pop("output_root", None)
    normalized.pop("rc2_output_digest_before", None)
    normalized.pop("rc2_output_digest_after", None)
    bridge_diagnostics = normalized.get("bridge_diagnostics")
    if isinstance(bridge_diagnostics, dict):
        bridge_diagnostics.pop("cap_pair_features_path", None)
    return normalized


def test_cap_sidecar_is_opt_in_and_non_interfering(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    caps_path = write_minimal_caps_fixture(repo_root / "caps.parquet", target_id="tgt")
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={
            "blockage_ratio": 0.8,
            "apo_accessible_goal_voxels": 4,
            "feasible_count": 5,
            "witness_pose_id": "pose-1",
            "obstruction_path_ids": ["path-1"],
        },
    )
    theta_table_path = write_managed_theta_table(repo_root / "theta.parquet", config_path=config_path)

    path_only_dir = tmp_path / "path-only" / "run"
    cap_on_dir = tmp_path / "cap-on" / "run"
    path_only = _run_cap_sidecar(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        caps_path=caps_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=path_only_dir,
        monkeypatch=monkeypatch,
        cap_enabled=False,
    )
    cap_on = _run_cap_sidecar(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        caps_path=caps_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=cap_on_dir,
        monkeypatch=monkeypatch,
        cap_enabled=True,
    )

    assert path_only["run_mode_complete"] is True
    assert cap_on["run_mode_complete"] is True
    assert _snapshot_rc2_files(path_only_dir) == _snapshot_rc2_files(cap_on_dir)
    assert (path_only_dir / "v3_sidecar" / "preconditions_readiness.json").exists()
    assert not (path_only_dir / "v3_sidecar" / "channel_evidence_cap.jsonl").exists()
    assert (cap_on_dir / "v3_sidecar" / "channel_evidence_cap.jsonl").exists()
    assert (cap_on_dir / "v3_sidecar" / "builder_provenance.json").exists()
    assert (cap_on_dir / "v3_sidecar" / "preconditions_readiness.json").exists()

    bundle = json.loads((cap_on_dir / "v3_sidecar" / "observation_bundle.json").read_text(encoding="utf-8"))
    assert [item["channel_name"] for item in bundle["observations"]] == ["path", "cap"]
    run_record = json.loads((cap_on_dir / "v3_sidecar" / "sidecar_run_record.json").read_text(encoding="utf-8"))
    assert run_record["channel_records"]["cap"]["enabled"] is True
    readiness = json.loads((cap_on_dir / "v3_sidecar" / "preconditions_readiness.json").read_text(encoding="utf-8"))
    builder_provenance = json.loads((cap_on_dir / "v3_sidecar" / "builder_provenance.json").read_text(encoding="utf-8"))
    manifest = json.loads((cap_on_dir / "v3_sidecar" / "generator_manifest.json").read_text(encoding="utf-8"))
    assert audit_readiness_consistency(
        readiness=readiness,
        builder_provenance=builder_provenance,
        sidecar_run_record=run_record,
        generator_manifest=manifest,
    ) == ()
    assert run_record["channel_records"]["cap"]["channel_state"] == "PROVISIONAL"
    assert run_record["channel_records"]["cap"]["truth_source_chain"][0]["source_label"] in {"pair_features.parquet", "pair_features.jsonl"}
    assert run_record["channel_records"]["path"]["enabled"] is True

    inventory = json.loads((cap_on_dir / "output_inventory.json").read_text(encoding="utf-8"))
    assert all(not name.startswith("v3_sidecar/") for name in inventory["generated_outputs"])


def test_cap_sidecar_outputs_are_deterministic_across_repeat_integrated_runs(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path, library_path, stageplan_path = _write_fixture_config(repo_root)
    caps_path = write_minimal_caps_fixture(repo_root / "caps.parquet", target_id="tgt")
    pat_diagnostics_path = write_pat_diagnostics(
        repo_root / "pat.json",
        goal_precheck_passed=True,
        extra_diagnostics={
            "blockage_ratio": 0.8,
            "apo_accessible_goal_voxels": 4,
            "feasible_count": 5,
            "witness_pose_id": "pose-1",
            "obstruction_path_ids": ["path-1"],
        },
    )
    theta_table_path = write_managed_theta_table(repo_root / "theta.parquet", config_path=config_path)

    first_dir = tmp_path / "first" / "run"
    second_dir = tmp_path / "second" / "run"
    _run_cap_sidecar(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        caps_path=caps_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=first_dir,
        monkeypatch=monkeypatch,
        cap_enabled=True,
    )
    _run_cap_sidecar(
        repo_root=repo_root,
        tmp_root=tmp_path,
        config_path=config_path,
        library_path=library_path,
        stageplan_path=stageplan_path,
        caps_path=caps_path,
        pat_diagnostics_path=pat_diagnostics_path,
        theta_table_path=theta_table_path,
        out_dir=second_dir,
        monkeypatch=monkeypatch,
        cap_enabled=True,
    )

    for name in (
        "observation_bundle.json",
        "channel_evidence_cap.jsonl",
        "builder_provenance.json",
        "preconditions_readiness.json",
    ):
        assert _normalized_sidecar_file(first_dir / "v3_sidecar" / name, run_dir=first_dir) == _normalized_sidecar_file(
            second_dir / "v3_sidecar" / name,
            run_dir=second_dir,
        )
    assert _normalized_run_record(first_dir / "v3_sidecar" / "sidecar_run_record.json", run_dir=first_dir) == _normalized_run_record(
        second_dir / "v3_sidecar" / "sidecar_run_record.json",
        run_dir=second_dir,
    )
