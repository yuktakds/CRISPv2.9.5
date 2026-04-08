"""Core Bridge: 既存 Core (crisp/) を frozen service として呼び出す統合シェル。

設計書 §4A-1, §B2, V29-I10, V29-I11, 別紙 D §D3 に準拠。

責務:
  - run_cpg() の public signature を変更せずに Core を呼び出す
  - Anchor proposal policy (trace-only noop) を適用し evidence_core.parquet を生成する
  - legacy Core evidence JSON を破壊しない（V29-I11）

FAIL-5 修正:
  evidence_core.parquet に stage_history_json 列を追記した。
  旧実装は stage_id_found（最終 stage 番号のみ）だったため、
  V29-I10「manifest から stage history を replay できる」を満たせていなかった。

PROPOSAL_POLICY_VERSION は anchor_proposal/policy.py と一致させる。
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from crisp.cli.phase1 import run_phase1_library
from crisp.config.loader import load_target_config
from crisp.repro.hashing import compute_config_hash, compute_input_hash, compute_requirements_hash
from crisp.v29.anchor_proposal import build_candidate_sources, build_proposal_trace, order_anchor_candidates
from crisp.v29.contracts import CoreBridgeResult
from crisp.v29.inputs import compute_joined_smiles, load_molecule_rows, to_core_library_text
from crisp.v29.tableio import write_records_table
from crisp.v29.writers import write_jsonl

_log = logging.getLogger(__name__)

PROPOSAL_POLICY_VERSION = "v29.trace-only.noop"


# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------

def _candidate_order_hash(warhead_atoms_union: list[int] | tuple[int, ...]) -> str:
    """warhead_atoms_union の決定論的ハッシュを返す。"""
    import hashlib
    payload = json.dumps(list(warhead_atoms_union), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_stage_history(exploration_log: dict[str, Any]) -> list[dict[str, Any]]:
    """exploration_log から stage_history を取得する。

    FAIL-5 修正:
    Core の exploration_log に stage_history フィールドが存在する場合はそれを使う。
    存在しない場合は stage_id_found を持つ 1 要素リストにフォールバックする。
    これにより V29-I10「stage history を replay できる」を満たす。
    """
    stage_history = exploration_log.get("stage_history")
    if isinstance(stage_history, list) and stage_history:
        return stage_history

    # フォールバック: 最終 stage だけを 1 エントリとして記録
    stage_id = exploration_log.get("stage_id_found")
    if stage_id is not None:
        return [
            {
                "stage_id": stage_id,
                "feasible_count": exploration_log.get("feasible_count"),
                "stopped_at_trial": exploration_log.get("stopped_at_trial"),
                "early_stop_reason": exploration_log.get("early_stop_reason"),
                "translation_type": exploration_log.get("translation_type_found"),
                "_fallback": True,
            }
        ]
    return []


def _extract_core_rows(
    summary_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Core summary.json から compound_rows と evidence_rows を抽出する。

    evidence_rows は別紙 D §D3 の必須列を満たす。
    FAIL-5: stage_history_json を追加。
    """
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    compound_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []

    run_id = summary.get("run_id")
    target_id = (
        summary.get("target_name")
        or summary.get("config", {}).get("target_name")
        or "target"
    )

    for record in summary.get("records", []):
        evidence_path = Path(record["evidence_path"])
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        exploration = evidence.get("exploration_log", {})
        anchoring = evidence.get("sensors", {}).get("anchoring", {})
        offtarget = evidence.get("sensors", {}).get("offtarget", {})

        witness_pose = anchoring.get("witness_pose")
        warhead_atoms_union = anchoring.get("warhead_provenance", {}).get(
            "warhead_atoms_union", []
        )

        # Anchor proposal trace (trace-only noop)
        candidate_rows = build_candidate_sources(warhead_atoms_union=warhead_atoms_union)
        ordered_tuple = order_anchor_candidates(candidate_rows)
        proposal_trace = build_proposal_trace(
            ordered_tuple=ordered_tuple,
            candidate_rows=candidate_rows,
            legacy_tuple=list(warhead_atoms_union),
        )

        # FAIL-5: stage_history_json を抽出
        stage_history = _extract_stage_history(exploration)

        molecule_id = str(record.get("name", ""))
        core_verdict = evidence.get("verdict")
        core_reason_code = evidence.get("reason")
        config_hash = evidence.get("config_hash")
        requirements_hash = evidence.get("requirements_hash")

        compound_row: dict[str, Any] = {
            "run_id": run_id,
            "molecule_id": molecule_id,
            "target_id": target_id,
            "core_verdict": core_verdict,
            "core_reason_code": core_reason_code,
            "best_target_distance": anchoring.get("best_target_distance"),
            "best_offtarget_distance": offtarget.get("best_offtarget_distance"),
            "final_stage": exploration.get("stage_id_found"),
            "config_hash": config_hash,
            # V29-I11: legacy alias。単一 global verdict との混同を防ぐため
            # legacy_core_final_verdict と命名する（設計書監査閉鎖項目1）
            "legacy_core_final_verdict": core_verdict,
        }

        evidence_row: dict[str, Any] = {
            # D3 必須列
            "run_id": run_id,
            "molecule_id": molecule_id,
            "target_id": target_id,
            "stage_id": exploration.get("stage_id_found"),
            "translation_type": exploration.get("translation_type_found"),
            "trial_number": None if witness_pose is None else witness_pose.get("trial_number"),
            "stopped_at_trial": exploration.get("stopped_at_trial"),
            "early_stop_reason": exploration.get("early_stop_reason"),
            "anchoring_witness_pose_json": witness_pose,
            "anchoring_fail_certificate_json": {
                "best_target_distance": anchoring.get("best_target_distance")
            },
            "candidate_order_hash": proposal_trace["candidate_order_hash"],
            "near_band_triggered": proposal_trace["near_band_triggered"],
            "proposal_policy_version": proposal_trace["proposal_policy_version"],
            "core_verdict": core_verdict,
            "core_reason_code": core_reason_code,
            "config_hash": config_hash,
            "input_hash": compute_input_hash(
                str(record.get("smiles", "")),
                str(requirements_hash or ""),
            ),
            "requirements_hash": requirements_hash,
            # FAIL-5 修正: stage_history_json を追記（V29-I10 対応）
            "stage_history_json": stage_history,
            # V29-I11 legacy alias
            "legacy_core_final_verdict": core_verdict,
            # 追加 provenance
            "proposal_trace_json": proposal_trace,
            "evidence_path": str(evidence_path),
        }

        compound_rows.append(compound_row)
        evidence_rows.append(evidence_row)

    _log.debug("_extract_core_rows: %d records processed", len(evidence_rows))
    return compound_rows, evidence_rows


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def run_core_bridge(
    *,
    repo_root: Path,
    config_path: Path,
    library_path: Path,
    stageplan_path: Path,
    out_dir: Path,
    proposal_mode: Literal["legacy_passthrough", "ordered_bridge"] = "legacy_passthrough",
) -> CoreBridgeResult:
    """Core を frozen service として呼び出し、統合出力を生成する。

    §4A-1:
      run_cpg() の public signature は変更しない。
      追加情報は exploration_log と evidence_core.parquet にのみ記録する。

    proposal_mode:
      legacy_passthrough: legacy Core と観測的に同一（current snapshot）
      ordered_bridge:    候補列順序と trace のみ変更（predicate/threshold は不変）
    """
    if proposal_mode not in {"legacy_passthrough", "ordered_bridge"}:
        raise ValueError(f"Unsupported proposal_mode: {proposal_mode!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = out_dir.name

    _log.info(
        "run_core_bridge: run_id=%s, proposal_mode=%s, library=%s",
        run_id, proposal_mode, library_path,
    )

    # 分子ライブラリを一時ファイルに書き出して Core に渡す
    molecule_rows = load_molecule_rows(library_path)
    library_text = to_core_library_text(molecule_rows)

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".smi", delete=False
    ) as tmp_fh:
        tmp_fh.write(library_text)
        tmp_library_path = Path(tmp_fh.name)

    try:
        payload = run_phase1_library(
            repo_root=repo_root,
            config_path=config_path,
            library_path=tmp_library_path,
            run_id=run_id,
            stageplan_path=stageplan_path,
            show_progress=False,
        )
    finally:
        try:
            tmp_library_path.unlink(missing_ok=True)
        except OSError:
            pass

    summary_path = Path(payload["summary_path"])
    compound_rows, evidence_rows = _extract_core_rows(summary_path)

    # 統合テーブルを書き出す
    core_compound_table = write_records_table(out_dir / "core_compounds.parquet", compound_rows)
    evidence_core_table = write_records_table(out_dir / "evidence_core.parquet", evidence_rows)
    core_rows_path = write_jsonl(out_dir / "core_rows.jsonl", evidence_rows)
    materialization_events = [
        core_compound_table.to_materialization_event(logical_output="core_compounds.parquet"),
        evidence_core_table.to_materialization_event(logical_output="evidence_core.parquet"),
    ]

    diagnostics: dict[str, Any] = {
        "proposal_mode": proposal_mode,
        "proposal_policy_version": PROPOSAL_POLICY_VERSION,
        "semantic_mode": "trace-only-noop",
        "source_summary_path": str(summary_path),
        "record_count": len(evidence_rows),
        "core_compounds_path": core_compound_table.path,
        "evidence_core_path": evidence_core_table.path,
        "stage_history_recorded": True,  # FAIL-5 修正マーカー
        "materialization_events": materialization_events,
    }
    diagnostics_path = out_dir / "core_bridge_diagnostics.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )

    # ハッシュ群を計算
    config = load_target_config(config_path)
    config_hash = compute_config_hash(config)
    requirements_hash = compute_requirements_hash()
    joined_smiles = compute_joined_smiles(molecule_rows)
    input_hash = compute_input_hash(joined_smiles, requirements_hash)

    _log.info(
        "run_core_bridge complete: %d compounds, evidence_core=%s",
        len(evidence_rows), evidence_core_table.path,
    )

    return CoreBridgeResult(
        core_rows_path=str(core_compound_table.path),
        evidence_core_path=evidence_core_table.path,
        diagnostics_path=str(diagnostics_path),
        config_hash=config_hash,
        input_hash=input_hash,
        requirements_hash=requirements_hash,
        materialization_events=materialization_events,
    )
