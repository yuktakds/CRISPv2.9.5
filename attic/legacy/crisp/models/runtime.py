"""ランタイムデータモデル。

設計書 v4.3.1 §4, §7, §8, §9, §10, §12 に準拠。
全 dataclass は frozen=True でイミュータブル性を保証する。
np.ndarray を含む型は __hash__ / __eq__ をオーバーライドして
frozen dataclass との互換性を確保する（BUG-04 修正）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

import numpy as np

TranslationType = Literal["global", "local"]


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCLEAR = "UNCLEAR"


class SearchControlAction(StrEnum):
    """§10.2: search-control logic の出力 5 値。"""
    CONTINUE = "CONTINUE"
    FINALIZE_PASS = "FINALIZE_PASS"
    FINALIZE_FAIL = "FINALIZE_FAIL"
    FINALIZE_UNCLEAR = "FINALIZE_UNCLEAR"
    FINALIZE_BY_TERMINAL_POLICY = "FINALIZE_BY_TERMINAL_POLICY"


# --- MEF 関連 ---

@dataclass(frozen=True, slots=True)
class WarheadMatch:
    """§6.2: SMARTS マッチ結果。mapped_atoms は昇順ソート済み (I-09)。"""
    smarts_index: int
    pattern: str
    mapped_atoms: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MefResult:
    """§6: MEF の判定結果。"""
    passed: bool
    reason: str | None
    smiles: str
    heavy_atom_count: int | None
    rotatable_bonds: int | None
    matched_smarts: tuple[WarheadMatch, ...] = ()
    warhead_atoms_union: tuple[int, ...] = ()


# --- 蛋白質構造 ---

@dataclass(slots=True)
class ProteinAtom:
    """蛋白質重原子。frozen=False で np.ndarray の hash 問題を回避 (BUG-04)。"""
    serial: int
    chain: str
    residue_number: int
    insertion_code: str
    residue_name: str
    atom_name: str
    element: str
    xyz: np.ndarray
    vdw_radius: float


@dataclass(frozen=True, slots=True)
class AnchorSourceAtom:
    atom: str
    xyz: tuple[float, float, float]


@dataclass(slots=True)
class ProteinGeometry:
    """§5.3: 蛋白質幾何情報。1 target につき 1 回だけ構築する。"""
    active_site_anchor_xyz: np.ndarray
    anchor_derivation: str
    anchor_source_atoms: tuple[AnchorSourceAtom, ...]
    protein_heavy_atoms: tuple[ProteinAtom, ...]
    target_atom_xyz: np.ndarray
    offtarget_atoms: tuple[tuple[str, np.ndarray], ...]


# --- CPG 関連 ---

@dataclass(frozen=True, slots=True)
class FeasiblePose:
    """§7.7: feasible pose。
    coords は Sensor 計算に必要な変換済みリガンド座標。
    warhead_coords は warhead 原子のみの座標で省メモリ化 (PERF-07)。
    """
    pose_id: int
    conformer_id: int
    translation: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]
    trial_number: int
    stage_id: int
    translation_type: TranslationType
    warhead_coords: np.ndarray  # warhead 原子のみの座標 (PERF-07)
    all_coords: np.ndarray | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class ExplorationLog:
    """§7.7: CPG 探索ログ。§7.8 staging provenance (I-13) 必須フィールドを含む。"""
    total_trials: int
    feasible_count: int
    c1_rejected: int
    early_stopped: bool
    stopped_at_trial: int
    active_site_anchor_xyz: tuple[float, float, float]
    anchor_derivation: str
    anchor_source_atoms: tuple[AnchorSourceAtom, ...]
    sampling_params: dict[str, Any]
    early_stop_reason: str | None = None
    stage_id_found: int | None = None
    translation_type_found: TranslationType | None = None
    first_feasible_trial: int | None = None
    first_feasible_stage_id: int | None = None
    first_feasible_translation_type: TranslationType | None = None
    first_feasible_conformer_id: int | None = None
    first_feasible_global_index: int | None = None
    best_target_distance_at_first_feasible: float | None = None
    trial_number_at_first_feasible: int | None = None
    conformer_index: int | None = None
    global_prefix_size_used: int | None = None
    global_q_index: int | None = None
    global_translation_index: int | None = None
    rotation_index: int | None = None


# --- Sensor 関連 ---

@dataclass(frozen=True, slots=True)
class ArgminInfo:
    """§8.1: tiebreak 情報 (I-10)。"""
    atom_index: int
    smarts_index: int
    smarts_pattern: str
    tiebreak_key: tuple[float, int, int, int]


@dataclass(frozen=True, slots=True)
class AnchoringObservation:
    """§8.2: Anchoring Sensor の出力。"""
    best_target_distance: float
    best_pose: FeasiblePose | None
    poses_evaluated: int
    matched_smarts: tuple[WarheadMatch, ...]
    warhead_atoms_union: tuple[int, ...]
    argmin_target: ArgminInfo | None
    top_k_poses: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class OffTargetObservation:
    """§8.3: OffTarget Sensor の出力。"""
    best_offtarget_distance: float
    closest_offtarget_residue: int | None
    best_offtarget_pose: FeasiblePose | None
    argmin_offtarget: ArgminInfo | None


@dataclass(frozen=True, slots=True)
class SensorVerdict:
    """§9: SCV が返す sensor 単位の判定。"""
    verdict: Verdict
    reason_or_meta: Any


# --- Phase1 統合結果 ---

@dataclass(frozen=True, slots=True)
class Phase1Evaluation:
    anchoring: AnchoringObservation
    offtarget: OffTargetObservation | None
    exploration_log: ExplorationLog
    v_anchor: SensorVerdict
    v_offtarget: SensorVerdict | None
    v_core: Verdict
    action: SearchControlAction
    final_verdict: Verdict
    final_reason: str | dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class CompoundRunResult:
    mef: MefResult
    phase1: Phase1Evaluation | None
    evidence: dict[str, Any]
