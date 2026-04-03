from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

import yaml
from rdkit import Chem

from crisp.cli.phase1 import run_phase1_library
from crisp.reason_codes import normalize_legacy_unclear_reason
from crisp.repro.hashing import (
    _parse_smiles_record,
    compute_input_hash,
    compute_requirements_hash,
    parse_smiles_library,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO_ROOT / "audit"
OUTPUT_ROOT = REPO_ROOT / "outputs"
STAGEPLAN_PATH = REPO_ROOT / "configs" / "stageplan.empty.json"
BASE_CONFIG_PATH = REPO_ROOT / "configs" / "9kr6_cys328.yaml"
SMOKE_CONFIG_PATH = REPO_ROOT / "configs" / "9kr6_cys328.smoke.yaml"

LIBRARIES = {
    "facr2240": {
        "source_library": OUTPUT_ROOT / "mef-facr2240-smoke-cxfix" / "libraries" / "mef_pass.smi",
        "cxsmiles_source": REPO_ROOT / "data" / "libraries" / "fACR2240.smiles",
        "old_summary": OUTPUT_ROOT / "phase1-facr2240-all" / "summary.json",
        "new_summary": OUTPUT_ROOT / "phase1-facr2240-all-cxfix" / "summary.json",
    },
    "cys3200": {
        "source_library": OUTPUT_ROOT / "mef-cys3200-smoke-cxfix" / "libraries" / "mef_pass.smi",
        "cxsmiles_source": REPO_ROOT / "data" / "libraries" / "CYS-3200.smiles",
        "old_summary": None,
        "new_summary": OUTPUT_ROOT / "phase1-cys3200-all-cxfix" / "summary.json",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def normalize_reason(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def normalize_reason_with_context(value: Any, *, feasible_count: int | None = None) -> str | None:
    normalized = normalize_legacy_unclear_reason(
        normalize_reason(value),
        feasible_count=feasible_count,
    )
    return normalize_reason(normalized)


def canonicalize_smiles(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def _stable_rank(smiles: str, name: str) -> str:
    return hashlib.sha256(f"{name}\t{smiles}".encode("utf-8")).hexdigest()


def select_sample(entries: list[tuple[str, str]], sample_size: int) -> list[tuple[str, str]]:
    ranked = [
        (_stable_rank(smiles, name), index, smiles, name)
        for index, (smiles, name) in enumerate(entries)
    ]
    chosen_indices = {index for _, index, _, _ in sorted(ranked)[:sample_size]}
    return [entry for index, entry in enumerate(entries) if index in chosen_indices]


def write_smiles_library(path: Path, entries: list[tuple[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{smiles} {name}\n" for smiles, name in entries)
    path.write_text(body, encoding="utf-8")
    return path


def config_diff(base_cfg: dict[str, Any], smoke_cfg: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    keys = sorted(set(base_cfg) | set(smoke_cfg))
    for key in keys:
        path = f"{prefix}.{key}" if prefix else key
        in_base = key in base_cfg
        in_smoke = key in smoke_cfg
        if not in_base or not in_smoke:
            paths.append({"path": path, "base": base_cfg.get(key), "smoke": smoke_cfg.get(key)})
            continue
        base_val = base_cfg[key]
        smoke_val = smoke_cfg[key]
        if isinstance(base_val, dict) and isinstance(smoke_val, dict):
            paths.extend(config_diff(base_val, smoke_val, path))
        elif base_val != smoke_val:
            paths.append({"path": path, "base": base_val, "smoke": smoke_val})
    return paths


def summarize_run(summary_payload: dict[str, Any]) -> dict[str, Any]:
    verdict_counts = Counter()
    reason_counts = Counter()
    core_reason_counts = Counter()
    anchoring_reason_counts = Counter()
    offtarget_reason_counts = Counter()
    offtarget_verdict_counts = Counter()
    early_stop_reason_counts = Counter()
    stage_id_found_counts = Counter()
    translation_type_counts = Counter()
    v_core_counts = Counter()
    early_stopped_true = 0
    feasible_counts: list[int] = []
    feasible_by_verdict: dict[str, list[int]] = {"PASS": [], "FAIL": [], "UNCLEAR": []}
    record_rows: list[dict[str, Any]] = []

    for index, record in enumerate(summary_payload["records"], start=1):
        evidence = load_json(Path(record["evidence_path"]))
        exploration = evidence.get("exploration_log", {})
        sensors = evidence.get("sensors", {})
        feasible_count = int(exploration.get("feasible_count", 0) or 0)
        verdict = str(record["verdict"])
        reason = normalize_reason_with_context(record.get("reason"), feasible_count=feasible_count)
        core_reason = normalize_reason_with_context(evidence.get("core_reason"), feasible_count=feasible_count)
        anchoring_reason = normalize_reason_with_context(
            evidence.get("anchoring_reason"),
            feasible_count=feasible_count,
        )
        offtarget_reason = normalize_reason_with_context(
            evidence.get("offtarget_reason"),
            feasible_count=feasible_count,
        )
        offtarget_verdict = sensors.get("offtarget", {}).get("verdict")
        early_stop_reason = normalize_reason(exploration.get("early_stop_reason"))
        stage_id_found = exploration.get("stage_id_found")
        translation_type = exploration.get("translation_type_found")
        v_core = evidence.get("v_core")

        verdict_counts[verdict] += 1
        reason_counts[reason or "PASS"] += 1
        core_reason_counts[core_reason or "PASS"] += 1
        anchoring_reason_counts[anchoring_reason or "PASS"] += 1
        offtarget_reason_counts[offtarget_reason or "NONE"] += 1
        offtarget_verdict_counts[str(offtarget_verdict)] += 1
        early_stop_reason_counts[early_stop_reason or "NONE"] += 1
        stage_id_found_counts[str(stage_id_found)] += 1
        translation_type_counts[str(translation_type)] += 1
        v_core_counts[str(v_core)] += 1
        early_stopped_true += int(bool(exploration.get("early_stopped")))
        feasible_counts.append(feasible_count)
        feasible_by_verdict[verdict].append(feasible_count)

        record_rows.append(
            {
                "index": index,
                "name": record["name"],
                "smiles": record["smiles"],
                "verdict": verdict,
                "reason": reason,
                "core_reason": core_reason,
                "anchoring_reason": anchoring_reason,
                "offtarget_reason": offtarget_reason,
                "offtarget_verdict": str(offtarget_verdict),
                "stage_id_found": stage_id_found,
                "translation_type_found": translation_type,
                "early_stop_reason": early_stop_reason,
                "early_stopped": bool(exploration.get("early_stopped")),
                "feasible_count": feasible_count,
                "stopped_at_trial": exploration.get("stopped_at_trial"),
                "total_trials": exploration.get("total_trials"),
                "input_hash": evidence.get("meta", {}).get("input_hash"),
            }
        )

    def _stats(values: list[int]) -> dict[str, Any]:
        if not values:
            return {"count": 0, "min": None, "median": None, "max": None}
        return {
            "count": len(values),
            "min": min(values),
            "median": median(values),
            "max": max(values),
        }

    return {
        "summary": summary_payload["summary"],
        "verdict_counts": dict(verdict_counts),
        "reason_counts": dict(reason_counts),
        "core_reason_counts": dict(core_reason_counts),
        "anchoring_reason_counts": dict(anchoring_reason_counts),
        "offtarget_reason_counts": dict(offtarget_reason_counts),
        "offtarget_verdict_counts": dict(offtarget_verdict_counts),
        "early_stop_reason_counts": dict(early_stop_reason_counts),
        "stage_id_found_counts": dict(stage_id_found_counts),
        "translation_type_counts": dict(translation_type_counts),
        "v_core_counts": dict(v_core_counts),
        "early_stopped_true": early_stopped_true,
        "feasible_count_stats": _stats(feasible_counts),
        "feasible_count_by_verdict": {key: _stats(values) for key, values in feasible_by_verdict.items()},
        "records": record_rows,
    }


def compare_runs(base_run: dict[str, Any], smoke_run: dict[str, Any]) -> dict[str, Any]:
    transitions = Counter()
    changed_records: list[dict[str, Any]] = []
    for base_record, smoke_record in zip(base_run["records"], smoke_run["records"], strict=True):
        transition_key = (
            f"{base_record['verdict']}:{base_record['reason'] or 'PASS'}"
            f" -> {smoke_record['verdict']}:{smoke_record['reason'] or 'PASS'}"
        )
        transitions[transition_key] += 1
        if (
            base_record["verdict"] != smoke_record["verdict"]
            or base_record["reason"] != smoke_record["reason"]
        ):
            changed_records.append(
                {
                    "index": base_record["index"],
                    "name": base_record["name"],
                    "base_verdict": base_record["verdict"],
                    "base_reason": base_record["reason"],
                    "smoke_verdict": smoke_record["verdict"],
                    "smoke_reason": smoke_record["reason"],
                    "base_feasible_count": base_record["feasible_count"],
                    "smoke_feasible_count": smoke_record["feasible_count"],
                    "base_stage_id_found": base_record["stage_id_found"],
                    "smoke_stage_id_found": smoke_record["stage_id_found"],
                    "base_offtarget_reason": base_record["offtarget_reason"],
                    "smoke_offtarget_reason": smoke_record["offtarget_reason"],
                }
            )

    return {
        "transition_counts": dict(transitions),
        "changed_record_count": len(changed_records),
        "changed_record_examples": changed_records[:15],
    }


def run_or_load_phase1(
    *,
    config_path: Path,
    library_path: Path,
    run_id: str,
    rerun: bool,
) -> dict[str, Any]:
    summary_path = OUTPUT_ROOT / run_id / "summary.json"
    if summary_path.exists() and not rerun:
        return load_json(summary_path)

    payload = run_phase1_library(
        repo_root=REPO_ROOT,
        config_path=config_path,
        library_path=library_path,
        run_id=run_id,
        stageplan_path=STAGEPLAN_PATH,
        prefilter_report_path=None,
        show_progress=False,
        progress_every=0,
        progress_seconds=0,
    )
    return load_json(Path(payload["summary_path"]))


def build_cxsmiles_table() -> list[dict[str, Any]]:
    requirements_hash = compute_requirements_hash()
    raw_lines = LIBRARIES["facr2240"]["cxsmiles_source"].read_text(encoding="utf-8").splitlines()
    old_summary = load_json(LIBRARIES["facr2240"]["old_summary"])
    new_summary = load_json(LIBRARIES["facr2240"]["new_summary"])
    rows: list[dict[str, Any]] = []

    for line_index, raw_line in enumerate(raw_lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or not parts[1].startswith("|"):
            continue

        old_smiles = parts[0]
        old_name = parts[1] if len(parts) > 1 else f"compound_{line_index:05d}"
        new_smiles, new_name = _parse_smiles_record(line, index=line_index)

        old_record = old_summary["records"][line_index - 1]
        new_record = new_summary["records"][line_index - 1]
        old_evidence = load_json(Path(old_record["evidence_path"]))
        new_evidence = load_json(Path(new_record["evidence_path"]))

        rows.append(
            {
                "line_index": line_index,
                "raw_line": raw_line,
                "old_name": old_name,
                "new_name": new_name,
                "old_smiles": old_smiles,
                "new_smiles": new_smiles,
                "old_input_hash": compute_input_hash(old_smiles, requirements_hash),
                "new_input_hash": compute_input_hash(new_smiles, requirements_hash),
                "old_evidence_input_hash": old_evidence.get("meta", {}).get("input_hash"),
                "new_evidence_input_hash": new_evidence.get("meta", {}).get("input_hash"),
                "old_canonical_smiles": canonicalize_smiles(old_smiles),
                "new_canonical_smiles": canonicalize_smiles(new_smiles),
                "old_verdict": old_record["verdict"],
                "new_verdict": new_record["verdict"],
                "old_reason": normalize_reason_with_context(old_record.get("reason"), feasible_count=0),
                "new_reason": normalize_reason_with_context(new_record.get("reason"), feasible_count=0),
                "verdict_changed": old_record["verdict"] != new_record["verdict"],
                "reason_changed": normalize_reason_with_context(
                    old_record.get("reason"),
                    feasible_count=0,
                ) != normalize_reason_with_context(
                    new_record.get("reason"),
                    feasible_count=0,
                ),
                "name_changed": old_name != new_name,
                "smiles_changed": old_smiles != new_smiles,
            }
        )
    return rows


def write_cxsmiles_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "line_index",
        "raw_line",
        "old_name",
        "new_name",
        "old_smiles",
        "new_smiles",
        "old_input_hash",
        "new_input_hash",
        "old_evidence_input_hash",
        "new_evidence_input_hash",
        "old_canonical_smiles",
        "new_canonical_smiles",
        "old_verdict",
        "new_verdict",
        "old_reason",
        "new_reason",
        "verdict_changed",
        "reason_changed",
        "name_changed",
        "smiles_changed",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(
    *,
    sample_size: int,
    config_changes: list[dict[str, Any]],
    sample_paths: dict[str, str],
    analyses: dict[str, Any],
    cx_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# 9KR6 smoke config semantic drift audit")
    lines.append("")
    lines.append("This audit compares the only local baseline artifact available in-repo,")
    lines.append("`configs/9kr6_cys328.yaml`, against `configs/9kr6_cys328.smoke.yaml`.")
    lines.append("No separate historical Phase1 config artifact was found under `configs/`,")
    lines.append("so the conclusions below are explicitly limited to semantic drift caused by")
    lines.append("the current smoke sampling profile versus the original low-sampling baseline.")
    lines.append("")
    lines.append("## Mechanical config diff")
    lines.append("")
    for diff in config_changes:
        lines.append(f"- `{diff['path']}`: `{diff['base']}` -> `{diff['smoke']}`")
    lines.append("")
    lines.append("## Fixed sample selection")
    lines.append("")
    lines.append("Samples are deterministic: the script ranks `(compound_name, smiles)` pairs by")
    lines.append(f"SHA256, takes the first `{sample_size}` rows, then restores original library order.")
    lines.append("")
    for library_name, sample_path in sample_paths.items():
        lines.append(f"- `{library_name}` sample: `{sample_path}`")
    lines.append("")
    lines.append("## Comparative findings")
    lines.append("")
    for library_name, payload in analyses.items():
        base_run = payload["base"]
        smoke_run = payload["smoke"]
        comparison = payload["comparison"]
        lines.append(f"### {library_name}")
        lines.append("")
        lines.append(
            f"- Baseline summary: PASS {base_run['summary']['PASS']}, "
            f"FAIL {base_run['summary']['FAIL']}, UNCLEAR {base_run['summary']['UNCLEAR']}"
        )
        lines.append(
            f"- Smoke summary: PASS {smoke_run['summary']['PASS']}, "
            f"FAIL {smoke_run['summary']['FAIL']}, UNCLEAR {smoke_run['summary']['UNCLEAR']}"
        )
        lines.append(f"- Baseline reasons: `{json.dumps(base_run['reason_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Smoke reasons: `{json.dumps(smoke_run['reason_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Baseline core reasons: `{json.dumps(base_run['core_reason_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Smoke core reasons: `{json.dumps(smoke_run['core_reason_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Baseline v_core counts: `{json.dumps(base_run['v_core_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Smoke v_core counts: `{json.dumps(smoke_run['v_core_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Transition counts: `{json.dumps(comparison['transition_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Changed records: `{comparison['changed_record_count']}` / `{len(base_run['records'])}`")
        lines.append(
            f"- Baseline feasible_count stats: `{json.dumps(base_run['feasible_count_stats'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Smoke feasible_count stats: `{json.dumps(smoke_run['feasible_count_stats'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Baseline offtarget verdicts: `{json.dumps(base_run['offtarget_verdict_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Smoke offtarget verdicts: `{json.dumps(smoke_run['offtarget_verdict_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Baseline offtarget reasons: `{json.dumps(base_run['offtarget_reason_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Smoke offtarget reasons: `{json.dumps(smoke_run['offtarget_reason_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Baseline early_stop reasons: `{json.dumps(base_run['early_stop_reason_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Smoke early_stop reasons: `{json.dumps(smoke_run['early_stop_reason_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Baseline stage_id_found counts: `{json.dumps(base_run['stage_id_found_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        lines.append(
            f"- Smoke stage_id_found counts: `{json.dumps(smoke_run['stage_id_found_counts'], ensure_ascii=False, sort_keys=True)}`"
        )
        if comparison["changed_record_examples"]:
            lines.append("- Example record flips:")
            for row in comparison["changed_record_examples"][:8]:
                lines.append(
                    f"  `{row['name']}`: `{row['base_verdict']}:{row['base_reason'] or 'PASS'}`"
                    f" -> `{row['smoke_verdict']}:{row['smoke_reason'] or 'PASS'}`, "
                    f"feasible `{row['base_feasible_count']}` -> `{row['smoke_feasible_count']}`"
                )
        lines.append("")

    name_changes = sum(1 for row in cx_rows if row["name_changed"])
    smiles_changes = sum(1 for row in cx_rows if row["smiles_changed"])
    input_hash_changes = sum(1 for row in cx_rows if row["old_input_hash"] != row["new_input_hash"])
    canonical_smiles_changes = sum(
        1
        for row in cx_rows
        if row["old_canonical_smiles"] != row["new_canonical_smiles"]
    )
    verdict_changes = sum(1 for row in cx_rows if row["verdict_changed"])
    reason_changes = sum(1 for row in cx_rows if row["reason_changed"])

    lines.append("## CXSMILES parser impact")
    lines.append("")
    lines.append(f"- CXSMILES rows audited in `fACR2240.smiles`: `{len(cx_rows)}`")
    lines.append(f"- Name changes: `{name_changes}`")
    lines.append(f"- SMILES tokenization changes: `{smiles_changes}`")
    lines.append(f"- Input hash changes: `{input_hash_changes}`")
    lines.append(f"- Canonical SMILES changes after RDKit parse: `{canonical_smiles_changes}`")
    lines.append(f"- Verdict changes in the old invalid run vs `-cxfix` run: `{verdict_changes}`")
    lines.append(f"- Reason changes in the old invalid run vs `-cxfix` run: `{reason_changes}`")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append("The CXSMILES parser fix corrects identifier and input-hash corruption for CX rows,")
    lines.append("but it does not explain the current Phase1 pass-heavy distribution. The reproducible")
    lines.append("drift seen here is dominated by the smoke sampling profile: the baseline config")
    lines.append("collapses to `FAIL_NO_FEASIBLE`, while the smoke config converts most of the same")
    lines.append("sample into `PASS` and pushes the residual failures almost entirely into")
    lines.append("`FAIL_ANCHORING_DISTANCE` without activating any additional offtarget taxonomy.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()

    base_config = yaml.safe_load(BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    smoke_config = yaml.safe_load(SMOKE_CONFIG_PATH.read_text(encoding="utf-8"))
    config_changes = config_diff(base_config, smoke_config)

    analyses: dict[str, Any] = {}
    sample_paths: dict[str, str] = {}

    for library_name, payload in LIBRARIES.items():
        entries = parse_smiles_library(payload["source_library"])
        sample_entries = select_sample(entries, args.sample_size)
        sample_path = OUTPUT_ROOT / "audit-inputs" / f"{library_name}-sample{args.sample_size}.smi"
        write_smiles_library(sample_path, sample_entries)
        sample_paths[library_name] = str(sample_path)

        base_run_id = f"audit-{library_name}-sample{args.sample_size}-base"
        smoke_run_id = f"audit-{library_name}-sample{args.sample_size}-smoke"

        base_summary = run_or_load_phase1(
            config_path=BASE_CONFIG_PATH,
            library_path=sample_path,
            run_id=base_run_id,
            rerun=args.rerun,
        )
        smoke_summary = run_or_load_phase1(
            config_path=SMOKE_CONFIG_PATH,
            library_path=sample_path,
            run_id=smoke_run_id,
            rerun=args.rerun,
        )
        base_analysis = summarize_run(base_summary)
        smoke_analysis = summarize_run(smoke_summary)
        analyses[library_name] = {
            "base": base_analysis,
            "smoke": smoke_analysis,
            "comparison": compare_runs(base_analysis, smoke_analysis),
            "sample_library_path": str(sample_path),
            "base_run_id": base_run_id,
            "smoke_run_id": smoke_run_id,
        }

    cx_rows = build_cxsmiles_table()
    markdown = render_markdown(
        sample_size=args.sample_size,
        config_changes=config_changes,
        sample_paths=sample_paths,
        analyses=analyses,
        cx_rows=cx_rows,
    )

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIT_DIR / "smoke_config_semantic_drift.md").write_text(markdown, encoding="utf-8")
    dump_json(
        AUDIT_DIR / "smoke_config_semantic_drift.json",
        {
            "config_changes": config_changes,
            "sample_paths": sample_paths,
            "analyses": analyses,
            "cxsmiles_rows": cx_rows,
        },
    )
    write_cxsmiles_csv(AUDIT_DIR / "facr2240_cxsmiles_rows.csv", cx_rows)

    print(json.dumps({
        "report_path": str(AUDIT_DIR / "smoke_config_semantic_drift.md"),
        "json_path": str(AUDIT_DIR / "smoke_config_semantic_drift.json"),
        "cxsmiles_csv_path": str(AUDIT_DIR / "facr2240_cxsmiles_rows.csv"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
