from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from crisp.config.loader import load_target_config
from crisp.cpg.structure import check_target_residue_exists
from crisp.evidence.writer import write_evidence_artifact
from crisp.mef.filter import run_mef
from crisp.repro.hashing import (
    compute_config_hash,
    compute_input_hash,
    compute_requirements_hash,
    parse_smiles_library,
)
from crisp.repro.manifest import (
    build_mef_run_sidecar_manifest,
    mef_sidecar_manifest_path,
    write_sidecar_manifest,
)
from crisp.utils.jsonx import canonical_json_bytes


def _write_smiles_library(path: Path, entries: list[tuple[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{smiles} {name}\n" for smiles, name in entries)
    path.write_text(body, encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for row in rows:
            fh.write(canonical_json_bytes(row))
            fh.write(b"\n")
    return path


def run_mef_library(
    *,
    repo_root: Path,
    config_path: Path,
    library_path: Path,
    run_id: str,
) -> dict[str, Any]:
    config = load_target_config(config_path)
    config_hash = compute_config_hash(config)
    requirements_hash = compute_requirements_hash()

    # MEF-06 is target-level validation, so run it once before the per-compound census.
    check_target_residue_exists(repo_root, config)

    entries = parse_smiles_library(library_path)
    out_root = repo_root / "outputs" / run_id
    libraries_root = out_root / "libraries"
    report_path = out_root / "mef_report.jsonl"
    summary_path = out_root / "summary.json"
    pass_library_path = libraries_root / "mef_pass.smi"
    fail_library_path = libraries_root / "mef_fail.smi"
    manifest_path = mef_sidecar_manifest_path(repo_root, run_id)

    reason_counts: Counter[str] = Counter()
    pass_entries: list[tuple[str, str]] = []
    fail_entries: list[tuple[str, str]] = []
    report_rows: list[dict[str, Any]] = []

    for index, (smiles, name) in enumerate(entries, start=1):
        result = run_mef(smiles, config, repo_root, skip_pdb_check=True)
        if result.passed:
            pass_entries.append((smiles, name))
            reason_counts["MEF_PASS"] += 1
        else:
            fail_entries.append((smiles, name))
            reason_counts[str(result.reason)] += 1

        report_rows.append(
            {
                "index": index,
                "mef_run_id": run_id,
                "name": name,
                "smiles": smiles,
                "passed": result.passed,
                "reason": result.reason,
                "heavy_atom_count": result.heavy_atom_count,
                "rotatable_bonds": result.rotatable_bonds,
                "config_hash": config_hash,
                "requirements_hash": requirements_hash,
                "input_hash": compute_input_hash(smiles, requirements_hash),
                "matched_smarts": [
                    {
                        "smarts_index": match.smarts_index,
                        "pattern": match.pattern,
                        "mapped_atoms": list(match.mapped_atoms),
                    }
                    for match in result.matched_smarts
                ],
                "warhead_atoms_union": list(result.warhead_atoms_union),
            }
        )

    _write_jsonl(report_path, report_rows)
    _write_smiles_library(pass_library_path, pass_entries)
    _write_smiles_library(fail_library_path, fail_entries)
    write_sidecar_manifest(
        manifest_path,
        build_mef_run_sidecar_manifest(
            run_id=run_id,
            config_path=config_path,
            config=config,
            library_path=library_path,
            report_path=report_path,
            summary_path=summary_path,
            mef_pass_library_path=pass_library_path,
            mef_fail_library_path=fail_library_path,
            config_hash=config_hash,
            requirements_hash=requirements_hash,
        ),
    )

    payload = {
        "run_id": run_id,
        "config_path": str(config_path),
        "library_path": str(library_path),
        "config_hash": config_hash,
        "requirements_hash": requirements_hash,
        "structure_validation": {
            "performed": True,
            "target_dependent": True,
        },
        "summary": {
            "total_compounds": len(entries),
            "passed_compounds": len(pass_entries),
            "failed_compounds": len(fail_entries),
            "reason_counts": dict(reason_counts),
        },
        "libraries": {
            "mef_pass": str(pass_library_path),
            "mef_fail": str(fail_library_path),
        },
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "manifest_path": str(manifest_path),
    }
    write_evidence_artifact(summary_path, payload)
    return payload
