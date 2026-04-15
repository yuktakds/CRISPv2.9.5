"""Anchoring Sensor (§8.2)。

責務: 観測量 target_distance の計算のみ。閾値判定は行わない (§4.1, I-07)。
改修:
  DEV-05: atom_to_smarts を全 SMARTS 組合せに展開し、
          最小 tiebreak_key を正確に決定 (I-10)。
  PERF-07: FeasiblePose.warhead_coords を使用し全座標の参照を回避。
"""
from __future__ import annotations

import math

import numpy as np

from crisp.models.runtime import (
    AnchoringObservation,
    ArgminInfo,
    FeasiblePose,
    WarheadMatch,
)


def _build_atom_smarts_pairs(
    matched_smarts: tuple[WarheadMatch, ...],
    warhead_atoms_union: tuple[int, ...],
) -> tuple[tuple[int, int, str], ...]:
    """各 warhead 原子に対応する全 (atom_index, smarts_index, pattern) を展開する。

    DEV-05: setdefault による先着バイアスを排除し、
    I-10 tiebreak で最小 smarts_index が選ばれるよう全候補を返す。
    """
    pairs: list[tuple[int, int, str]] = []
    for atom_idx in warhead_atoms_union:
        found = False
        for match in matched_smarts:
            if atom_idx in match.mapped_atoms:
                pairs.append((atom_idx, match.smarts_index, match.pattern))
                found = True
        if not found:
            # warhead_atoms_union には必ず対応する SMARTS がある (I-08)
            pairs.append((atom_idx, -1, ""))
    return tuple(pairs)


def compute_anchoring_observation(
    *,
    feasible_poses: tuple[FeasiblePose, ...],
    target_xyz: np.ndarray,
    matched_smarts: tuple[WarheadMatch, ...],
    warhead_atoms_union: tuple[int, ...],
    top_k: int,
) -> AnchoringObservation:
    """§8.2: 全 feasible pose から target_distance の最小値を求める。"""
    if not feasible_poses:
        return AnchoringObservation(
            best_target_distance=math.inf,
            best_pose=None,
            poses_evaluated=0,
            matched_smarts=matched_smarts,
            warhead_atoms_union=warhead_atoms_union,
            argmin_target=None,
            top_k_poses=(),
        )

    atom_smarts_pairs = _build_atom_smarts_pairs(matched_smarts, warhead_atoms_union)
    # warhead_atoms_union のインデックスからローカルインデックスへのマッピング
    warhead_local_map = {atom_idx: local_idx for local_idx, atom_idx in enumerate(warhead_atoms_union)}

    best_key: tuple[float, int, int, int] | None = None
    best_pose: FeasiblePose | None = None
    best_info: ArgminInfo | None = None
    pose_scores: list[tuple[float, FeasiblePose]] = []

    for pose in feasible_poses:
        pose_min = math.inf
        for atom_idx, smarts_index, smarts_pattern in atom_smarts_pairs:
            local_idx = warhead_local_map[atom_idx]
            distance = float(np.linalg.norm(pose.warhead_coords[local_idx] - target_xyz))
            key = (distance, int(pose.trial_number), int(smarts_index), int(atom_idx))

            # I-10: 辞書式最小 tiebreak
            if best_key is None or key < best_key:
                best_key = key
                best_pose = pose
                best_info = ArgminInfo(
                    atom_index=int(atom_idx),
                    smarts_index=int(smarts_index),
                    smarts_pattern=smarts_pattern,
                    tiebreak_key=key,
                )
            pose_min = min(pose_min, distance)
        pose_scores.append((pose_min, pose))

    # top_k: target_distance 昇順、tiebreak は trial_number → pose_id
    pose_scores.sort(key=lambda x: (x[0], x[1].trial_number, x[1].pose_id))
    top_k_poses = tuple(
        {
            "target_distance": float(score),
            "pose_id": pose.pose_id,
            "trial_number": pose.trial_number,
            "stage_id": pose.stage_id,
            "translation_type": pose.translation_type,
        }
        for score, pose in pose_scores[:top_k]
    )

    return AnchoringObservation(
        best_target_distance=float(best_key[0]) if best_key is not None else math.inf,
        best_pose=best_pose,
        poses_evaluated=len(feasible_poses),
        matched_smarts=matched_smarts,
        warhead_atoms_union=warhead_atoms_union,
        argmin_target=best_info,
        top_k_poses=top_k_poses,
    )
