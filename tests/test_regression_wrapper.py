from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from crisp.cli import regression


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def test_load_regression_config_accepts_benchmark() -> None:
    config = regression.load_regression_config(
        config_path=(CONFIG_DIR / "9kr6_cys328.benchmark.yaml").resolve(),
        context="test",
    )
    assert config.config_role == "benchmark"
    assert config.frozen_for_regression is True


def test_load_regression_config_rejects_smoke() -> None:
    with pytest.raises(ValueError, match="frozen_for_regression=true"):
        regression.load_regression_config(
            config_path=(CONFIG_DIR / "9kr6_cys328.smoke.yaml").resolve(),
            context="test",
        )


def test_load_regression_config_rejects_production() -> None:
    with pytest.raises(ValueError, match="frozen_for_regression=true"):
        regression.load_regression_config(
            config_path=(CONFIG_DIR / "9kr6_cys328.production.yaml").resolve(),
            context="test",
        )


def test_regression_wrapper_phase1_single_invokes_underlying_runner(monkeypatch, capsys) -> None:
    calls: list[tuple[Path, str]] = []

    monkeypatch.setattr(regression, "find_repo_root", lambda: REPO_ROOT)

    def fake_run_phase1_single(*, repo_root: Path, config_path: Path, smiles: str):
        calls.append((config_path, smiles))
        return SimpleNamespace(evidence={"verdict": "PASS", "reason": None})

    monkeypatch.setattr(regression, "run_phase1_single", fake_run_phase1_single)

    status = regression.cmd_run_phase1_single(
        Namespace(
            config=str(CONFIG_DIR / "9kr6_cys328.benchmark.yaml"),
            smiles="CCO",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["verdict"] == "PASS"
    assert calls == [((CONFIG_DIR / "9kr6_cys328.benchmark.yaml").resolve(), "CCO")]
