from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
from crisp.v29.tableio import write_records_table
from crisp.v3.channels.cap import CapEvidenceChannel
from crisp.v3.channels.catalytic import CatalyticEvidenceChannel
from crisp.v3.path_channel import PathEvidenceChannel
from crisp.v3.scv_bridge import SCVBridge

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def make_config(*, path_model: str = "TUNNEL", blockage_pass_threshold: float = 0.5) -> TargetConfig:
    return TargetConfig(
        target_name="tgt",
        config_role="smoke",
        expected_use="Pipeline health-check regime for end-to-end completion on real data.",
        allowed_comparisons=["cross-regime"],
        frozen_for_regression=False,
        pathway="covalent",
        pdb=PdbConfig(path="s.cif", model_id=1, altloc_policy="first", include_hydrogens=False),
        residue_id_format="auth",
        target_cysteine=AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG"),
        anchor_atom_set=[AtomSpec(chain="A", residue_number=1, insertion_code="", atom_name="SG")],
        offtarget_cysteines=[],
        search_radius=6.0,
        distance_threshold=2.2,
        sampling=SamplingConfig(n_conformers=1, n_rotations=1, n_translations=1, alpha=0.5),
        anchoring=AnchoringConfig(bond_threshold=2.2, near_threshold=3.5, epsilon=0.1),
        offtarget=OfftargetConfig(distance_threshold=2.2, epsilon=0.1),
        scv=ScvConfig(confident_fail_threshold=1, zero_feasible_abort=4096),
        staging=StagingConfig(
            retry_distance_lower=2.2,
            retry_distance_upper=3.5,
            far_target_threshold=6.0,
            max_stage=2,
        ),
        translation=TranslationConfig(
            local_fraction=0.5,
            local_min_radius=1.0,
            local_max_radius=2.0,
            local_start_stage=2,
        ),
        pat=PatConfig(
            path_model=path_model,
            goal_mode="shell",
            grid_spacing=0.5,
            probe_radius=1.4,
            r_outer_margin=2.0,
            blockage_pass_threshold=blockage_pass_threshold,
            top_k_poses=4,
            goal_shell_clearance=0.2,
            goal_shell_thickness=1.0,
            surface_window_radius=4.0,
        ),
        random_seed=42,
    )


def write_pat_payload(path: str | Path, payload: dict[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return out


def load_pat_fixture(name: str) -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / name
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def write_pat_fixture(path: str | Path, name: str) -> Path:
    return write_pat_payload(path, load_pat_fixture(name))


def build_v3_shadow_bundle(
    *,
    run_id: str,
    config: TargetConfig,
    pat_diagnostics_path: str | Path,
    pathyes_force_false: bool = False,
    include_cap: bool = False,
    include_catalytic: bool = False,
):
    result = PathEvidenceChannel().evaluate(
        config=config,
        pat_diagnostics_path=pat_diagnostics_path,
        pathyes_force_false=pathyes_force_false,
    )
    evidences = [] if result.evidence is None else [result.evidence]
    applicability_records = list(result.applicability_records)
    if include_cap:
        cap_rows = [
            {"canonical_link_id": "a", "molecule_id": "n1", "cap_id": "c1", "pairing_role": "native", "comb": 0.82, "PAS": 0.75},
            {"canonical_link_id": "a", "molecule_id": "n2", "cap_id": "c2", "pairing_role": "native", "comb": 0.80, "PAS": 0.72},
            {"canonical_link_id": "a", "molecule_id": "n3", "cap_id": "c3", "pairing_role": "native", "comb": 0.78, "PAS": 0.70},
            {"canonical_link_id": "a", "molecule_id": "f1", "cap_id": "c4", "pairing_role": "matched_falsification", "comb": 0.22, "PAS": 0.18},
            {"canonical_link_id": "a", "molecule_id": "f2", "cap_id": "c5", "pairing_role": "matched_falsification", "comb": 0.20, "PAS": 0.15},
        ]
        pair_features_table = write_records_table(
            Path(pat_diagnostics_path).parent / "pair_features.parquet",
            cap_rows,
        )
        cap_result = CapEvidenceChannel().evaluate(
            pair_features_rows=cap_rows,
            source=pair_features_table.path,
        )
        if cap_result.evidence is not None:
            evidences.append(cap_result.evidence)
        applicability_records.extend(cap_result.applicability_records)
    if include_catalytic:
        catalytic_rows = [
            {
                "run_id": run_id,
                "molecule_id": "m1",
                "target_id": "tgt",
                "candidate_order_hash": "sha256:a",
                "proposal_policy_version": "v29.trace-only.noop",
                "stage_history_json": [{"stage_id": 1}],
                "proposal_trace_json": {
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "candidate_order_hash": "sha256:a",
                    "near_band_triggered": True,
                    "anchor_candidate_atoms": [0, 1, 2],
                    "struct_conn_status": "present",
                },
                "evidence_path": "ignored-a.json",
            },
            {
                "run_id": run_id,
                "molecule_id": "m2",
                "target_id": "tgt",
                "candidate_order_hash": "sha256:b",
                "proposal_policy_version": "v29.trace-only.noop",
                "stage_history_json": [],
                "proposal_trace_json": {
                    "proposal_policy_version": "v29.trace-only.noop",
                    "semantic_mode": "trace-only-noop",
                    "candidate_order_hash": "sha256:b",
                    "near_band_triggered": False,
                    "anchor_candidate_atoms": [0, 1],
                    "struct_conn_status": "missing",
                },
                "evidence_path": "ignored-b.json",
            },
        ]
        evidence_core_table = write_records_table(
            Path(pat_diagnostics_path).parent / "evidence_core.parquet",
            catalytic_rows,
        )
        catalytic_result = CatalyticEvidenceChannel().evaluate(
            evidence_core_rows=catalytic_rows,
            source=evidence_core_table.path,
        )
        if catalytic_result.evidence is not None:
            evidences.append(catalytic_result.evidence)
        applicability_records.extend(catalytic_result.applicability_records)
    return SCVBridge().bundle(
        run_id=run_id,
        evidences=evidences,
        applicability_records=applicability_records,
    )
