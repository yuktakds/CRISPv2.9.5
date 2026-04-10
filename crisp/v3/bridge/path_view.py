"""RC2 / v3 パス観測のペイロード正規化・ビュー射影。

comparator.py の「判定」ロジックから I/O 正規化を分離する。
このモジュールは SCVObservation ペイロードを正規化された dict 形式へ射影するだけで、
ドリフト有無の判定は行わない。
"""
from __future__ import annotations

from typing import Any

from crisp.v3.contracts import SCVObservation, SCVObservationBundle

# ---------------------------------------------------------------------------
# Path チャネルのキー群（comparator.py と共有）
# ---------------------------------------------------------------------------

PATH_QUANTITATIVE_KEYS: tuple[str, ...] = (
    "max_blockage_ratio",
    "numeric_resolution_limited",
    "persistence_confidence",
)
PATH_EXPLORATION_KEYS: tuple[str, ...] = (
    "apo_accessible_goal_voxels",
    "goal_voxel_count",
    "feasible_count",
)
PATH_WITNESS_KEYS: tuple[str, ...] = (
    "witness_pose_id",
    "obstruction_path_ids",
    "path_family",
)
PATH_APPLICABILITY_KEYS: tuple[str, ...] = (
    "goal_precheck_passed",
    "goal_precheck_reason",
    "supported_path_model",
    "pathyes_rule1_applicability",
    "pathyes_mode_resolved",
    "pathyes_diagnostics_status",
    "pathyes_diagnostics_error_code",
)


# ---------------------------------------------------------------------------
# 型正規化ヘルパー（副作用なし・純粋関数）
# ---------------------------------------------------------------------------

def normalize_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


def normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def normalize_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return None


# ---------------------------------------------------------------------------
# Path ビュー射影
# ---------------------------------------------------------------------------

def path_threshold(observation: SCVObservation) -> float | None:
    payload_value = normalize_numeric(observation.payload.get("blockage_pass_threshold"))
    if payload_value is not None:
        return payload_value
    return normalize_numeric(observation.bridge_metrics.get("blockage_pass_threshold"))


def path_view(observation: SCVObservation | None) -> dict[str, Any]:
    """SCVObservation を正規化された path ビュー dict へ射影する。

    observation が None（チャネル欠損）の場合はすべて None のスケルトンを返す。
    """
    if observation is None:
        return {
            "quantitative_metrics": {key: None for key in PATH_QUANTITATIVE_KEYS},
            "exploration_slice": {key: None for key in PATH_EXPLORATION_KEYS},
            "witness_bundle": {
                "witness_pose_id": None,
                "obstruction_path_ids": None,
                "path_family": None,
            },
            "applicability": {key: None for key in PATH_APPLICABILITY_KEYS},
            "blockage_pass_threshold": None,
        }

    payload = dict(observation.payload)
    raw_quantitative = payload.get("quantitative_metrics")
    quantitative_metrics = {
        "max_blockage_ratio": normalize_numeric(
            raw_quantitative.get("max_blockage_ratio")
            if isinstance(raw_quantitative, dict)
            else payload.get("max_blockage_ratio", payload.get("blockage_ratio"))
        ),
        "numeric_resolution_limited": normalize_bool_or_none(
            raw_quantitative.get("numeric_resolution_limited")
            if isinstance(raw_quantitative, dict)
            else payload.get("numeric_resolution_limited")
        ),
        "persistence_confidence": normalize_numeric(
            raw_quantitative.get("persistence_confidence")
            if isinstance(raw_quantitative, dict)
            else payload.get("persistence_confidence")
        ),
    }
    raw_exploration = payload.get("exploration_slice")
    exploration_slice = {
        "apo_accessible_goal_voxels": normalize_int(
            raw_exploration.get("apo_accessible_goal_voxels")
            if isinstance(raw_exploration, dict)
            else payload.get("apo_accessible_goal_voxels")
        ),
        "goal_voxel_count": normalize_int(
            raw_exploration.get("goal_voxel_count")
            if isinstance(raw_exploration, dict)
            else payload.get("goal_voxel_count")
        ),
        "feasible_count": normalize_int(
            raw_exploration.get("feasible_count")
            if isinstance(raw_exploration, dict)
            else payload.get("feasible_count")
        ),
    }
    raw_witness = payload.get("witness_bundle")
    witness_bundle = {
        "witness_pose_id": (
            raw_witness.get("witness_pose_id")
            if isinstance(raw_witness, dict)
            else payload.get("witness_pose_id")
        ),
        "obstruction_path_ids": normalize_str_list(
            raw_witness.get("obstruction_path_ids")
            if isinstance(raw_witness, dict)
            else payload.get("obstruction_path_ids")
        ),
        "path_family": (
            raw_witness.get("path_family")
            if isinstance(raw_witness, dict)
            else payload.get("path_family", observation.family)
        ),
    }
    raw_applicability = payload.get("applicability")
    applicability = {
        "goal_precheck_passed": normalize_bool_or_none(
            raw_applicability.get("goal_precheck_passed")
            if isinstance(raw_applicability, dict)
            else payload.get("goal_precheck_passed")
        ),
        "goal_precheck_reason": (
            raw_applicability.get("goal_precheck_reason")
            if isinstance(raw_applicability, dict)
            else payload.get("goal_precheck_reason")
        ),
        "supported_path_model": normalize_bool_or_none(
            raw_applicability.get("supported_path_model")
            if isinstance(raw_applicability, dict)
            else payload.get("supported_path_model")
        ),
        "pathyes_rule1_applicability": (
            raw_applicability.get("pathyes_rule1_applicability")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_rule1_applicability")
        ),
        "pathyes_mode_resolved": (
            raw_applicability.get("pathyes_mode_resolved")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_mode_resolved")
        ),
        "pathyes_diagnostics_status": (
            raw_applicability.get("pathyes_diagnostics_status")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_diagnostics_status")
        ),
        "pathyes_diagnostics_error_code": (
            raw_applicability.get("pathyes_diagnostics_error_code")
            if isinstance(raw_applicability, dict)
            else payload.get("pathyes_diagnostics_error_code")
        ),
    }
    return {
        "quantitative_metrics": quantitative_metrics,
        "exploration_slice": exploration_slice,
        "witness_bundle": witness_bundle,
        "applicability": applicability,
        "blockage_pass_threshold": path_threshold(observation),
    }


def applicability_signature(bundle: SCVObservationBundle, *, channel_name: str) -> list[dict[str, Any]]:
    """チャネルの run-level applicability records をソート済みリストで返す。"""
    rows = [
        {
            "reason_code": record.reason_code,
            "detail": record.detail,
            "scope": record.scope,
            "applicable": record.applicable,
        }
        for record in bundle.applicability_records
        if record.channel_name == channel_name
    ]
    return sorted(rows, key=lambda row: (str(row["reason_code"]), str(row["detail"])))
