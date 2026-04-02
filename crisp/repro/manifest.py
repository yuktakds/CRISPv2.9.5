from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from crisp.config.models import TargetConfig
from crisp.repro.hashing import (
    compute_compound_order_hash,
    compute_config_hash,
    compute_library_hash,
    compute_requirements_hash,
    compute_stageplan_hash,
    read_smiles_file,
    sha256_file,
)
from crisp.utils.jsonx import canonical_json_bytes


def _capture(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            cmd,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception:
        return None


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    target_case_id: str
    target_config_path: str
    structure_path: str
    library_path: str
    stageplan_path: str
    library_hash: str
    compound_order_hash: str
    staging_plan_hash: str
    structure_file_digest: str
    config_hash: str
    requirements_hash: str
    created_at_utc: str
    python_version: str
    platform: str
    uv_version: str | None
    git_version: str | None


@dataclass(frozen=True, slots=True)
class MefRunSidecarManifest:
    run_kind: Literal["mef_run"]
    run_id: str
    target_case_id: str
    target_config_path: str
    source_library_path: str
    report_path: str
    summary_path: str
    mef_pass_library_path: str
    mef_fail_library_path: str
    config_hash: str
    requirements_hash: str
    structure_validation_target_dependent: bool
    created_at_utc: str


@dataclass(frozen=True, slots=True)
class Phase1RunSidecarManifest:
    run_kind: Literal["phase1_run"]
    run_id: str
    parent_mef_run_id: str | None
    prefilter_report_path: str | None
    supplied_phase1_library_path: str
    effective_phase1_library_path: str
    mef_strategy: str
    report_config_hash: str | None
    report_requirements_hash: str | None
    current_config_hash: str
    current_requirements_hash: str
    prefilter_hashes_match: bool | None
    phase1_stage_accumulation_mode: str
    cpg_local_offsets_mode: str
    cpg_clash_mode: str
    cpg_global_sampler_mode: str
    created_at_utc: str


def build_run_manifest(
    *,
    run_id: str,
    repo_root: Path,
    config_path: Path,
    config: TargetConfig,
    library_path: Path,
    stageplan_path: Path,
) -> RunManifest:
    structure_path = config.resolve_structure_path(repo_root)
    if not library_path.exists():
        raise FileNotFoundError(f"Library file not found: {library_path}")
    if not stageplan_path.exists():
        raise FileNotFoundError(f"Stageplan file not found: {stageplan_path}")
    if not structure_path.exists():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    smiles_list = read_smiles_file(library_path)
    requirements_hash = compute_requirements_hash()

    return RunManifest(
        run_id=run_id,
        target_case_id=config.target_name,
        target_config_path=str(config_path),
        structure_path=str(structure_path),
        library_path=str(library_path),
        stageplan_path=str(stageplan_path),
        library_hash=compute_library_hash(library_path),
        compound_order_hash=compute_compound_order_hash(smiles_list),
        staging_plan_hash=compute_stageplan_hash(stageplan_path),
        structure_file_digest=sha256_file(structure_path),
        config_hash=compute_config_hash(config),
        requirements_hash=requirements_hash,
        created_at_utc=datetime.now(UTC).isoformat(),
        python_version=platform.python_version(),
        platform=platform.platform(),
        uv_version=_capture(["uv", "--version"]),
        git_version=_capture(["git", "--version"]),
    )


def write_run_manifest(path: str | Path, manifest: RunManifest) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json_bytes(asdict(manifest)))
    return out


def mef_sidecar_manifest_path(repo_root: Path, run_id: str) -> Path:
    return repo_root / "manifests" / "runs" / f"{run_id}.mef-run.json"


def phase1_sidecar_manifest_path(repo_root: Path, run_id: str) -> Path:
    return repo_root / "manifests" / "runs" / f"{run_id}.phase1-run.json"


def build_mef_run_sidecar_manifest(
    *,
    run_id: str,
    config_path: Path,
    config: TargetConfig,
    library_path: Path,
    report_path: Path,
    summary_path: Path,
    mef_pass_library_path: Path,
    mef_fail_library_path: Path,
    config_hash: str,
    requirements_hash: str,
) -> MefRunSidecarManifest:
    return MefRunSidecarManifest(
        run_kind="mef_run",
        run_id=run_id,
        target_case_id=config.target_name,
        target_config_path=str(config_path),
        source_library_path=str(library_path),
        report_path=str(report_path),
        summary_path=str(summary_path),
        mef_pass_library_path=str(mef_pass_library_path),
        mef_fail_library_path=str(mef_fail_library_path),
        config_hash=config_hash,
        requirements_hash=requirements_hash,
        structure_validation_target_dependent=True,
        created_at_utc=datetime.now(UTC).isoformat(),
    )


def build_phase1_run_sidecar_manifest(
    *,
    run_id: str,
    supplied_phase1_library_path: Path,
    effective_phase1_library_path: Path,
    mef_strategy: str,
    current_config_hash: str,
    current_requirements_hash: str,
    parent_mef_run_id: str | None = None,
    prefilter_report_path: Path | None = None,
    report_config_hash: str | None = None,
    report_requirements_hash: str | None = None,
    prefilter_hashes_match: bool | None = None,
    phase1_stage_accumulation_mode: str,
    cpg_local_offsets_mode: str,
    cpg_clash_mode: str,
    cpg_global_sampler_mode: str,
) -> Phase1RunSidecarManifest:
    return Phase1RunSidecarManifest(
        run_kind="phase1_run",
        run_id=run_id,
        parent_mef_run_id=parent_mef_run_id,
        prefilter_report_path=(
            None if prefilter_report_path is None else str(prefilter_report_path)
        ),
        supplied_phase1_library_path=str(supplied_phase1_library_path),
        effective_phase1_library_path=str(effective_phase1_library_path),
        mef_strategy=mef_strategy,
        report_config_hash=report_config_hash,
        report_requirements_hash=report_requirements_hash,
        current_config_hash=current_config_hash,
        current_requirements_hash=current_requirements_hash,
        prefilter_hashes_match=prefilter_hashes_match,
        phase1_stage_accumulation_mode=phase1_stage_accumulation_mode,
        cpg_local_offsets_mode=cpg_local_offsets_mode,
        cpg_clash_mode=cpg_clash_mode,
        cpg_global_sampler_mode=cpg_global_sampler_mode,
        created_at_utc=datetime.now(UTC).isoformat(),
    )


def write_sidecar_manifest(
    path: str | Path,
    manifest: MefRunSidecarManifest | Phase1RunSidecarManifest,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json_bytes(asdict(manifest)))
    return out
