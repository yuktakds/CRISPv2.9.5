from __future__ import annotations

from crisp.v29.pathyes import PathYesState
from crisp.v29.rule1 import compute_rule1_assessment


def test_rule1_sensor_detects_ring_lock_for_fused_ring() -> None:
    state = PathYesState(
        supported_path_model=True,
        goal_precheck_passed=None,
        pat_run_diagnostics_json={"mode": "bootstrap"},
        rule1_applicability="PATH_NOT_EVALUABLE",
    )
    result = compute_rule1_assessment(molecule_id="naphthalene", smiles="c1ccc2ccccc2c1", pathyes_state=state)
    assert result.ring_lock_present is True
    assert result.largest_rigid_block_heavy_atoms >= 6
    assert result.rule1_applicability == "PATH_NOT_EVALUABLE"


# ---------------------------------------------------------------------------
# Rule1RigiditySensor / Rule1SCV クラス分離の確認 (FAIL-1 修正確認)
# ---------------------------------------------------------------------------

from crisp.v29.rule1 import Rule1RigiditySensor, Rule1SCV, compute_rule1_assessment
from crisp.v29.contracts import PathYesState


def _bootstrap_state(applicability: str = "PATH_NOT_EVALUABLE") -> PathYesState:
    return PathYesState(
        supported_path_model=True,
        goal_precheck_passed=None,
        pat_run_diagnostics_json={"mode": "bootstrap"},
        rule1_applicability=applicability,
        skip_code=None,
    )


def _evaluable_state() -> PathYesState:
    return PathYesState(
        supported_path_model=True,
        goal_precheck_passed=True,
        pat_run_diagnostics_json={"mode": "pat-backed"},
        rule1_applicability="PATH_EVALUABLE",
        skip_code=None,
    )


class TestRule1RigiditySensor:
    def test_sensor_returns_tuple_of_7(self) -> None:
        """Sensor は観測量 7 要素のタプルを返す（verdict を含まない）。"""
        vals = Rule1RigiditySensor.measure("C=CC(=O)NCC1CC1")
        assert len(vals) == 7

    def test_sensor_invalid_smiles_returns_zeros(self) -> None:
        vals = Rule1RigiditySensor.measure("INVALID_SMILES_XYZ")
        assert vals == (0, 0, 0.0, False, False, False, 0.0)

    def test_ring_lock_detected_for_fused_ring(self) -> None:
        # ナフタレン: 2つの6員環が2原子を共有 → ring_lock = True
        naphthalene = "c1ccc2ccccc2c1"
        vals = Rule1RigiditySensor.measure(naphthalene)
        assert vals[3] is True, "Fused ring should have ring_lock_present=True"

    def test_no_ring_lock_for_single_ring(self) -> None:
        cyclohexane = "C1CCCCC1"
        vals = Rule1RigiditySensor.measure(cyclohexane)
        assert vals[3] is False

    def test_rigid_volume_proxy_formula(self) -> None:
        # 単純分子: RVP = largest_rigid / (1 + rotatable_bonds)
        vals = Rule1RigiditySensor.measure("CCC")  # propane: no ring, 1 rot bond
        rotatable, largest, _, _, _, _, rvp = vals
        expected = largest / (1 + rotatable) if (1 + rotatable) > 0 else 0.0
        assert abs(rvp - expected) < 1e-9


class TestRule1SCV:
    def test_scv_suppressed_in_bootstrap_mode(self) -> None:
        """FAIL-1 修正確認: bootstrap mode では verdict = None (公開しない)。"""
        verdict, reason = Rule1SCV.decide(
            ring_lock_present=True,
            shape_proxy_evaluable=True,
            within_calibration_domain=True,
            rigid_volume_proxy=2.0,
            theta_rule1=1.0,
            pathyes_state=_bootstrap_state(),
        )
        assert verdict is None, "bootstrap mode must suppress verdict"
        assert reason is None

    def test_scv_fail_no_ring_lock(self) -> None:
        verdict, reason = Rule1SCV.decide(
            ring_lock_present=False,
            shape_proxy_evaluable=True,
            within_calibration_domain=True,
            rigid_volume_proxy=2.0,
            theta_rule1=1.0,
            pathyes_state=_evaluable_state(),
        )
        assert verdict == "FAIL"
        assert reason == "FAIL_R1_NO_RING_LOCK"

    def test_scv_pass_when_rigid_enough(self) -> None:
        verdict, reason = Rule1SCV.decide(
            ring_lock_present=True,
            shape_proxy_evaluable=True,
            within_calibration_domain=True,
            rigid_volume_proxy=1.5,
            theta_rule1=1.0,
            pathyes_state=_evaluable_state(),
        )
        assert verdict == "PASS"
        assert reason is None

    def test_scv_fail_too_flexible(self) -> None:
        verdict, reason = Rule1SCV.decide(
            ring_lock_present=True,
            shape_proxy_evaluable=True,
            within_calibration_domain=True,
            rigid_volume_proxy=0.5,
            theta_rule1=1.0,
            pathyes_state=_evaluable_state(),
        )
        assert verdict == "FAIL"
        assert reason == "FAIL_R1_TOO_FLEXIBLE"

    def test_scv_unclear_not_evaluable(self) -> None:
        verdict, reason = Rule1SCV.decide(
            ring_lock_present=True,
            shape_proxy_evaluable=False,
            within_calibration_domain=True,
            rigid_volume_proxy=2.0,
            theta_rule1=1.0,
            pathyes_state=_evaluable_state(),
        )
        assert verdict == "UNCLEAR"
        assert reason == "UNCLEAR_R1_NOT_EVALUABLE"


class TestComputeRule1Assessment:
    def test_full_assessment_bootstrap(self) -> None:
        assessment = compute_rule1_assessment(
            molecule_id="mol_001",
            smiles="c1ccc2ccccc2c1",
            pathyes_state=_bootstrap_state(),
        )
        assert assessment.molecule_id == "mol_001"
        assert assessment.rule1_verdict is None
        assert assessment.rule1_reason_code is None
        assert assessment.ring_lock_present is True

    def test_full_assessment_evaluable(self) -> None:
        # ナフタレン: ring_lock=True, rigid_volume_proxy 大 → PASS
        assessment = compute_rule1_assessment(
            molecule_id="nap",
            smiles="c1ccc2ccccc2c1",
            pathyes_state=_evaluable_state(),
            theta_rule1=1.0,
        )
        assert assessment.rule1_verdict == "PASS"
