from __future__ import annotations

from crisp.v3.pathyes import (
    PAT_DIAGNOSTICS_INVALID_SKIP_CODE,
    PAT_DIAGNOSTICS_MISSING_SKIP_CODE,
    PAT_GOAL_PRECHECK_SOURCE,
    PathYesState,
    pathyes_contract_fields,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _state(**overrides: object) -> PathYesState:
    defaults: dict = {
        "supported_path_model": True,
        "goal_precheck_passed": True,
        "pat_run_diagnostics_json": {},
        "rule1_applicability": "applicable",
    }
    defaults.update(overrides)
    return PathYesState(**defaults)


# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------


def test_pat_diagnostics_missing_skip_code_is_string() -> None:
    assert isinstance(PAT_DIAGNOSTICS_MISSING_SKIP_CODE, str)
    assert PAT_DIAGNOSTICS_MISSING_SKIP_CODE.startswith("SKIP_")


def test_pat_diagnostics_invalid_skip_code_is_string() -> None:
    assert isinstance(PAT_DIAGNOSTICS_INVALID_SKIP_CODE, str)
    assert PAT_DIAGNOSTICS_INVALID_SKIP_CODE.startswith("SKIP_")


def test_pat_goal_precheck_source_references_diagnostics() -> None:
    assert "pat_diagnostics" in PAT_GOAL_PRECHECK_SOURCE
    assert "goal_precheck" in PAT_GOAL_PRECHECK_SOURCE


def test_skip_codes_are_distinct() -> None:
    assert PAT_DIAGNOSTICS_MISSING_SKIP_CODE != PAT_DIAGNOSTICS_INVALID_SKIP_CODE


# ---------------------------------------------------------------------------
# pathyes_contract_fields
# ---------------------------------------------------------------------------


def test_contract_fields_has_eight_keys() -> None:
    result = pathyes_contract_fields(_state())

    assert len(result) == 8


def test_contract_fields_all_keys_prefixed_pathyes() -> None:
    result = pathyes_contract_fields(_state())

    assert all(k.startswith("pathyes_") for k in result.keys())


def test_contract_fields_goal_precheck_passed_true() -> None:
    result = pathyes_contract_fields(_state(goal_precheck_passed=True))

    assert result["pathyes_goal_precheck_passed"] is True


def test_contract_fields_goal_precheck_passed_none() -> None:
    result = pathyes_contract_fields(_state(goal_precheck_passed=None))

    assert result["pathyes_goal_precheck_passed"] is None


def test_contract_fields_rule1_applicability_preserved() -> None:
    result = pathyes_contract_fields(_state(rule1_applicability="not_applicable"))

    assert result["pathyes_rule1_applicability"] == "not_applicable"


def test_contract_fields_skip_code_none_by_default() -> None:
    result = pathyes_contract_fields(_state())

    assert result["pathyes_skip_code"] is None


def test_contract_fields_skip_code_preserved() -> None:
    result = pathyes_contract_fields(
        _state(skip_code=PAT_DIAGNOSTICS_MISSING_SKIP_CODE)
    )

    assert result["pathyes_skip_code"] == PAT_DIAGNOSTICS_MISSING_SKIP_CODE


def test_contract_fields_mode_none_by_default() -> None:
    result = pathyes_contract_fields(_state())

    assert result["pathyes_mode_resolved"] is None


def test_contract_fields_source_none_by_default() -> None:
    result = pathyes_contract_fields(_state())

    assert result["pathyes_state_source"] is None


def test_contract_fields_diagnostics_error_code_none_by_default() -> None:
    result = pathyes_contract_fields(_state())

    assert result["pathyes_diagnostics_error_code"] is None
