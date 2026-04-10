from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from crisp.cli.main import (
    cmd_assert_config_comparison,
    cmd_assert_regression_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def test_cmd_assert_regression_config_passes_for_benchmark(capsys) -> None:
    status = cmd_assert_regression_config(
        Namespace(config=str(CONFIG_DIR / "9kr6_cys328.benchmark.yaml"))
    )
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["result"] == "PASS"
    assert payload["config_role"] == "benchmark"


def test_cmd_assert_regression_config_rejects_smoke() -> None:
    with pytest.raises(ValueError, match="frozen_for_regression=true"):
        cmd_assert_regression_config(
            Namespace(config=str(CONFIG_DIR / "9kr6_cys328.smoke.yaml"))
        )


def test_cmd_assert_config_comparison_passes_for_cross_regime(capsys) -> None:
    status = cmd_assert_config_comparison(
        Namespace(
            lhs_config=str(CONFIG_DIR / "9kr6_cys328.lowsampling.yaml"),
            rhs_config=str(CONFIG_DIR / "9kr6_cys328.smoke.yaml"),
            comparison_type="cross-regime",
        )
    )
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["result"] == "PASS"
    assert payload["comparison_type"] == "cross-regime"


def test_cmd_assert_config_comparison_rejects_same_config_for_smoke() -> None:
    with pytest.raises(ValueError, match="comparison_type='same-config'"):
        cmd_assert_config_comparison(
            Namespace(
                lhs_config=str(CONFIG_DIR / "9kr6_cys328.smoke.yaml"),
                rhs_config=str(CONFIG_DIR / "9kr6_cys328.production.yaml"),
                comparison_type="same-config",
            )
        )
