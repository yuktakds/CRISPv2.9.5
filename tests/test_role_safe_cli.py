from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from crisp.cli import v29 as role_safe_cli


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def test_role_safe_parser_captures_expected_role() -> None:
    parser = role_safe_cli.build_parser()
    args = parser.parse_args([
        "benchmark",
        "--config", str(CONFIG_DIR / "9kr6_cys328.benchmark.yaml"),
        "--library", "library.smi",
        "--stageplan", "stageplan.json",
        "--out", "outputs/run-1",
    ])

    assert args.expected_config_role == "benchmark"
    assert args.run_mode == "core-only"


def test_role_safe_cli_rejects_config_role_mismatch_before_run(
    monkeypatch,
    capsys,
) -> None:
    called = False

    def fake_run_integrated_v29(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("run_integrated_v29 must not be called on role mismatch")

    monkeypatch.setattr(role_safe_cli, "run_integrated_v29", fake_run_integrated_v29)

    status = role_safe_cli.cmd_run_role_safe(
        Namespace(
            expected_config_role="benchmark",
            config=str(CONFIG_DIR / "9kr6_cys328.production.yaml"),
            library="library.smi",
            stageplan="stageplan.json",
            out="outputs/run-2",
            integrated=None,
            repo_root=None,
            caps=None,
            assays=None,
            run_mode="core+rule1+cap",
            comparison_type=None,
        )
    )

    output = capsys.readouterr().out
    assert status == 2
    assert called is False
    assert "[fail-fast]" in output
    assert "CLI_CONFIG_ROLE_MISMATCH" in output


def test_role_safe_cli_prints_banner_and_artifact_summary(monkeypatch, capsys) -> None:
    out_dir = REPO_ROOT / "outputs" / "role-safe-test"

    def fake_run_integrated_v29(**kwargs):
        return {
            "run_id": "role-safe-test",
            "run_mode": "core+rule1+cap",
            "repo_root": str(REPO_ROOT),
            "repo_root_source": "cli",
            "out_dir": str(out_dir),
            "generated_outputs": [
                "run_manifest.json",
                "output_inventory.json",
                "replay_audit.json",
            ],
            "missing_outputs": [],
            "run_mode_complete": True,
        }

    monkeypatch.setattr(role_safe_cli, "run_integrated_v29", fake_run_integrated_v29)

    status = role_safe_cli.cmd_run_role_safe(
        Namespace(
            expected_config_role="benchmark",
            config=str(CONFIG_DIR / "9kr6_cys328.benchmark.yaml"),
            library="library.smi",
            stageplan="stageplan.json",
            out=str(out_dir),
            integrated=None,
            repo_root=None,
            caps="caps.parquet",
            assays=None,
            run_mode="core+rule1+cap",
            comparison_type=None,
        )
    )

    output = capsys.readouterr().out.splitlines()
    assert status == 0
    assert any(
        "[progress] banner" in line
        and "role=benchmark" in line
        and "comparison=same-config" in line
        and "truth-source=cap_batch_eval.json" in line
        and "core-frozen=true" in line
        for line in output
    )
    assert any(line.startswith("[summary] run_id=role-safe-test") for line in output)
    artifact_lines = [line for line in output if line.startswith("[artifact]")]
    assert len(artifact_lines) == 3
    assert any("run_manifest.json" in line for line in artifact_lines)
