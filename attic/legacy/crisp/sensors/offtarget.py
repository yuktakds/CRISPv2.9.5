"""OffTarget Sensor (§8.3)。

責務: 観測量 offtarget_distance の計算のみ。閾値判定は行わない (§4.1, I-07)。
§8.4: OffTarget の witness は「最も危険な pose でも安全であること」を示す集合レベル witness。
"""
from __future__ import annotations

import math

import numpy as np

from crisp.models.runtime import (
    ArgminInfo,
    FeasiblePose,
    OffTargetObservation,
    WarheadMatch,
)


def _build_atom_smarts_pairs(
    matched_smarts: tuple[WarheadMatch, ...],
    warhead_atoms_union: tuple[int, ...],
) -> tuple[tuple[int, int, str], ...]:
    """DEV-05: 全 SMARTS 組合せを展開 (anchoring.py と同一ロジック)。"""
    pairs: list[tuple[int, int, str]] = []
    for atom_idx in warhead_atoms_union:
        found = False
        for match in matched_smarts:
            if atom_idx in match.mapped_atoms:
                pairs.append((atom_idx, match.smarts_index, match.pattern))
                found = True
        if not found:
            pairs.append((atom_idx, -1, ""))
    return tuple(pairs)


def compute_offtarget_observation(
    *,
    feasible_poses: tuple[FeasiblePose, ...],
    offtarget_atoms: tuple[tuple[str, np.ndarray], ...],
    matched_smarts: tuple[WarheadMatch, ...],
    warhead_atoms_union: tuple[int, ...],
) -> OffTargetObservation:
    """§8.3: 全 feasible pose × 全 offtarget Cys から最小距離を求める。"""
    if not feasible_poses or not offtarget_atoms:
        return OffTargetObservation(
            best_offtarget_distance=math.inf,
            closest_offtarget_residue=None,
            best_offtarget_pose=None,
            argmin_offtarget=None,
        )

    atom_smarts_pairs = _build_atom_smarts_pairs(matched_smarts, warhead_atoms_union)
    warhead_local_map = {atom_idx: local_idx for local_idx, atom_idx in enumerate(warhead_atoms_union)}

    best_key: tuple[float, int, int, int] | None = None
    best_pose: FeasiblePose | None = None
    best_residue: int | None = None
    best_info: ArgminInfo | None = None

    for pose in feasible_poses:
        for atom_idx, smarts_index, smarts_pattern in atom_smarts_pairs:
            local_idx = warhead_local_map[atom_idx]
            lig_xyz = pose.warhead_coords[local_idx]
            for label, cys_xyz in offtarget_atoms:
                distance = float(np.linalg.norm(lig_xyz - cys_xyz))
                key = (distance, int(pose.trial_number), int(smarts_index), int(atom_idx))
                if best_key is None or key < best_key:
                    best_key = key
                    best_pose = pose
                    # label形式: "chain:residue_number:atom_name"
                    try:
                        best_residue = int(label.split(":")[1])
                    except (IndexError, ValueError):
                        best_residue = None
                    best_info = ArgminInfo(
                        atom_index=int(atom_idx),
                        smarts_index=int(smarts_index),
                        smarts_pattern=smarts_pattern,
                        tiebreak_key=key,
                    )

    return OffTargetObservation(
        best_offtarget_distance=float(best_key[0]) if best_key is not None else math.inf,
        closest_offtarget_residue=best_residue,
        best_offtarget_pose=best_pose,
        argmin_offtarget=best_info,
    )
