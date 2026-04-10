from __future__ import annotations

from pathlib import Path

from crisp.config.loader import load_target_config
from crisp.config.models import (
    AnchoringConfig,
    AtomSpec,
    OfftargetConfig,
    PatConfig,
    PdbConfig,
    SamplingConfig,
    ScvConfig,
    StagingConfig,
    TargetConfig,
    TranslationConfig,
)
from crisp.repro.hashing import compute_config_hash
from crisp.v29.rule1_theta import (
    THETA_RULE1_RUNTIME_CONTRACT,
    ThetaRule1RuntimeError,
    load_theta_rule1_runtime_table,
    resolve_theta_rule1,
    trace_theta_rule1_resolution,
    write_theta_rule1_calibration_table,
)
from crisp.v29.validators import validate_theta_rule1_runtime_table


def _config() -> TargetConfig:
    return TargetConfig(
        target_name="tgt",
        config_role="benchmark",
        expected_use="Frozen regression baseline for parser, search, and reason-taxonomy changes.",
        allowed_comparisons=["same-config", "cross-regime"],
        frozen_for_regression=True,
        pathway="covalent",
        pdb=PdbConfig(path="x.cif", model_id=1, altloc_policy="first", include_hydrogens=False),
        residue_id_format="auth",
        target_cysteine=AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG"),
        anchor_atom_set=[AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG")],
        offtarget_cysteines=[],
        search_radius=5.0,
        distance_threshold=2.2,
        sampling=SamplingConfig(n_conformers=1, n_rotations=1, n_translations=1, alpha=0.8),
        anchoring=AnchoringConfig(bond_threshold=2.2, near_threshold=3.5, epsilon=0.1),
        offtarget=OfftargetConfig(distance_threshold=5.0, epsilon=0.1),
        scv=ScvConfig(confident_fail_threshold=1, zero_feasible_abort=4096),
        staging=StagingConfig(retry_distance_lower=2.2, retry_distance_upper=3.5, far_target_threshold=6.0, max_stage=2),
        translation=TranslationConfig(local_fraction=0.5, local_min_radius=0.5, local_max_radius=1.5, local_start_stage=2),
        pat=PatConfig(path_model="TUNNEL", goal_mode="anchor", grid_spacing=0.5, probe_radius=1.4, r_outer_margin=1.0, blockage_pass_threshold=0.5, top_k_poses=5, goal_shell_clearance=0.5, goal_shell_thickness=1.0, surface_window_radius=2.0),
        random_seed=42,
    )


def test_load_theta_rule1_runtime_table_reads_managed_metadata(tmp_path: Path) -> None:
    table = write_theta_rule1_calibration_table(
        tmp_path / "theta_rule1_table.parquet",
        values_by_key={"default": 1.0, "tgt": 0.8},
        table_version="2026-04-03",
        table_source="benchmark:9kr6 seed=42 cohort=fold0",
        benchmark_config_path="configs/9kr6_cys328.benchmark.yaml",
        benchmark_config_hash="cfg-hash",
        calibration_seed=42,
        calibration_cohort="fold0",
        calibrated_by="test-suite",
    )

    runtime_table = load_theta_rule1_runtime_table(table.path, require_managed=True)

    assert runtime_table.table_id.startswith("table:")
    assert runtime_table.table_version == "2026-04-03"
    assert runtime_table.table_source == "benchmark:9kr6 seed=42 cohort=fold0"
    assert runtime_table.table_digest is not None and runtime_table.table_digest.startswith("sha256:")
    assert runtime_table.runtime_contract == THETA_RULE1_RUNTIME_CONTRACT
    assert runtime_table.calibration_metadata["benchmark_config_role"] == "benchmark"
    assert runtime_table.calibration_metadata["calibration_seed"] == 42
    assert resolve_theta_rule1(runtime_table, config=_config()) == 0.8


def test_validate_theta_rule1_runtime_table_reports_provenance_and_resolution(
    tmp_path: Path,
) -> None:
    benchmark_config_path = tmp_path / "benchmark.yaml"
    benchmark_config_path.write_text(
        """target_name: tgt
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons: [same-config, cross-regime]
frozen_for_regression: true
pathway: covalent
pdb:
  path: x.cif
  model_id: 1
  altloc_policy: first
  include_hydrogens: false
residue_id_format: auth
target_cysteine: {chain: A, residue_number: 1, insertion_code: '', atom_name: SG}
anchor_atom_set:
  - {chain: A, residue_number: 1, insertion_code: '', atom_name: SG}
offtarget_cysteines: []
search_radius: 5.0
distance_threshold: 2.2
sampling: {n_conformers: 1, n_rotations: 1, n_translations: 1, alpha: 0.8}
anchoring: {bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}
offtarget: {distance_threshold: 5.0, epsilon: 0.1}
scv: {confident_fail_threshold: 1, zero_feasible_abort: 4096}
staging: {retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}
translation: {local_fraction: 0.5, local_min_radius: 0.5, local_max_radius: 1.5, local_start_stage: 2}
pat: {path_model: TUNNEL, goal_mode: anchor, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 1.0, blockage_pass_threshold: 0.5, top_k_poses: 5, goal_shell_clearance: 0.5, goal_shell_thickness: 1.0, surface_window_radius: 2.0}
random_seed: 42
""",
        encoding="utf-8",
    )
    benchmark_config_hash = compute_config_hash(load_target_config(benchmark_config_path))
    table = write_theta_rule1_calibration_table(
        tmp_path / "theta_rule1_table.parquet",
        values_by_key={"default": 1.0, "tgt": 0.8},
        table_version="2026-04-03",
        table_source="benchmark:tgt seed=42 cohort=fold0",
        benchmark_config_path=str(benchmark_config_path),
        benchmark_config_hash=benchmark_config_hash,
        calibration_seed=42,
        calibration_cohort="fold0",
        calibrated_by="test-suite",
    )

    runtime_table = load_theta_rule1_runtime_table(table.path, require_managed=True)
    trace = trace_theta_rule1_resolution(runtime_table, config=_config())
    errors, warnings, diagnostics = validate_theta_rule1_runtime_table(
        runtime_table,
        config=_config(),
        config_path=benchmark_config_path,
        resolution_trace=trace,
    )

    assert errors == []
    assert warnings == []
    assert diagnostics["benchmark_config_loaded"] is True
    assert diagnostics["resolved_lookup_key"] == "tgt"
    assert diagnostics["resolution_status"] == "exact_target"
    assert diagnostics["validator_errors"] == []


def test_validate_theta_rule1_runtime_table_rejects_scope_mismatch(tmp_path: Path) -> None:
    mismatched_benchmark_path = tmp_path / "benchmark-other.yaml"
    mismatched_benchmark_path.write_text(
        """target_name: other
config_role: benchmark
expected_use: Frozen regression baseline for parser, search, and reason-taxonomy changes.
allowed_comparisons: [same-config, cross-regime]
frozen_for_regression: true
pathway: noncovalent
pdb:
  path: x.cif
  model_id: 1
  altloc_policy: first
  include_hydrogens: false
residue_id_format: auth
target_cysteine: {chain: A, residue_number: 1, insertion_code: '', atom_name: SG}
anchor_atom_set:
  - {chain: A, residue_number: 1, insertion_code: '', atom_name: SG}
offtarget_cysteines: []
search_radius: 5.0
distance_threshold: 2.2
sampling: {n_conformers: 1, n_rotations: 1, n_translations: 1, alpha: 0.8}
anchoring: {bond_threshold: 2.2, near_threshold: 3.5, epsilon: 0.1}
offtarget: {distance_threshold: 5.0, epsilon: 0.1}
scv: {confident_fail_threshold: 1, zero_feasible_abort: 4096}
staging: {retry_distance_lower: 2.2, retry_distance_upper: 3.5, far_target_threshold: 6.0, max_stage: 2}
translation: {local_fraction: 0.5, local_min_radius: 0.5, local_max_radius: 1.5, local_start_stage: 2}
pat: {path_model: TUNNEL, goal_mode: anchor, grid_spacing: 0.5, probe_radius: 1.4, r_outer_margin: 1.0, blockage_pass_threshold: 0.5, top_k_poses: 5, goal_shell_clearance: 0.5, goal_shell_thickness: 1.0, surface_window_radius: 2.0}
random_seed: 42
""",
        encoding="utf-8",
    )
    mismatched_benchmark_hash = compute_config_hash(load_target_config(mismatched_benchmark_path))
    table = write_theta_rule1_calibration_table(
        tmp_path / "theta_rule1_scope_mismatch.parquet",
        values_by_key={"other": 0.7},
        table_version="2026-04-03",
        table_source="benchmark:other seed=42 cohort=fold0",
        benchmark_config_path=str(mismatched_benchmark_path),
        benchmark_config_hash=mismatched_benchmark_hash,
        calibration_seed=42,
        calibration_cohort="fold0",
        calibrated_by="test-suite",
    )

    runtime_table = load_theta_rule1_runtime_table(table.path, require_managed=True)
    trace = trace_theta_rule1_resolution(runtime_table, config=_config())
    errors, warnings, diagnostics = validate_theta_rule1_runtime_table(
        runtime_table,
        config=_config(),
        config_path=mismatched_benchmark_path,
        resolution_trace=trace,
    )

    assert warnings == []
    assert "THETA_RULE1_SCOPE_MISMATCH:['target_name', 'pathway']" in errors
    assert "THETA_RULE1_SCOPE_MISMATCH:NO_MATCHING_LOOKUP_KEY" in errors
    assert diagnostics["validator_errors"]


def test_load_theta_rule1_runtime_table_requires_managed_file_when_requested() -> None:
    try:
        load_theta_rule1_runtime_table(None, require_managed=True)
    except ThetaRule1RuntimeError as exc:
        assert exc.code == "THETA_RULE1_TABLE_MISSING"
    else:
        raise AssertionError("expected managed theta_rule1 requirement to fail")


def test_load_theta_rule1_runtime_table_rejects_stale_table(tmp_path: Path) -> None:
    table = write_theta_rule1_calibration_table(
        tmp_path / "theta_rule1_table.parquet",
        values_by_key={"default": 1.0},
        table_version="2026-04-03",
        table_source="benchmark:9kr6 seed=42 cohort=fold0",
        benchmark_config_path="configs/9kr6_cys328.benchmark.yaml",
        benchmark_config_hash="cfg-hash",
        calibration_seed=42,
        calibration_cohort="fold0",
        calibrated_by="test-suite",
        table_status="stale",
    )

    try:
        load_theta_rule1_runtime_table(table.path, require_managed=True)
    except ThetaRule1RuntimeError as exc:
        assert exc.code == "THETA_RULE1_TABLE_STALE"
    else:
        raise AssertionError("expected stale theta_rule1 table to fail")


def test_load_theta_rule1_runtime_table_rejects_incompatible_runtime_contract(
    tmp_path: Path,
) -> None:
    table = write_theta_rule1_calibration_table(
        tmp_path / "theta_rule1_table.parquet",
        values_by_key={"default": 1.0},
        table_version="2026-04-03",
        table_source="benchmark:9kr6 seed=42 cohort=fold0",
        benchmark_config_path="configs/9kr6_cys328.benchmark.yaml",
        benchmark_config_hash="cfg-hash",
        calibration_seed=42,
        calibration_cohort="fold0",
        calibrated_by="test-suite",
    )
    path = Path(table.path)
    rows = load_theta_rule1_runtime_table(table.path, require_managed=True)
    assert rows.runtime_contract == THETA_RULE1_RUNTIME_CONTRACT

    import pandas as pd  # type: ignore[import]

    df = pd.read_parquet(path)
    df["runtime_contract"] = "crisp.v29.theta_rule1.runtime/v0"
    df.to_parquet(path)

    try:
        load_theta_rule1_runtime_table(path, require_managed=True)
    except ThetaRule1RuntimeError as exc:
        assert exc.code == "THETA_RULE1_TABLE_INCOMPATIBLE_RUNTIME"
    else:
        raise AssertionError("expected incompatible theta_rule1 runtime contract to fail")
