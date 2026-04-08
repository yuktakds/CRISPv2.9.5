"""Phase 1 実行パイプライン。

§4 アーキテクチャに従い、MEF → CPG → Sensors → SCV → Staging Policy を順次実行する。

改修:
  PERF-01: 蛋白質構造を 1 run で 1 回だけ load
  PERF-02: TargetConfig を library 実行で 1 回だけ load
  PERF-03: requirements_hash を 1 run で 1 回だけ計算
  PERF-04: ProteinROI (KDTree) を 1 run で 1 回だけ構築
  PERF-05: コンフォーマをステージ間で再利用
  DEV-02: should_stop による早期停止の統合
  DEV-03: target_class フィールドの追加
  BUG-01: ステージ間での feasible poses 蓄積
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from crisp.config.loader import load_target_config
from crisp.config.models import TargetConfig
from crisp.cpg.engine import (
    LigandConformers,
    ProteinROI,
    _resolve_clash_mode,
    _resolve_global_sampler_mode,
    _resolve_local_offsets_mode,
    run_cpg,
)
from crisp.cpg.structure import load_protein_geometry
from crisp.evidence.writer import write_evidence_artifact
from crisp.mef.filter import run_mef
from crisp.models.runtime import (
    AnchoringObservation,
    CompoundRunResult,
    ExplorationLog,
    FeasiblePose,
    MefResult,
    Phase1Evaluation,
    ProteinGeometry,
    SearchControlAction,
    SensorVerdict,
    Verdict,
    WarheadMatch,
)
from crisp.repro.hashing import (
    compute_config_hash,
    compute_input_hash,
    compute_requirements_hash,
    parse_smiles_library,
)
from crisp.reason_codes import (
    UNCLEAR_EXPLORATION_LIMIT_REACHED,
    UNCLEAR_INSUFFICIENT_FEASIBLE_POSES,
)
from crisp.repro.manifest import (
    build_phase1_run_sidecar_manifest,
    build_run_manifest,
    mef_sidecar_manifest_path,
    phase1_sidecar_manifest_path,
    write_run_manifest,
    write_sidecar_manifest,
)
from crisp.scv.core import scv_anchoring, scv_integrate, scv_offtarget
from crisp.sensors.anchoring import compute_anchoring_observation
from crisp.sensors.offtarget import compute_offtarget_observation
from crisp.staging.policy import decide_action, scv_terminal_policy, should_stop

# --- Windows ファイル名安全化 ---

_WINDOWS_RESERVED_BASENAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})
STAGE_ACCUMULATION_MODE_CURRENT = "current-accumulate-all-stages"
STAGE_ACCUMULATION_MODE_LEGACY_FINAL_STAGE_ONLY = "legacy-final-stage-only"
STAGE_ACCUMULATION_MODE_ENV = "PHASE1_STAGE_ACCUMULATION_MODE"


def _sanitize_filename(value: str, *, default: str = "compound") -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(". ")
    if not sanitized:
        sanitized = default
    if sanitized.upper() in _WINDOWS_RESERVED_BASENAMES:
        sanitized = f"_{sanitized}"
    return sanitized[:80]


def _artifact_file_stem(*, index: int, name: str) -> str:
    safe_name = _sanitize_filename(name)
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    return f"{index:06d}_{safe_name}_{digest}"


def _write_smiles_library(path: Path, entries: list[tuple[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{smiles} {name}\n" for smiles, name in entries)
    path.write_text(body, encoding="utf-8")
    return path


def _resolve_stage_accumulation_mode(mode: str | None = None) -> str:
    selected = (
        os.environ.get(
            STAGE_ACCUMULATION_MODE_ENV,
            STAGE_ACCUMULATION_MODE_CURRENT,
        )
        if mode is None
        else mode
    )
    valid_modes = {
        STAGE_ACCUMULATION_MODE_CURRENT,
        STAGE_ACCUMULATION_MODE_LEGACY_FINAL_STAGE_ONLY,
    }
    if selected not in valid_modes:
        valid = ", ".join(sorted(valid_modes))
        raise ValueError(
            f"Unsupported {STAGE_ACCUMULATION_MODE_ENV}={selected!r}; expected one of: {valid}"
        )
    return selected


def _resolve_phase1_runtime_modes() -> dict[str, str]:
    return {
        "phase1_stage_accumulation_mode": _resolve_stage_accumulation_mode(),
        "cpg_local_offsets_mode": _resolve_local_offsets_mode(),
        "cpg_clash_mode": _resolve_clash_mode(),
        "cpg_global_sampler_mode": _resolve_global_sampler_mode(),
    }


# --- Evidence 構築 ---


def _determine_target_class(config: TargetConfig, phase1: Phase1Evaluation) -> str:
    """§12.1: target_class の決定 (DEV-03)。"""
    if phase1.final_verdict == Verdict.PASS:
        return "ON_TARGET"
    return "OFF_TARGET"


def _sensor_reason(verdict: SensorVerdict | None) -> Any:
    if verdict is None:
        return None
    return verdict.reason_or_meta


def _derive_core_reason(phase1: Phase1Evaluation) -> Any:
    if phase1.v_anchor.verdict == Verdict.FAIL:
        return phase1.v_anchor.reason_or_meta
    if phase1.v_offtarget is not None and phase1.v_offtarget.verdict == Verdict.FAIL:
        return phase1.v_offtarget.reason_or_meta
    if phase1.v_anchor.verdict == Verdict.UNCLEAR:
        return phase1.v_anchor.reason_or_meta
    if phase1.v_offtarget is not None and phase1.v_offtarget.verdict == Verdict.UNCLEAR:
        return phase1.v_offtarget.reason_or_meta
    return None


def _build_evidence(
    result: CompoundRunResult,
    config_hash: str,
    requirements_hash: str,
    config: TargetConfig,
) -> dict[str, Any]:
    """Evidence Artifact を構築する (§12)。"""
    mef = result.mef
    phase1 = result.phase1
    input_hash = compute_input_hash(mef.smiles, requirements_hash)
    runtime_modes = _resolve_phase1_runtime_modes()

    evidence: dict[str, Any] = {
        "verdict": "FAIL" if phase1 is None else phase1.final_verdict.value,
        "reason": mef.reason if phase1 is None else phase1.final_reason,
        "v_core": None if phase1 is None else phase1.v_core.value,
        "core_reason": None if phase1 is None else _derive_core_reason(phase1),
        "anchoring_reason": None if phase1 is None else _sensor_reason(phase1.v_anchor),
        "offtarget_reason": None if phase1 is None else _sensor_reason(phase1.v_offtarget),
        "stage_id_found": None if phase1 is None else phase1.exploration_log.stage_id_found,
        "translation_type_found": (
            None if phase1 is None else phase1.exploration_log.translation_type_found
        ),
        "first_feasible_trial": (
            None if phase1 is None else phase1.exploration_log.first_feasible_trial
        ),
        "first_feasible_stage_id": (
            None if phase1 is None else phase1.exploration_log.first_feasible_stage_id
        ),
        "first_feasible_translation_type": (
            None if phase1 is None else phase1.exploration_log.first_feasible_translation_type
        ),
        "first_feasible_conformer_id": (
            None if phase1 is None else phase1.exploration_log.first_feasible_conformer_id
        ),
        "first_feasible_global_index": (
            None if phase1 is None else phase1.exploration_log.first_feasible_global_index
        ),
        "best_target_distance_at_first_feasible": (
            None
            if phase1 is None else phase1.exploration_log.best_target_distance_at_first_feasible
        ),
        "trial_number_at_first_feasible": (
            None if phase1 is None else phase1.exploration_log.trial_number_at_first_feasible
        ),
        "conformer_index": (
            None if phase1 is None else phase1.exploration_log.conformer_index
        ),
        "global_prefix_size_used": (
            None if phase1 is None else phase1.exploration_log.global_prefix_size_used
        ),
        "global_q_index": (
            None if phase1 is None else phase1.exploration_log.global_q_index
        ),
        "global_translation_index": (
            None if phase1 is None else phase1.exploration_log.global_translation_index
        ),
        "rotation_index": (
            None if phase1 is None else phase1.exploration_log.rotation_index
        ),
        "pathway": config.pathway,
        "meta": {
            "requirements_hash": requirements_hash,
            "input_hash": input_hash,
            "config_hash": config_hash,
            **runtime_modes,
        },
        "mef": {
            "passed": mef.passed,
            "reason": mef.reason,
            "heavy_atom_count": mef.heavy_atom_count,
            "rotatable_bonds": mef.rotatable_bonds,
            "matched_smarts": [
                {
                    "smarts_index": m.smarts_index,
                    "pattern": m.pattern,
                    "mapped_atoms": list(m.mapped_atoms),
                }
                for m in mef.matched_smarts
            ],
            "warhead_atoms_union": list(mef.warhead_atoms_union),
        },
    }
    if phase1 is None:
        return evidence

    # DEV-03: target_class 追加
    evidence["target_class"] = _determine_target_class(config, phase1)

    exploration_log = phase1.exploration_log
    evidence["sensors"] = {
        "anchoring": {
            "verdict": phase1.v_anchor.verdict.value,
            "reason_or_meta": phase1.v_anchor.reason_or_meta,
            "best_target_distance": phase1.anchoring.best_target_distance,
            "witness_pose": (
                None if phase1.anchoring.best_pose is None else {
                    "pose_id": phase1.anchoring.best_pose.pose_id,
                    "conformer_id": phase1.anchoring.best_pose.conformer_id,
                    "trial_number": phase1.anchoring.best_pose.trial_number,
                    "stage_id": phase1.anchoring.best_pose.stage_id,
                    "translation_type": phase1.anchoring.best_pose.translation_type,
                }
            ),
            "warhead_provenance": {
                "matched_smarts": [
                    {
                        "smarts_index": m.smarts_index,
                        "pattern": m.pattern,
                        "mapped_atoms": list(m.mapped_atoms),
                    }
                    for m in phase1.anchoring.matched_smarts
                ],
                "warhead_atoms_union": list(phase1.anchoring.warhead_atoms_union),
                "argmin_target": (
                    None if phase1.anchoring.argmin_target is None else {
                        "atom_index": phase1.anchoring.argmin_target.atom_index,
                        "smarts_index": phase1.anchoring.argmin_target.smarts_index,
                        "smarts_pattern": phase1.anchoring.argmin_target.smarts_pattern,
                        "tiebreak_key": list(phase1.anchoring.argmin_target.tiebreak_key),
                    }
                ),
            },
            "top_k_poses": list(phase1.anchoring.top_k_poses),
        },
    }

    if phase1.offtarget is not None and phase1.v_offtarget is not None:
        evidence["sensors"]["offtarget"] = {
            "verdict": phase1.v_offtarget.verdict.value,
            "reason_or_meta": phase1.v_offtarget.reason_or_meta,
            "best_offtarget_distance": phase1.offtarget.best_offtarget_distance,
            "closest_residue": phase1.offtarget.closest_offtarget_residue,
            "argmin_offtarget": (
                None if phase1.offtarget.argmin_offtarget is None else {
                    "atom_index": phase1.offtarget.argmin_offtarget.atom_index,
                    "smarts_index": phase1.offtarget.argmin_offtarget.smarts_index,
                    "smarts_pattern": phase1.offtarget.argmin_offtarget.smarts_pattern,
                    "tiebreak_key": list(phase1.offtarget.argmin_offtarget.tiebreak_key),
                }
            ),
        }

    evidence["exploration_log"] = {
        "total_trials": exploration_log.total_trials,
        "feasible_count": exploration_log.feasible_count,
        "c1_rejected": exploration_log.c1_rejected,
        "early_stopped": exploration_log.early_stopped,
        "stopped_at_trial": exploration_log.stopped_at_trial,
        "early_stop_reason": exploration_log.early_stop_reason,
        "active_site_anchor_xyz": list(exploration_log.active_site_anchor_xyz),
        "stage_id_found": exploration_log.stage_id_found,
        "translation_type_found": exploration_log.translation_type_found,
        "first_feasible_trial": exploration_log.first_feasible_trial,
        "first_feasible_stage_id": exploration_log.first_feasible_stage_id,
        "first_feasible_translation_type": exploration_log.first_feasible_translation_type,
        "first_feasible_conformer_id": exploration_log.first_feasible_conformer_id,
        "first_feasible_global_index": exploration_log.first_feasible_global_index,
        "best_target_distance_at_first_feasible": (
            exploration_log.best_target_distance_at_first_feasible
        ),
        "trial_number_at_first_feasible": exploration_log.trial_number_at_first_feasible,
        "conformer_index": exploration_log.conformer_index,
        "global_prefix_size_used": exploration_log.global_prefix_size_used,
        "global_q_index": exploration_log.global_q_index,
        "global_translation_index": exploration_log.global_translation_index,
        "rotation_index": exploration_log.rotation_index,
        "sampling": exploration_log.sampling_params,
    }
    return evidence


# --- 単一化合物評価 ---

def evaluate_single_compound(
    *,
    config: TargetConfig,
    config_hash: str,
    requirements_hash: str,
    protein: ProteinGeometry,
    roi: ProteinROI,
    smiles: str,
    repo_root: Path,
    skip_pdb_check: bool = False,
    mef_result: MefResult | None = None,
) -> CompoundRunResult:
    """1 化合物に対する Phase 1 評価を実行する。

    蛋白質構造・ROI・config・hash は外部からキャッシュ注入する (PERF-01〜04)。
    """
    mef = (
        run_mef(smiles, config, repo_root, skip_pdb_check=skip_pdb_check)
        if mef_result is None else mef_result
    )

    if mef.smiles != smiles:
        raise ValueError("Precomputed MEF result does not match the requested SMILES")

    if not mef.passed:
        result = CompoundRunResult(mef=mef, phase1=None, evidence={})
        evidence = _build_evidence(result, config_hash, requirements_hash, config)
        return CompoundRunResult(mef=mef, phase1=None, evidence=evidence)

    # PERF-05: コンフォーマを 1 化合物で 1 回だけ生成
    try:
        ligand = LigandConformers.from_smiles(smiles, config)
    except RuntimeError:
        # コンフォーマ生成失敗は MEF 通過後なので FAIL_NO_FEASIBLE として扱う
        empty_log = ExplorationLog(
            total_trials=0, feasible_count=0, c1_rejected=0,
            early_stopped=True, stopped_at_trial=0,
            active_site_anchor_xyz=tuple(float(x) for x in protein.active_site_anchor_xyz),
            anchor_derivation=protein.anchor_derivation,
            anchor_source_atoms=protein.anchor_source_atoms,
            sampling_params={}, early_stop_reason="FAIL_NO_FEASIBLE",
        )
        phase1 = Phase1Evaluation(
            anchoring=AnchoringObservation(
                best_target_distance=math.inf, best_pose=None, poses_evaluated=0,
                matched_smarts=mef.matched_smarts, warhead_atoms_union=mef.warhead_atoms_union,
                argmin_target=None,
            ),
            offtarget=None, exploration_log=empty_log,
            v_anchor=SensorVerdict(Verdict.UNCLEAR, UNCLEAR_INSUFFICIENT_FEASIBLE_POSES),
            v_offtarget=None, v_core=Verdict.UNCLEAR,
            action=SearchControlAction.FINALIZE_BY_TERMINAL_POLICY,
            final_verdict=Verdict.FAIL, final_reason="FAIL_NO_FEASIBLE",
        )
        result = CompoundRunResult(mef=mef, phase1=phase1, evidence={})
        evidence = _build_evidence(result, config_hash, requirements_hash, config)
        return CompoundRunResult(mef=mef, phase1=phase1, evidence=evidence)

    last_phase1: Phase1Evaluation | None = None
    final_verdict = Verdict.UNCLEAR
    final_reason: str | dict[str, Any] | None = None
    stage_accumulation_mode = _resolve_stage_accumulation_mode()

    # current mode: BUG-01 修正として feasible poses をステージ間で蓄積する
    # replay mode: p1.0 strict replay のため final stage の評価だけを見る
    accumulated_poses: list[FeasiblePose] = []
    cumulative_trials = 0
    accumulated_c1_rejected = 0
    first_feasible_trial: int | None = None
    first_feasible_stage_id: int | None = None
    first_feasible_translation_type: str | None = None
    first_feasible_conformer_id: int | None = None
    first_feasible_global_index: int | None = None
    best_target_distance_at_first_feasible: float | None = None
    trial_number_at_first_feasible: int | None = None
    conformer_index: int | None = None
    global_prefix_size_used: int | None = None
    global_q_index: int | None = None
    global_translation_index: int | None = None
    rotation_index: int | None = None

    for stage_id in range(1, int(config.staging.max_stage) + 1):
        stage_trial_offset = cumulative_trials
        cpg = run_cpg(
            config=config,
            protein=protein,
            roi=roi,
            ligand=ligand,
            warhead_atoms_union=mef.warhead_atoms_union,
            stage_id=stage_id,
        )
        cumulative_trials += cpg.exploration_log.total_trials
        if (
            first_feasible_trial is None
            and cpg.exploration_log.first_feasible_trial is not None
        ):
            first_feasible_trial = (
                stage_trial_offset + cpg.exploration_log.first_feasible_trial
            )
            first_feasible_stage_id = cpg.exploration_log.first_feasible_stage_id
            first_feasible_translation_type = (
                cpg.exploration_log.first_feasible_translation_type
            )
            first_feasible_conformer_id = cpg.exploration_log.first_feasible_conformer_id
            first_feasible_global_index = cpg.exploration_log.first_feasible_global_index
            best_target_distance_at_first_feasible = (
                cpg.exploration_log.best_target_distance_at_first_feasible
            )
            trial_number_at_first_feasible = (
                stage_trial_offset + cpg.exploration_log.trial_number_at_first_feasible
                if cpg.exploration_log.trial_number_at_first_feasible is not None else None
            )
            conformer_index = cpg.exploration_log.conformer_index
            global_prefix_size_used = cpg.exploration_log.global_prefix_size_used
            global_q_index = cpg.exploration_log.global_q_index
            global_translation_index = cpg.exploration_log.global_translation_index
            rotation_index = cpg.exploration_log.rotation_index

        if stage_accumulation_mode == STAGE_ACCUMULATION_MODE_CURRENT:
            accumulated_poses.extend(cpg.feasible_poses)
            accumulated_c1_rejected += cpg.exploration_log.c1_rejected
            evaluation_feasible = tuple(accumulated_poses)
            evaluation_log = replace(
                cpg.exploration_log,
                total_trials=cumulative_trials,
                feasible_count=len(evaluation_feasible),
                c1_rejected=accumulated_c1_rejected,
            )
        else:
            evaluation_feasible = cpg.feasible_poses
            evaluation_log = cpg.exploration_log

        # Sensor 評価: current mode では全 stage 累積、replay mode では当該 stage のみ
        anchoring_obs = compute_anchoring_observation(
            feasible_poses=evaluation_feasible,
            target_xyz=protein.target_atom_xyz,
            matched_smarts=mef.matched_smarts,
            warhead_atoms_union=mef.warhead_atoms_union,
            top_k=int(config.pat.top_k_poses),
        )
        v_anchor = scv_anchoring(anchoring_obs, evaluation_log, config)

        offtarget_obs = None
        v_offtarget = None
        if config.pathway == "covalent":
            offtarget_obs = compute_offtarget_observation(
                feasible_poses=evaluation_feasible,
                offtarget_atoms=protein.offtarget_atoms,
                matched_smarts=mef.matched_smarts,
                warhead_atoms_union=mef.warhead_atoms_union,
            )
            v_offtarget = scv_offtarget(offtarget_obs, evaluation_log, config)
            v_core = scv_integrate([v_anchor.verdict, v_offtarget.verdict])
        else:
            v_core = scv_integrate([v_anchor.verdict])

        # DEV-02: should_stop による早期停止 (§11)
        if should_stop(anchoring_obs, offtarget_obs, config):
            final_verdict = Verdict.PASS
            final_reason = None
            action = SearchControlAction.FINALIZE_PASS
        else:
            action = decide_action(
                v_core=v_core,
                feasible_count=len(evaluation_feasible),
                best_target_distance=anchoring_obs.best_target_distance,
                config=config,
                stage_id=stage_id,
            )

            if action == SearchControlAction.FINALIZE_PASS:
                final_verdict = Verdict.PASS
                final_reason = None
            elif action == SearchControlAction.FINALIZE_FAIL:
                final_verdict = Verdict.FAIL
                if v_anchor.verdict == Verdict.FAIL:
                    final_reason = v_anchor.reason_or_meta
                elif v_offtarget is not None and v_offtarget.verdict == Verdict.FAIL:
                    final_reason = v_offtarget.reason_or_meta
                else:
                    final_reason = "FAIL_UNKNOWN"
            elif action == SearchControlAction.FINALIZE_BY_TERMINAL_POLICY:
                final_verdict, final_reason = scv_terminal_policy(
                    v_core=v_core,
                    feasible_count=len(evaluation_feasible),
                    best_target_distance=anchoring_obs.best_target_distance,
                    config=config,
                )
            else:
                final_verdict = Verdict.UNCLEAR
                final_reason = UNCLEAR_EXPLORATION_LIMIT_REACHED

        final_log = replace(
            evaluation_log,
            first_feasible_trial=first_feasible_trial,
            first_feasible_stage_id=first_feasible_stage_id,
            first_feasible_translation_type=first_feasible_translation_type,
            first_feasible_conformer_id=first_feasible_conformer_id,
            first_feasible_global_index=first_feasible_global_index,
            best_target_distance_at_first_feasible=best_target_distance_at_first_feasible,
            trial_number_at_first_feasible=trial_number_at_first_feasible,
            conformer_index=conformer_index,
            global_prefix_size_used=global_prefix_size_used,
            global_q_index=global_q_index,
            global_translation_index=global_translation_index,
            rotation_index=rotation_index,
        )
        if anchoring_obs.best_pose is not None:
            final_log = replace(
                final_log,
                stage_id_found=anchoring_obs.best_pose.stage_id,
                translation_type_found=anchoring_obs.best_pose.translation_type,
            )

        last_phase1 = Phase1Evaluation(
            anchoring=anchoring_obs,
            offtarget=offtarget_obs,
            exploration_log=final_log,
            v_anchor=v_anchor,
            v_offtarget=v_offtarget,
            v_core=v_core,
            action=action,
            final_verdict=final_verdict,
            final_reason=final_reason,
        )

        if action != SearchControlAction.CONTINUE:
            break

    if last_phase1 is None:
        raise RuntimeError("Phase1 evaluation failed to produce any stage result")

    result = CompoundRunResult(mef=mef, phase1=last_phase1, evidence={})
    evidence = _build_evidence(result, config_hash, requirements_hash, config)
    return CompoundRunResult(mef=mef, phase1=last_phase1, evidence=evidence)


# --- CLI エントリポイント ---

def run_phase1_single(*, repo_root: Path, config_path: Path, smiles: str) -> CompoundRunResult:
    """単一化合物の Phase 1 評価。"""
    config = load_target_config(config_path)
    config_hash = compute_config_hash(config)
    requirements_hash = compute_requirements_hash()
    protein = load_protein_geometry(repo_root, config)
    roi = ProteinROI.from_geometry(protein, config)

    return evaluate_single_compound(
        config=config, config_hash=config_hash, requirements_hash=requirements_hash,
        protein=protein, roi=roi, smiles=smiles, repo_root=repo_root,
    )


# --- 進捗表示ユーティリティ ---

def _format_clock(seconds: float | None) -> str:
    if seconds is None:
        return "--:--:--"
    value = max(0, int(round(seconds)))
    return f"{value // 3600:02d}:{(value % 3600) // 60:02d}:{value % 60:02d}"


def _should_emit_progress(
    *, completed: int, total: int, now: float, last_report: float,
    progress_every: int, progress_seconds: float,
) -> bool:
    if completed <= 0:
        return False
    if completed >= total:
        return True
    if progress_every > 0 and completed % progress_every == 0:
        return True
    return progress_seconds > 0 and (now - last_report) >= progress_seconds


def _emit_progress_line(
    *, run_id: str, completed: int, total: int, elapsed: float,
    summary: dict[str, int], last_name: str, last_verdict: str,
) -> None:
    eta = None if completed <= 0 or elapsed <= 0 else (total - completed) * elapsed / completed
    pct = 100.0 if total == 0 else (completed / total) * 100.0
    seconds_per_compound = 0.0 if completed <= 0 else elapsed / completed
    print(
        f"[progress] run_id={run_id} "
        f"completed={completed}/{total} ({pct:5.1f}%) "
        f"elapsed={_format_clock(elapsed)} eta={_format_clock(eta)} "
        f"rate={seconds_per_compound:.2f} s/cmp "
        f"PASS={summary['PASS']} FAIL={summary['FAIL']} UNCLEAR={summary['UNCLEAR']} "
        f"last={last_name}:{last_verdict}",
        file=sys.stderr, flush=True,
    )


def _load_prefilter_report(
    prefilter_report_path: Path,
) -> dict[str, Any]:
    pass_entries: list[tuple[str, str]] = []
    pass_mef_results: list[MefResult] = []
    total_rows = 0
    mef_run_id: str | None = None
    report_config_hash: str | None = None
    report_requirements_hash: str | None = None

    for line_no, raw_line in enumerate(
        prefilter_report_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue

        row = json.loads(line)
        total_rows += 1
        required = {
            "mef_run_id",
            "smiles",
            "name",
            "passed",
            "config_hash",
            "requirements_hash",
        }
        if not required.issubset(row):
            raise ValueError(
                f"Invalid prefilter report row at line {line_no}: "
                "expected mef_run_id, smiles, name, passed, config_hash, "
                "and requirements_hash fields"
            )
        row_run_id = str(row["mef_run_id"])
        row_config_hash = str(row["config_hash"])
        row_requirements_hash = str(row["requirements_hash"])
        if mef_run_id is None:
            mef_run_id = row_run_id
            report_config_hash = row_config_hash
            report_requirements_hash = row_requirements_hash
        elif (
            row_run_id != mef_run_id
            or row_config_hash != report_config_hash
            or row_requirements_hash != report_requirements_hash
        ):
            raise ValueError(
                f"Invalid prefilter report row at line {line_no}: "
                "verification metadata is inconsistent within the report"
            )
        if row["passed"]:
            smiles = str(row["smiles"])
            name = str(row["name"])
            heavy_atom_count = row.get("heavy_atom_count")
            rotatable_bonds = row.get("rotatable_bonds")
            if heavy_atom_count is None or rotatable_bonds is None:
                raise ValueError(
                    f"Invalid PASS row at line {line_no}: "
                    "expected heavy_atom_count and rotatable_bonds"
                )
            matched_smarts = tuple(
                WarheadMatch(
                    smarts_index=int(match["smarts_index"]),
                    pattern=str(match["pattern"]),
                    mapped_atoms=tuple(int(atom) for atom in match["mapped_atoms"]),
                )
                for match in row.get("matched_smarts", [])
            )
            warhead_atoms_union = tuple(
                int(atom) for atom in row.get("warhead_atoms_union", [])
            )
            pass_entries.append((smiles, name))
            pass_mef_results.append(
                MefResult(
                    passed=True,
                    reason=None,
                    smiles=smiles,
                    heavy_atom_count=int(heavy_atom_count),
                    rotatable_bonds=int(rotatable_bonds),
                    matched_smarts=matched_smarts,
                    warhead_atoms_union=warhead_atoms_union,
                )
            )

    if mef_run_id is None or report_config_hash is None or report_requirements_hash is None:
        raise ValueError(
            "Prefilter report did not contain any verification metadata; rerun run-mef-library"
        )

    return {
        "path": str(prefilter_report_path),
        "mef_run_id": mef_run_id,
        "config_hash": report_config_hash,
        "requirements_hash": report_requirements_hash,
        "total_rows": total_rows,
        "passed_rows": len(pass_entries),
        "pass_entries": pass_entries,
        "pass_mef_results": pass_mef_results,
    }


def _load_parent_mef_manifest(
    *,
    repo_root: Path,
    mef_run_id: str,
) -> dict[str, Any]:
    manifest_path = mef_sidecar_manifest_path(repo_root, mef_run_id)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"MEF sidecar manifest not found for run_id '{mef_run_id}': {manifest_path}"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _rerun_mef_for_library(
    *,
    library_path: Path,
    config: TargetConfig,
    repo_root: Path,
) -> tuple[list[tuple[str, str]], list[MefResult]]:
    pass_entries: list[tuple[str, str]] = []
    pass_mef_results: list[MefResult] = []

    for smiles, name in parse_smiles_library(library_path):
        result = run_mef(smiles, config, repo_root, skip_pdb_check=True)
        if result.passed:
            pass_entries.append((smiles, name))
            pass_mef_results.append(result)

    return pass_entries, pass_mef_results


def _resolve_prefilter_strategy(
    *,
    repo_root: Path,
    config: TargetConfig,
    current_config_hash: str,
    current_requirements_hash: str,
    supplied_library_path: Path,
    library_entries: list[tuple[str, str]],
    prefilter_report_path: Path,
) -> dict[str, Any]:
    report = _load_prefilter_report(prefilter_report_path)
    hashes_match = (
        report["config_hash"] == current_config_hash
        and report["requirements_hash"] == current_requirements_hash
    )
    if hashes_match:
        if library_entries != report["pass_entries"]:
            raise ValueError(
                "Phase1 library does not match the PASS entries in the prefilter report"
            )
        return {
            "parent_mef_run_id": report["mef_run_id"],
            "prefilter": {
                "path": report["path"],
                "mef_run_id": report["mef_run_id"],
                "report_config_hash": report["config_hash"],
                "report_requirements_hash": report["requirements_hash"],
                "current_config_hash": current_config_hash,
                "current_requirements_hash": current_requirements_hash,
                "total_rows": report["total_rows"],
                "passed_rows": report["passed_rows"],
                "hashes_match": True,
                "mef_strategy": "verified-skip",
            },
            "effective_entries": report["pass_entries"],
            "effective_mef_results": report["pass_mef_results"],
            "effective_library_path": supplied_library_path,
        }

    parent_manifest = _load_parent_mef_manifest(
        repo_root=repo_root,
        mef_run_id=report["mef_run_id"],
    )
    source_library_path = Path(parent_manifest["source_library_path"])
    effective_entries, effective_mef_results = _rerun_mef_for_library(
        library_path=source_library_path,
        config=config,
        repo_root=repo_root,
    )
    return {
        "parent_mef_run_id": report["mef_run_id"],
        "prefilter": {
            "path": report["path"],
            "mef_run_id": report["mef_run_id"],
            "report_config_hash": report["config_hash"],
            "report_requirements_hash": report["requirements_hash"],
            "current_config_hash": current_config_hash,
            "current_requirements_hash": current_requirements_hash,
            "total_rows": report["total_rows"],
            "passed_rows": report["passed_rows"],
            "hashes_match": False,
            "mef_strategy": "recomputed",
            "recomputed_from_source_library": str(source_library_path),
        },
        "effective_entries": effective_entries,
        "effective_mef_results": effective_mef_results,
        "effective_library_path": source_library_path,
    }


# --- ライブラリ実行 ---

def run_phase1_library(
    *, repo_root: Path, config_path: Path, library_path: Path, run_id: str,
    stageplan_path: Path, prefilter_report_path: Path | None = None,
    show_progress: bool = True,
    progress_every: int = 25, progress_seconds: float = 15.0,
) -> dict[str, Any]:
    """ライブラリ全体の Phase 1 評価を実行する。

    PERF-01〜04: config・蛋白質構造・ROI・hash を 1 回だけ構築し全化合物で共有。
    """
    # --- 1 回だけ構築するリソース (PERF-01〜04) ---
    supplied_entries = parse_smiles_library(library_path)
    config = load_target_config(config_path)
    config_hash = compute_config_hash(config)
    requirements_hash = compute_requirements_hash()
    runtime_modes = _resolve_phase1_runtime_modes()

    prefilter = None
    parent_mef_run_id = None
    effective_entries = supplied_entries
    effective_mef_results: list[MefResult] | None = None
    mef_strategy = "rerun"
    effective_library_path = library_path

    if prefilter_report_path is not None:
        resolution = _resolve_prefilter_strategy(
            repo_root=repo_root,
            config=config,
            current_config_hash=config_hash,
            current_requirements_hash=requirements_hash,
            supplied_library_path=library_path,
            library_entries=supplied_entries,
            prefilter_report_path=prefilter_report_path,
        )
        prefilter = resolution["prefilter"]
        parent_mef_run_id = resolution["parent_mef_run_id"]
        effective_entries = resolution["effective_entries"]
        effective_mef_results = resolution["effective_mef_results"]
        mef_strategy = prefilter["mef_strategy"]

    out_root = repo_root / "outputs" / run_id
    evidence_root = out_root / "evidence"
    libraries_root = out_root / "libraries"
    if prefilter is not None and prefilter["hashes_match"] is False:
        effective_library_path = _write_smiles_library(
            libraries_root / "mef_pass.recomputed.smi",
            effective_entries,
        )

    protein = load_protein_geometry(repo_root, config)
    roi = ProteinROI.from_geometry(protein, config)

    manifest = build_run_manifest(
        run_id=run_id, repo_root=repo_root, config_path=config_path,
        config=config, library_path=effective_library_path, stageplan_path=stageplan_path,
    )
    manifest_path = repo_root / "manifests" / "runs" / f"{run_id}.json"
    write_run_manifest(manifest_path, manifest)
    phase1_sidecar_path = phase1_sidecar_manifest_path(repo_root, run_id)
    write_sidecar_manifest(
        phase1_sidecar_path,
        build_phase1_run_sidecar_manifest(
            run_id=run_id,
            config=config,
            supplied_phase1_library_path=library_path,
            effective_phase1_library_path=effective_library_path,
            mef_strategy=mef_strategy,
            current_config_hash=config_hash,
            current_requirements_hash=requirements_hash,
            parent_mef_run_id=parent_mef_run_id,
            prefilter_report_path=prefilter_report_path,
            report_config_hash=(
                None if prefilter is None else prefilter["report_config_hash"]
            ),
            report_requirements_hash=(
                None if prefilter is None else prefilter["report_requirements_hash"]
            ),
            prefilter_hashes_match=(
                None if prefilter is None else prefilter["hashes_match"]
            ),
            phase1_stage_accumulation_mode=runtime_modes["phase1_stage_accumulation_mode"],
            cpg_local_offsets_mode=runtime_modes["cpg_local_offsets_mode"],
            cpg_clash_mode=runtime_modes["cpg_clash_mode"],
            cpg_global_sampler_mode=runtime_modes["cpg_global_sampler_mode"],
        ),
    )

    evidence_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, int] = {"PASS": 0, "FAIL": 0, "UNCLEAR": 0}
    records: list[dict[str, Any]] = []
    total = len(effective_entries)

    started = time.monotonic()
    last_report = started

    if show_progress:
        print(
            f"[progress] run_id={run_id} starting total_compounds={total}",
            file=sys.stderr, flush=True,
        )

    for index, (smiles, name) in enumerate(effective_entries, start=1):
        mef_result = None
        if effective_mef_results is not None:
            mef_result = effective_mef_results[index - 1]
        result = evaluate_single_compound(
            config=config,
            config_hash=config_hash,
            requirements_hash=requirements_hash,
            protein=protein,
            roi=roi,
            smiles=smiles,
            repo_root=repo_root,
            skip_pdb_check=True,  # MEF-06 は初回 load_protein_geometry で検証済み
            mef_result=mef_result,
        )
        verdict = result.evidence["verdict"]
        summary[verdict] += 1
        artifact_stem = _artifact_file_stem(index=index, name=name)
        evidence_path = write_evidence_artifact(
            evidence_root / f"{artifact_stem}.json", result.evidence
        )
        records.append({
            "name": name, "smiles": smiles, "verdict": verdict,
            "reason": result.evidence.get("reason"),
            "evidence_path": str(evidence_path), "artifact_id": artifact_stem,
        })

        now = time.monotonic()
        if show_progress and _should_emit_progress(
            completed=index, total=total, now=now, last_report=last_report,
            progress_every=progress_every, progress_seconds=progress_seconds,
        ):
            _emit_progress_line(
                run_id=run_id, completed=index, total=total,
                elapsed=now - started, summary=summary,
                last_name=name, last_verdict=verdict,
            )
            last_report = now

    summary_path = repo_root / "outputs" / run_id / "summary.json"
    write_evidence_artifact(
        summary_path,
        {
            "run_id": run_id,
            "summary": summary,
            "records": records,
            "mef_strategy": mef_strategy,
            "effective_library_path": str(effective_library_path),
            "prefilter": prefilter,
            "runtime_modes": runtime_modes,
        },
    )
    elapsed = time.monotonic() - started
    payload = {
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "sidecar_manifest_path": str(phase1_sidecar_path),
        "summary_path": str(summary_path),
        "summary": summary,
        "mef_strategy": mef_strategy,
        "effective_library_path": str(effective_library_path),
        "prefilter": prefilter,
        "runtime_modes": runtime_modes,
        "progress": {
            "total_compounds": total,
            "elapsed_seconds": elapsed,
            "average_seconds_per_compound": None if total == 0 else elapsed / total,
        },
    }
    if show_progress:
        print(
            f"[progress] run_id={run_id} finished total_compounds={total} "
            f"elapsed={_format_clock(elapsed)} PASS={summary['PASS']} "
            f"FAIL={summary['FAIL']} UNCLEAR={summary['UNCLEAR']}",
            file=sys.stderr, flush=True,
        )
    return payload
