from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from crisp.config.loader import load_target_config
from crisp.repro.hashing import compute_config_hash
from crisp.v29.contracts import CoreBridgeResult
from crisp.v29.inputs import load_molecule_rows
from crisp.v29.rule1_theta import write_theta_rule1_calibration_table
from crisp.v29.tableio import read_records_table, write_records_table


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"
DATA_DIR = REPO_ROOT / "data"


def write_real_library_subset(
    source_path: str | Path,
    out_path: str | Path,
    *,
    limit: int = 2,
) -> Path:
    source = Path(source_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    selected_lines: list[str] = []
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        selected_lines.append(raw_line)
        if len(selected_lines) >= limit:
            break

    if len(selected_lines) < limit:
        raise ValueError(
            f"real-data library subset requires at least {limit} rows: {source}"
        )

    out.write_text("\n".join(selected_lines) + "\n", encoding="utf-8")
    return out


def write_pat_diagnostics(
    path: str | Path,
    *,
    goal_precheck_passed: bool = True,
    supported_path_model: bool = True,
    extra_diagnostics: dict[str, Any] | None = None,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "supported_path_model": supported_path_model,
        "goal_precheck_passed": goal_precheck_passed,
        "pat_run_diagnostics_json": {
            "probe_count": 4,
            "goal_shell_clearance": 0.2,
            **({} if extra_diagnostics is None else dict(extra_diagnostics)),
        },
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return out


def write_managed_theta_table(
    path: str | Path,
    *,
    config_path: str | Path,
    table_version: str = "2026-04-03",
    calibration_cohort: str = "smoke",
    calibrated_by: str = "tests.v29_smoke_helpers",
) -> Path:
    config = load_target_config(config_path)
    config_hash = compute_config_hash(config)
    result = write_theta_rule1_calibration_table(
        path,
        values_by_key={
            "default": 1.0,
            config.pathway: 1.0,
            config.target_name: 0.8,
        },
        table_version=table_version,
        table_source=(
            f"benchmark:{Path(config_path).name} "
            f"seed={config.random_seed} cohort={calibration_cohort}"
        ),
        benchmark_config_path=str(Path(config_path)),
        benchmark_config_hash=config_hash,
        calibration_seed=config.random_seed,
        calibration_cohort=calibration_cohort,
        calibrated_by=calibrated_by,
    )
    return Path(result.path)


def write_minimal_caps_fixture(
    path: str | Path,
    *,
    target_id: str,
) -> Path:
    result = write_records_table(
        path,
        [
            {
                "cap_id": "cap_native",
                "target_id": target_id,
                "axis_x": 1.0,
                "axis_y": 0.0,
                "axis_z": 0.0,
                "polar_coords_json": "[]",
                "motion_class": "m",
                "source_db": "fixture",
                "source_entry_id": "native-1",
                "derivation_method": "manual",
                "is_canonical_cap": True,
            },
            {
                "cap_id": "cap_alt",
                "target_id": target_id,
                "axis_x": 0.0,
                "axis_y": 1.0,
                "axis_z": 0.0,
                "polar_coords_json": "[]",
                "motion_class": "m",
                "source_db": "fixture",
                "source_entry_id": "alt-1",
                "derivation_method": "manual",
                "is_canonical_cap": False,
            },
        ],
    )
    return Path(result.path)


def write_minimal_assays_fixture(
    path: str | Path,
    *,
    target_id: str,
    molecule_ids: list[str],
) -> Path:
    if not molecule_ids:
        raise ValueError("molecule_ids must not be empty")
    rows = [
        {
            "canonical_link_id": f"link-{index + 1}",
            "molecule_id": molecule_id,
            "target_id": target_id,
            "condition_hash": f"condition-{index + 1}",
            "functional_score_raw": 1.0 - (index * 0.1),
            "assay_type": "activity",
            "direction": "increase",
            "unit": "a.u.",
        }
        for index, molecule_id in enumerate(molecule_ids)
    ]
    result = write_records_table(path, rows)
    return Path(result.path)


def create_minimal_full_mode_fixture_bundle(base_dir: str | Path) -> dict[str, Path]:
    base = Path(base_dir)
    repo_root = base / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        "[project]\nname=\"crisp\"\nversion=\"0.0.0\"\n",
        encoding="utf-8",
    )
    structure_path = repo_root / "s.cif"
    structure_path.write_text("data_dummy\n", encoding="utf-8")
    config_path = repo_root / "cfg.yaml"
    config_path.write_text(
        f"""target_name: tgt
config_role: smoke
expected_use: Pipeline health-check regime for end-to-end completion on real data.
allowed_comparisons: [cross-regime]
frozen_for_regression: false
pathway: covalent
pdb:
  path: {structure_path}
  model_id: 1
  altloc_policy: first
  include_hydrogens: false
residue_id_format: auth
target_cysteine: {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
anchor_atom_set:
  - {{chain: A, residue_number: 1, insertion_code: '', atom_name: SG}}
offtarget_cysteines:
  - {{chain: B, residue_number: 2, insertion_code: '', atom_name: SG}}
search_radius: 6.0
distance_threshold: 2.2
sampling: {{n_conformers: 1, n_rotations: 1, n_translations: 1, alpha: 0.5}}
anchoring: {{bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}}
offtarget: {{distance_threshold: 2.2, epsilon: 0.1}}
scv: {{confident_fail_threshold: 1, zero_feasible_abort: 4096}}
staging: {{retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}}
translation: {{local_fraction: 0.5, local_min_radius: 1.0, local_max_radius: 2.0, local_start_stage: 2}}
pat: {{path_model: TUNNEL, goal_mode: shell, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 2.0, blockage_pass_threshold: 0.5, top_k_poses: 4, goal_shell_clearance: 0.2, goal_shell_thickness: 1.0, surface_window_radius: 4.0}}
random_seed: 42
""",
        encoding="utf-8",
    )
    library_result = write_records_table(
        repo_root / "molecules.parquet",
        [
            {"molecule_id": "m1", "smiles": "CCO", "library_id": "fixture", "input_order": 0},
            {"molecule_id": "m2", "smiles": "CCN", "library_id": "fixture", "input_order": 1},
        ],
    )
    library_path = Path(library_result.path)
    caps_path = write_minimal_caps_fixture(repo_root / "caps.parquet", target_id="tgt")
    assays_path = write_minimal_assays_fixture(
        repo_root / "assays.parquet",
        target_id="tgt",
        molecule_ids=["m1", "m2"],
    )
    stageplan_path = repo_root / "stageplan.json"
    stageplan_path.write_text("{}", encoding="utf-8")
    return {
        "repo_root": repo_root,
        "config_path": config_path,
        "library_path": library_path,
        "caps_path": caps_path,
        "assays_path": assays_path,
        "stageplan_path": stageplan_path,
    }


def make_stub_core_bridge(
    *,
    library_path: str | Path,
    target_id: str,
) -> Callable[..., CoreBridgeResult]:
    molecule_rows = load_molecule_rows(library_path)

    def _fake_run_core_bridge(**kwargs: Any) -> CoreBridgeResult:
        out_dir = Path(kwargs["out_dir"])
        core_rows = [
            {
                "run_id": out_dir.name,
                "molecule_id": str(row["molecule_id"]),
                "target_id": target_id,
                "core_verdict": "PASS",
                "core_reason_code": None,
                "best_target_distance": 1.0,
                "best_offtarget_distance": 5.0,
                "final_stage": 1,
                "config_hash": "cfg",
                "legacy_core_final_verdict": "PASS",
            }
            for row in molecule_rows
        ]
        evidence_rows = [
            {
                "run_id": out_dir.name,
                "molecule_id": str(row["molecule_id"]),
                "target_id": target_id,
                "stage_id": 1,
                "translation_type": "global",
                "trial_number": 1,
                "stopped_at_trial": 1,
                "early_stop_reason": None,
                "anchoring_witness_pose_json": {},
                "anchoring_fail_certificate_json": {},
                "candidate_order_hash": f"h-{row['molecule_id']}",
                "near_band_triggered": False,
                "proposal_policy_version": "v29",
                "config_hash": "cfg",
                "requirements_hash": "req",
                "input_hash": f"inp-{row['molecule_id']}",
                "core_verdict": "PASS",
                "core_reason_code": None,
                "legacy_core_final_verdict": "PASS",
                "stage_history_json": [],
                "proposal_trace_json": {
                    "anchor_candidate_atoms": [0, 1, 1, 2],
                    "anchor_candidate_sources": [
                        {"atom_index": 0, "source": "struct_conn"},
                        {"atom_index": 1, "source": "smarts_union"},
                        {"atom_index": 1, "source": "near_band"},
                        {"atom_index": 2, "source": "near_band"},
                    ],
                    "candidate_order_hash": f"h-{row['molecule_id']}",
                    "near_band_triggered": True,
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "struct_conn_status": "present",
                },
            }
            for row in molecule_rows
        ]
        core_table = write_records_table(out_dir / "core_compounds.parquet", core_rows)
        evidence_table = write_records_table(out_dir / "evidence_core.parquet", evidence_rows)
        diagnostics_path = out_dir / "core_bridge_diagnostics.json"
        diagnostics_path.write_text(
            json.dumps({"ok": True, "record_count": len(molecule_rows)}, sort_keys=True),
            encoding="utf-8",
        )
        return CoreBridgeResult(
            core_rows_path=core_table.path,
            evidence_core_path=evidence_table.path,
            diagnostics_path=str(diagnostics_path),
            config_hash="cfg",
            input_hash="inp",
            requirements_hash="req",
            materialization_events=[
                core_table.to_materialization_event(logical_output="core_compounds.parquet"),
                evidence_table.to_materialization_event(logical_output="evidence_core.parquet"),
            ],
        )

    return _fake_run_core_bridge


def required_cap_smoke_outputs() -> list[str]:
    return [
        "run_manifest.json",
        "output_inventory.json",
        "core_compounds.parquet",
        "rule1_assessments.parquet",
        "theta_rule1_resolution.json",
        "rule3_trace_summary.json",
        "cap_batch_eval.json",
        "qc_report.json",
        "eval_report.json",
        "collapse_figure_spec.json",
        "replay_audit.json",
    ]


def required_full_smoke_outputs() -> list[str]:
    return required_cap_smoke_outputs() + [
        "mapping_table.parquet",
        "falsification_table.parquet",
        "pair_features.parquet",
        "evidence_pairs.parquet",
    ]


def row_count(path: str | Path) -> int:
    return len(read_records_table(path))


def assert_outputs_exist(out_dir: str | Path, outputs: list[str]) -> None:
    base = Path(out_dir)
    missing = [name for name in outputs if not (base / name).exists()]
    if missing:
        raise AssertionError(f"missing outputs: {missing}")
