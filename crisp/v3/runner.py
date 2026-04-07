from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from crisp.repro.hashing import sha256_file, sha256_json
from crisp.v3.artifacts.sink import ArtifactSink
from crisp.v3.contracts import SidecarOptions, SidecarRunRecord, SidecarRunResult, SidecarSnapshot
from crisp.v3.path_channel import PathEvidenceChannel
from crisp.v3.policy import SEMANTIC_POLICY_VERSION, SIDECAR_RUN_RECORD_SCHEMA_VERSION, semantic_policy_payload
from crisp.v3.scv_bridge import SCVBridge, bundle_to_jsonl_rows


class SidecarInvariantError(RuntimeError):
    pass


def build_sidecar_snapshot(
    *,
    run_id: str,
    run_mode: str,
    repo_root: str,
    out_dir: str | Path,
    config_path: str | Path,
    integrated_config_path: str | Path | None,
    resource_profile: str,
    comparison_type: str | None,
    pathyes_mode_requested: str | None,
    pathyes_force_false_requested: bool,
    pat_diagnostics_path: str | Path | None,
    config: Any,
    rc2_generated_outputs: list[str],
) -> SidecarSnapshot:
    return SidecarSnapshot(
        run_id=run_id,
        run_mode=run_mode,
        repo_root=str(repo_root),
        out_dir=str(out_dir),
        config_path=str(config_path),
        integrated_config_path=(
            None if integrated_config_path is None else str(integrated_config_path)
        ),
        resource_profile=resource_profile,
        comparison_type=comparison_type,
        pathyes_mode_requested=pathyes_mode_requested,
        pathyes_force_false_requested=pathyes_force_false_requested,
        pat_diagnostics_path=(None if pat_diagnostics_path is None else str(pat_diagnostics_path)),
        config=config,
        rc2_generated_outputs=tuple(rc2_generated_outputs),
    )


def _rc2_output_state(run_dir: Path, *, sidecar_dirname: str) -> tuple[dict[str, str], str]:
    state: dict[str, str] = {}
    if not run_dir.exists():
        return state, sha256_json(state)

    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(run_dir).as_posix()
        if relative_path.startswith(f"{sidecar_dirname}/"):
            continue
        state[relative_path] = sha256_file(path)
    return state, sha256_json(state)


def run_sidecar(
    *,
    snapshot: SidecarSnapshot,
    options: SidecarOptions,
) -> SidecarRunResult | None:
    if not options.enabled:
        return None

    run_dir = Path(snapshot.out_dir)
    sidecar_root = run_dir / options.output_dirname
    rc2_state_before, rc2_digest_before = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)

    sink = ArtifactSink(sidecar_root, semantic_policy_version=SEMANTIC_POLICY_VERSION)
    sink.write_json("semantic_policy_version.json", semantic_policy_payload(), layer="layer0")

    path_channel = PathEvidenceChannel()
    path_result = path_channel.evaluate(
        config=snapshot.config,
        pat_diagnostics_path=snapshot.pat_diagnostics_path,
        pathyes_force_false=snapshot.pathyes_force_false_requested,
    )
    evidences = [] if path_result.evidence is None else [path_result.evidence]
    applicability_records = list(path_result.applicability_records)

    bridge = SCVBridge()
    bundle = bridge.bundle(
        run_id=snapshot.run_id,
        evidences=evidences,
        applicability_records=applicability_records,
    )
    sink.write_json("observation_bundle.json", asdict(bundle), layer="layer1")
    sink.write_jsonl("channel_evidence_path.jsonl", bundle_to_jsonl_rows(evidences), layer="layer1")

    _, rc2_digest_after = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)
    materialized_before_manifest = [
        *sink.materialized_outputs(),
        "sidecar_run_record.json",
    ]
    run_record = SidecarRunRecord(
        schema_version=SIDECAR_RUN_RECORD_SCHEMA_VERSION,
        run_id=snapshot.run_id,
        run_mode=snapshot.run_mode,
        output_root=str(sidecar_root),
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        enabled_channels=["path"],
        observation_count=len(bundle.observations),
        applicability_records=applicability_records,
        materialized_outputs=materialized_before_manifest,
        rc2_output_digest_before=rc2_digest_before,
        rc2_output_digest_after=rc2_digest_after,
        rc2_outputs_unchanged=rc2_digest_before == rc2_digest_after,
        bridge_diagnostics={
            **dict(bundle.bridge_diagnostics),
            "comparison_type": snapshot.comparison_type,
            "pathyes_mode_requested": snapshot.pathyes_mode_requested,
            "resource_profile": snapshot.resource_profile,
        },
    )
    sink.write_json("sidecar_run_record.json", asdict(run_record), layer="layer0")
    manifest_path, expected_output_digest = sink.write_generator_manifest(run_id=snapshot.run_id)

    rc2_state_after, rc2_digest_after_final = _rc2_output_state(run_dir, sidecar_dirname=options.output_dirname)
    if rc2_digest_before != rc2_digest_after_final or rc2_state_before != rc2_state_after:
        raise SidecarInvariantError("v3 sidecar mutated existing rc2 outputs")

    return SidecarRunResult(
        output_root=str(sidecar_root),
        materialized_outputs=[*sink.materialized_outputs(), manifest_path.name],
        expected_output_digest=expected_output_digest,
        rc2_outputs_unchanged=True,
    )

