"""CPG: Constrained Placement Generation (§7)。

責務: 候補 pose 集合の生成と致命的衝突棄却 (C1)。
閾値判定は行わない (§4.1)。

改修:
  PERF-04: ProteinGeometry を外部から注入し KDTree を 1 回構築
  PERF-05: コンフォーマを外部から渡せるようにしステージ間で再利用
  PERF-06: _is_feasible_pose をベクトル化
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from scipy.spatial import cKDTree

from crisp.config.models import TargetConfig
from crisp.cpg.geometry import (
    quaternion_to_matrix,
    shoemake_quaternions,
    sobol_points_in_ball,
)
from crisp.cpg.structure import BONDI_VDW, DEFAULT_VDW
from crisp.models.runtime import ExplorationLog, FeasiblePose, ProteinGeometry

LOCAL_OFFSETS_MODE_CURRENT = "current"
LOCAL_OFFSETS_MODE_LEGACY_SHELL = "legacy-shell"
LOCAL_OFFSETS_MODE_ENV = "CRISP_LOCAL_OFFSETS_MODE"
CLASH_MODE_CURRENT = "current"
CLASH_MODE_LEGACY_LOOP = "legacy-loop"
CLASH_MODE_ENV = "CRISP_CLASH_MODE"
GLOBAL_SAMPLER_MODE_CURRENT = "current"
GLOBAL_SAMPLER_MODE_LEGACY_PREFIX = "legacy-prefix"
GLOBAL_SAMPLER_MODE_ENV = "CRISP_GLOBAL_SAMPLER_MODE"


@dataclass(frozen=True, slots=True)
class CpgResult:
    feasible_poses: tuple[FeasiblePose, ...]
    exploration_log: ExplorationLog
    protein_geometry: ProteinGeometry


@dataclass(slots=True)
class ProteinROI:
    """蛋白質の ROI（関心領域）キャッシュ (PERF-04)。
    1 target につき 1 回だけ構築する。
    """
    protein_xyz: np.ndarray
    protein_radii: np.ndarray
    kdtree: cKDTree
    max_protein_radius: float

    @classmethod
    def from_geometry(cls, protein: ProteinGeometry, config: TargetConfig) -> ProteinROI:
        roi_margin = 6.0
        all_xyz = np.array([a.xyz for a in protein.protein_heavy_atoms], dtype=np.float64)
        all_radii = np.array([a.vdw_radius for a in protein.protein_heavy_atoms], dtype=np.float64)
        # ROI フィルタ: anchor 近傍のみ保持
        distances = np.linalg.norm(
            all_xyz - protein.active_site_anchor_xyz[np.newaxis, :], axis=1
        )
        keep = distances <= (float(config.search_radius) + roi_margin)
        roi_xyz = all_xyz[keep]
        roi_radii = all_radii[keep]
        return cls(
            protein_xyz=roi_xyz,
            protein_radii=roi_radii,
            kdtree=cKDTree(roi_xyz),
            max_protein_radius=float(roi_radii.max()) if len(roi_radii) > 0 else DEFAULT_VDW,
        )


@dataclass(slots=True)
class LigandConformers:
    """リガンドのコンフォーマキャッシュ (PERF-05)。
    同一化合物に対しステージ間で再利用する。
    """
    mol: Chem.Mol
    conf_ids: list[int]
    coords_per_conf: dict[int, np.ndarray]
    heavy_atom_indices: np.ndarray
    ligand_radii: np.ndarray

    @classmethod
    def from_smiles(cls, smiles: str, config: TargetConfig) -> LigandConformers:
        mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
        params = AllChem.ETKDGv3()
        params.randomSeed = int(config.random_seed)
        params.pruneRmsThresh = 0.5
        params.useRandomCoords = False
        conf_ids = list(AllChem.EmbedMultipleConfs(
            mol, numConfs=int(config.sampling.n_conformers), params=params,
        ))
        if not conf_ids:
            raise RuntimeError("RDKit conformer generation failed")
        mol = Chem.RemoveHs(mol)

        # 各コンフォーマの座標をキャッシュ
        coords_per_conf: dict[int, np.ndarray] = {}
        for cid in conf_ids:
            conf = mol.GetConformer(cid)
            coords = np.zeros((mol.GetNumAtoms(), 3), dtype=np.float64)
            for i in range(mol.GetNumAtoms()):
                pos = conf.GetAtomPosition(i)
                coords[i] = (float(pos.x), float(pos.y), float(pos.z))
            coords_per_conf[cid] = coords

        # 重原子インデックス (昇順ソート: I-09)
        heavy_idx = np.array(
            sorted(a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() > 1),
            dtype=np.int64,
        )

        # vdW 半径
        radii = np.array([
            float(BONDI_VDW.get(a.GetSymbol().strip().upper(), DEFAULT_VDW))
            for a in mol.GetAtoms()
        ], dtype=np.float64)

        return cls(
            mol=mol,
            conf_ids=conf_ids,
            coords_per_conf=coords_per_conf,
            heavy_atom_indices=heavy_idx,
            ligand_radii=radii,
        )


def _global_trial_count(config: TargetConfig, stage_id: int) -> int:
    """ステージごとの global trial 予算 (UNDEF-02)。"""
    total = int(config.sampling.n_rotations) * int(config.sampling.n_translations)
    return max(1, int(np.ceil(total * stage_id / config.staging.max_stage)))


def _legacy_global_trial_count(config: TargetConfig, stage_id: int) -> int:
    total = int(config.sampling.n_rotations) * int(config.sampling.n_translations)
    return max(1, int(np.ceil(total * stage_id / config.staging.max_stage)))


def _legacy_global_offsets(config: TargetConfig, stage_id: int) -> np.ndarray:
    n = _legacy_global_trial_count(config, stage_id)
    return sobol_points_in_ball(n=n, radius=float(config.search_radius), seed_offset=0)


def _legacy_global_quaternions(config: TargetConfig, stage_id: int) -> np.ndarray:
    n = _legacy_global_trial_count(config, stage_id)
    return shoemake_quaternions(n=n, seed_offset=0)


def _coords_transformed(
    coords: np.ndarray, quat: np.ndarray, translation: np.ndarray,
) -> np.ndarray:
    """座標変換: 重心中心化 → 回転 → 並進。float64 強制 (§13.1 R0)。"""
    rot = quaternion_to_matrix(quat)
    centered = coords - coords.mean(axis=0, keepdims=True)
    return (centered @ rot.T + translation).astype(np.float64)


def _current_clash_constraint(
    coords: np.ndarray,
    heavy_idx: np.ndarray,
    ligand_radii: np.ndarray,
    roi: ProteinROI,
    alpha: float,
) -> bool:
    """§7.3 C1 制約のベクトル化衝突判定 (PERF-06)。

    全重原子について KDTree で近傍を一括検索し、
    NumPy の距離計算で衝突を判定する。
    """
    heavy_coords = coords[heavy_idx]
    heavy_radii = ligand_radii[heavy_idx]
    max_cutoff = float(alpha) * (float(heavy_radii.max()) + roi.max_protein_radius)

    # 一括近傍検索
    neighbor_lists = roi.kdtree.query_ball_point(heavy_coords, r=max_cutoff)

    for local_idx, neighbors in enumerate(neighbor_lists):
        if not neighbors:
            continue
        neighbor_idx = np.array(neighbors, dtype=np.int64)
        # ベクトル化距離計算
        diffs = roi.protein_xyz[neighbor_idx] - heavy_coords[local_idx]
        distances = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))
        cutoffs = alpha * (heavy_radii[local_idx] + roi.protein_radii[neighbor_idx])
        if np.any(distances < cutoffs):
            return False
    return True


def _legacy_loop_clash_constraint(
    coords: np.ndarray,
    heavy_idx: np.ndarray,
    ligand_radii: np.ndarray,
    roi: ProteinROI,
    alpha: float,
) -> bool:
    if len(roi.protein_radii) == 0 or len(heavy_idx) == 0:
        return True
    max_cutoff = float(alpha) * float(ligand_radii[heavy_idx].max() + roi.protein_radii.max())
    heavy_coords = coords[heavy_idx]
    neighbor_lists = roi.kdtree.query_ball_point(heavy_coords, r=max_cutoff)
    for lig_local_idx, neighbors in enumerate(neighbor_lists):
        lig_idx = int(heavy_idx[lig_local_idx])
        lig_xyz = coords[lig_idx]
        lig_r = float(ligand_radii[lig_idx])
        for protein_idx in neighbors:
            distance = float(np.linalg.norm(lig_xyz - roi.protein_xyz[protein_idx]))
            cutoff = float(alpha) * (lig_r + float(roi.protein_radii[protein_idx]))
            if distance < cutoff:
                return False
    return True


def _resolve_local_offsets_mode(mode: str | None = None) -> str:
    selected = mode
    if selected is None:
        selected = os.environ.get(LOCAL_OFFSETS_MODE_ENV, LOCAL_OFFSETS_MODE_CURRENT)
    normalized = selected.strip().lower()
    if normalized not in {LOCAL_OFFSETS_MODE_CURRENT, LOCAL_OFFSETS_MODE_LEGACY_SHELL}:
        raise ValueError(f"Unsupported local offsets mode: {selected}")
    return normalized


def _resolve_clash_mode(mode: str | None = None) -> str:
    selected = mode
    if selected is None:
        selected = os.environ.get(CLASH_MODE_ENV, CLASH_MODE_CURRENT)
    normalized = selected.strip().lower()
    if normalized not in {CLASH_MODE_CURRENT, CLASH_MODE_LEGACY_LOOP}:
        raise ValueError(f"Unsupported clash mode: {selected}")
    return normalized


def _resolve_global_sampler_mode(mode: str | None = None) -> str:
    selected = mode
    if selected is None:
        selected = os.environ.get(
            GLOBAL_SAMPLER_MODE_ENV, GLOBAL_SAMPLER_MODE_CURRENT,
        )
    normalized = selected.strip().lower()
    if normalized not in {GLOBAL_SAMPLER_MODE_CURRENT, GLOBAL_SAMPLER_MODE_LEGACY_PREFIX}:
        raise ValueError(f"Unsupported global sampler mode: {selected}")
    return normalized


def _build_global_sampler(
    config: TargetConfig,
    stage_id: int,
    *,
    mode: str | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    selected_mode = _resolve_global_sampler_mode(mode)
    if selected_mode == GLOBAL_SAMPLER_MODE_LEGACY_PREFIX:
        offsets = _legacy_global_offsets(config, stage_id)
        quats = _legacy_global_quaternions(config, stage_id)
        return offsets, quats, len(offsets)
    n_global = _global_trial_count(config, stage_id)
    offsets = sobol_points_in_ball(
        n=n_global, radius=float(config.search_radius), seed_offset=0,
    )
    quats = shoemake_quaternions(n=n_global, seed_offset=0)
    return offsets, quats, n_global


def _passes_clash_constraint(
    coords: np.ndarray,
    heavy_idx: np.ndarray,
    ligand_radii: np.ndarray,
    roi: ProteinROI,
    alpha: float,
    *,
    mode: str | None = None,
) -> bool:
    selected_mode = _resolve_clash_mode(mode)
    if selected_mode == CLASH_MODE_LEGACY_LOOP:
        return _legacy_loop_clash_constraint(coords, heavy_idx, ligand_radii, roi, alpha)
    return _current_clash_constraint(coords, heavy_idx, ligand_radii, roi, alpha)


def _target_distance_for_pose(
    warhead_coords: np.ndarray,
    target_xyz: np.ndarray,
) -> float | None:
    if len(warhead_coords) == 0:
        return None
    diffs = warhead_coords - target_xyz[np.newaxis, :]
    distances = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))
    return float(distances.min())


def _build_local_translation(
    ligand_coords: np.ndarray,
    warhead_atoms_union: tuple[int, ...],
    target_xyz: np.ndarray,
    offset: np.ndarray,
) -> np.ndarray:
    """§7.6.1: warhead 基準の local rescue 並進。"""
    warhead_centroid = ligand_coords[np.array(warhead_atoms_union, dtype=np.int64)].mean(axis=0)
    return target_xyz + offset - warhead_centroid


def _legacy_shell_local_offsets(config: TargetConfig, n: int, stage_id: int) -> np.ndarray:
    if stage_id < config.translation.local_start_stage or n <= 0:
        return np.zeros((0, 3), dtype=np.float64)
    r_min = float(config.translation.local_min_radius)
    r_max = float(config.translation.local_max_radius)
    base = sobol_points_in_ball(n=n, radius=1.0, seed_offset=0)
    norms = np.linalg.norm(base, axis=1)
    norms = np.where(norms == 0, 1.0, norms)
    unit = base / norms[:, None]
    radii = np.linspace(r_min, r_max, num=n, endpoint=True, dtype=np.float64)
    return unit * radii[:, None]


def _current_local_offsets(config: TargetConfig, n: int, stage_id: int) -> np.ndarray:
    if stage_id < config.translation.local_start_stage or n <= 0:
        return np.zeros((0, 3), dtype=np.float64)
    r_max = float(config.translation.local_max_radius)
    return sobol_points_in_ball(
        n=n, radius=r_max, seed_offset=(stage_id - 1) * n,
    ).clip(-r_max, r_max)


def _local_offsets(
    config: TargetConfig, n: int, stage_id: int, *, mode: str | None = None,
) -> np.ndarray:
    """§7.6.3: local rescue のオフセット生成。"""
    selected_mode = _resolve_local_offsets_mode(mode)
    if selected_mode == LOCAL_OFFSETS_MODE_LEGACY_SHELL:
        return _legacy_shell_local_offsets(config, n, stage_id)
    return _current_local_offsets(config, n, stage_id)


def run_cpg(
    *,
    config: TargetConfig,
    protein: ProteinGeometry,
    roi: ProteinROI,
    ligand: LigandConformers,
    warhead_atoms_union: tuple[int, ...],
    stage_id: int,
) -> CpgResult:
    """CPG を実行する。

    蛋白質構造・ROI・リガンドコンフォーマは外部からキャッシュ注入する (PERF-01,04,05)。
    """
    global_sampler_mode = _resolve_global_sampler_mode()
    global_offsets, global_quats, n_global = _build_global_sampler(
        config, stage_id, mode=global_sampler_mode,
    )

    n_local_count = int(round(n_global * float(config.translation.local_fraction)))
    local_offsets_mode = _resolve_local_offsets_mode()
    local_offsets = _local_offsets(
        config, n_local_count, stage_id, mode=local_offsets_mode,
    )
    clash_mode = _resolve_clash_mode()

    feasible: list[FeasiblePose] = []
    c1_rejected = 0
    total_trials = 0
    early_stopped = False
    early_stop_reason: str | None = None
    pose_id = 0
    no_feasible_abort = int(config.scv.zero_feasible_abort)
    alpha = float(config.sampling.alpha)
    first_feasible_trial: int | None = None
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

    warhead_idx = (
        np.array(warhead_atoms_union, dtype=np.int64)
        if warhead_atoms_union else np.array([], dtype=np.int64)
    )

    for conformer_id in ligand.conf_ids:
        base_coords = ligand.coords_per_conf[conformer_id]

        # --- global 探索 ---
        for i in range(n_global):
            total_trials += 1
            translation = protein.active_site_anchor_xyz + global_offsets[i]
            coords = _coords_transformed(base_coords, global_quats[i], translation)

            if _passes_clash_constraint(
                coords, ligand.heavy_atom_indices, ligand.ligand_radii, roi, alpha,
                mode=clash_mode,
            ):
                pose_id += 1
                feasible.append(FeasiblePose(
                    pose_id=pose_id,
                    conformer_id=int(conformer_id),
                    translation=tuple(float(x) for x in translation),
                    quaternion=tuple(float(x) for x in global_quats[i]),
                    trial_number=total_trials,
                    stage_id=stage_id,
                    translation_type="global",
                    warhead_coords=(
                        coords[warhead_idx].copy()
                        if len(warhead_idx) > 0 else np.empty((0, 3), dtype=np.float64)
                    ),
                    all_coords=coords,
                ))
                if first_feasible_trial is None:
                    first_feasible_trial = total_trials
                    first_feasible_translation_type = "global"
                    first_feasible_conformer_id = int(conformer_id)
                    first_feasible_global_index = i
                    best_target_distance_at_first_feasible = _target_distance_for_pose(
                        feasible[-1].warhead_coords, protein.target_atom_xyz,
                    )
                    trial_number_at_first_feasible = total_trials
                    conformer_index = int(conformer_id)
                    global_prefix_size_used = n_global
                    global_q_index = i
                    global_translation_index = i
                    rotation_index = i
            else:
                c1_rejected += 1

            if not feasible and total_trials >= no_feasible_abort:
                early_stopped = True
                early_stop_reason = "FAIL_NO_FEASIBLE"
                break

        if early_stopped:
            break

        # --- local rescue (§7.6) ---
        if stage_id >= config.translation.local_start_stage and warhead_atoms_union:
            for i in range(len(local_offsets)):
                total_trials += 1
                quat = global_quats[i % len(global_quats)]
                rotated = _coords_transformed(base_coords, quat, np.zeros(3, dtype=np.float64))
                translation = _build_local_translation(
                    rotated, warhead_atoms_union, protein.target_atom_xyz, local_offsets[i],
                )
                coords = rotated + translation

                if _passes_clash_constraint(
                    coords, ligand.heavy_atom_indices, ligand.ligand_radii, roi, alpha,
                    mode=clash_mode,
                ):
                    pose_id += 1
                    feasible.append(FeasiblePose(
                        pose_id=pose_id,
                        conformer_id=int(conformer_id),
                        translation=tuple(float(x) for x in translation),
                        quaternion=tuple(float(x) for x in quat),
                        trial_number=total_trials,
                        stage_id=stage_id,
                        translation_type="local",
                        warhead_coords=(
                            coords[warhead_idx].copy()
                            if len(warhead_idx) > 0 else np.empty((0, 3), dtype=np.float64)
                        ),
                        all_coords=coords,
                    ))
                    if first_feasible_trial is None:
                        first_feasible_trial = total_trials
                        first_feasible_translation_type = "local"
                        first_feasible_conformer_id = int(conformer_id)
                        first_feasible_global_index = i
                        best_target_distance_at_first_feasible = _target_distance_for_pose(
                            feasible[-1].warhead_coords, protein.target_atom_xyz,
                        )
                        trial_number_at_first_feasible = total_trials
                        conformer_index = int(conformer_id)
                        global_prefix_size_used = n_global
                        global_q_index = i % len(global_quats) if len(global_quats) > 0 else None
                        global_translation_index = None
                        rotation_index = i % len(global_quats) if len(global_quats) > 0 else None
                else:
                    c1_rejected += 1

                if not feasible and total_trials >= no_feasible_abort:
                    early_stopped = True
                    early_stop_reason = "FAIL_NO_FEASIBLE"
                    break

        if early_stopped:
            break

    log = ExplorationLog(
        total_trials=total_trials,
        feasible_count=len(feasible),
        c1_rejected=c1_rejected,
        early_stopped=early_stopped,
        stopped_at_trial=total_trials,
        active_site_anchor_xyz=tuple(float(x) for x in protein.active_site_anchor_xyz),
        anchor_derivation=protein.anchor_derivation,
        anchor_source_atoms=protein.anchor_source_atoms,
        sampling_params={
            "n_conformers": int(config.sampling.n_conformers),
            "n_rotations": int(config.sampling.n_rotations),
            "n_translations": int(config.sampling.n_translations),
            "alpha": alpha,
            "stage_id": stage_id,
            "global_trials_prefix": n_global,
            "local_trials_added": len(local_offsets),
            "local_offsets_mode": local_offsets_mode,
            "clash_mode": clash_mode,
            "global_sampler_mode": global_sampler_mode,
        },
        early_stop_reason=early_stop_reason,
        first_feasible_trial=first_feasible_trial,
        first_feasible_stage_id=stage_id if first_feasible_trial is not None else None,
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
    return CpgResult(tuple(feasible), log, protein)
