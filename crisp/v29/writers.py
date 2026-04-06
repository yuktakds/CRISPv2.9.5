from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json

from crisp.utils.jsonx import canonical_json_bytes
from crisp.v29.contracts import CapBatchEval, IntegratedRunManifest, OutputInventory


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical_json_bytes(payload))
    return out


def write_integrated_manifest(path: str | Path, manifest: IntegratedRunManifest) -> Path:
    return _write_json(path, asdict(manifest))


def write_output_inventory(path: str | Path, inventory: OutputInventory) -> Path:
    return _write_json(path, asdict(inventory))


def write_cap_batch_eval(path: str | Path, cap_eval: CapBatchEval) -> Path:
    return _write_json(path, cap_eval.to_dict())


def write_eval_report(path: str | Path, payload: dict[str, Any]) -> Path:
    forbidden = {
        'cap_batch_verdict',
        'cap_batch_reason_code',
        'verdict_layer0',
        'verdict_layer1',
        'verdict_layer2',
        'verdict_final',
    }
    overlap = forbidden & set(payload.keys())
    if overlap:
        raise ValueError(f'eval_report.json must not contain verdict keys: {sorted(overlap)}')
    return _write_json(path, payload)


def write_qc_report(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)


def write_collapse_figure_spec(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)


def write_replay_audit(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)


def write_theta_rule1_resolution(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)


def write_rule3_trace_summary(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            fh.write('\n')
    return out


def write_legacy_phase1_evidence_alias(path: str | Path, payload: dict[str, Any]) -> Path:
    return _write_json(path, payload)
