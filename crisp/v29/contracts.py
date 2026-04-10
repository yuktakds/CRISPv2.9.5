from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


RunMode = Literal["core-only", "core+rule1", "core+rule1+cap", "full"]
ProposalMode = Literal["legacy_passthrough", "ordered_bridge"]
TableFormat = Literal["parquet", "jsonl"]


@dataclass(frozen=True, slots=True)
class CoreBridgeResult:
    core_rows_path: str
    core_compounds_path: str
    evidence_core_path: str
    diagnostics_path: str
    config_hash: str
    input_hash: str
    requirements_hash: str
    materialization_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PathYesState:
    supported_path_model: bool
    goal_precheck_passed: bool | None
    pat_run_diagnostics_json: dict[str, Any]
    rule1_applicability: str
    skip_code: str | None = None
    mode: str | None = None
    source: str | None = None
    diagnostics_status: str | None = None
    diagnostics_error_code: str | None = None
    diagnostics_source_path: str | None = None
    sanitized_fields_removed: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Rule1Assessment:
    run_id: str | None
    molecule_id: str
    smiles: str
    rotatable_bonds: int
    largest_rigid_block_heavy_atoms: int
    rigid_fraction: float
    ring_lock_present: bool
    shape_proxy_evaluable: bool
    within_calibration_domain: bool
    rigid_volume_proxy: float
    rule1_applicability: str
    pathyes_state_json: dict[str, Any]
    theta_rule1: float
    rule1_verdict: str | None
    rule1_reason_code: str | None


@dataclass(frozen=True, slots=True)
class TableWriteResult:
    path: str
    format: TableFormat
    row_count: int
    primary_path: str | None = None
    primary_format: TableFormat | None = None
    fallback_used: bool = False
    fallback_reason_code: str | None = None
    fallback_reason_detail: str | None = None

    def to_materialization_event(self, *, logical_output: str) -> dict[str, Any]:
        return {
            "logical_output": logical_output,
            "primary_path": self.primary_path or logical_output,
            "materialized_path": self.path,
            "primary_format": self.primary_format,
            "materialized_format": self.format,
            "fallback_used": self.fallback_used,
            "fallback_reason_code": self.fallback_reason_code,
            "fallback_reason_detail": self.fallback_reason_detail,
        }


@dataclass(frozen=True, slots=True)
class IntegratedRunManifest:
    run_id: str
    spec_version: str
    run_mode: RunMode
    resource_profile: str
    target_case_id: str
    target_config_path: str
    target_config_role: str
    target_config_expected_use: str
    target_config_allowed_comparisons: list[str]
    target_config_frozen_for_regression: bool
    structure_path: str
    library_path: str
    stageplan_path: str
    config_hash: str
    input_hash: str
    requirements_hash: str
    library_hash: str
    compound_order_hash: str
    staging_plan_hash: str
    structure_file_digest: str
    rotation_seed: int
    shuffle_seed: int
    bootstrap_seed: int
    cv_seed: int
    label_shuffle_seed: int
    shuffle_universe_scope: str
    shuffle_donor_pool_hash: str | None
    donor_plan_hash: str | None
    functional_score_dictionary_id: str
    theta_rule1_table_id: str
    requested_branches: list[str]
    implemented_branches: list[str]
    generated_outputs: list[str]
    repo_root_source: str
    repo_root_resolved_path: str
    completion_basis_json: dict[str, Any]
    theta_rule1_table_version: str | None = None
    theta_rule1_table_digest: str | None = None
    theta_rule1_table_source: str | None = None
    theta_rule1_runtime_contract: str | None = None


@dataclass(frozen=True, slots=True)
class OutputInventory:
    run_id: str
    run_mode: RunMode
    requested_branches: list[str]
    implemented_branches: list[str]
    generated_outputs: list[str]
    missing_outputs: list[str]
    schema_validation: dict[str, Any]
    warnings: list[str]
    run_mode_complete: bool
    branch_status_json: dict[str, Any]
    completion_basis_json: dict[str, Any]
    completion_checks_json: dict[str, Any]
    repo_root_source: str
    repo_root_resolved_path: str


@dataclass(frozen=True, slots=True)
class CapBatchEval:
    run_id: str
    status: str
    cap_batch_verdict: str | None
    cap_batch_reason_code: str | None
    source_of_truth: bool = True
    diagnostics_json: dict[str, Any] = field(default_factory=dict)
    verdict_layer0: str | None = None
    verdict_layer1: str | None = None
    verdict_layer2: str | None = None
    verdict_final: str | None = None
    reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Layer2Result:
    status: str
    n_rows_mapping: int
    n_rows_falsification: int
    cv_r2_m1_base: float | None
    cv_r2_m1_full: float | None
    cv_r2_m2_base: float | None
    cv_r2_m2_full: float | None
    delta_cv_r2_m1: float | None
    delta_cv_r2_m2: float | None
    bootstrap_ci_m1: tuple[float, float] | None
    bootstrap_ci_m2: tuple[float, float] | None
    r_shuffle_joint: float | None
    diagnostics_json: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationBatchResult:
    conditions_run: list[str]
    qc_report_path: str
    eval_report_path: str
    collapse_figure_spec_path: str
    result: str
