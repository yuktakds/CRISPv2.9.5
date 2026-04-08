"""Regression-only CLI wrapper.

This entrypoint exists to remove the human step of adding
`--require-frozen-for-regression` to ad hoc commands. All subcommands here
require a frozen regression config and reject smoke/production profiles before
any run starts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crisp.cli.mef import run_mef_library
from crisp.cli.phase1 import run_phase1_library, run_phase1_single
from crisp.config.loader import load_target_config
from crisp.v29.cli import run_integrated_v29
from crisp.v29.repo import RepoRootResolutionError


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repo root containing pyproject.toml")


def load_regression_config(*, config_path: Path, context: str):
    config = load_target_config(config_path)
    config.assert_regression_ready(context=context, config_path=config_path)
    return config


def cmd_run_mef_library(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    config_path = Path(args.config).resolve()
    load_regression_config(
        config_path=config_path,
        context="crisp-regression run-mef-library",
    )
    payload = run_mef_library(
        repo_root=repo_root,
        config_path=config_path,
        library_path=Path(args.library).resolve(),
        run_id=args.run_id,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_run_phase1_single(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    config_path = Path(args.config).resolve()
    load_regression_config(
        config_path=config_path,
        context="crisp-regression run-phase1-single",
    )
    result = run_phase1_single(
        repo_root=repo_root,
        config_path=config_path,
        smiles=args.smiles,
    )
    print(json.dumps(result.evidence, indent=2, ensure_ascii=False))
    return 0


def cmd_run_phase1_library(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    config_path = Path(args.config).resolve()
    load_regression_config(
        config_path=config_path,
        context="crisp-regression run-phase1-library",
    )
    payload = run_phase1_library(
        repo_root=repo_root,
        config_path=config_path,
        library_path=Path(args.library).resolve(),
        run_id=args.run_id,
        stageplan_path=Path(args.stageplan).resolve(),
        prefilter_report_path=(
            None if args.prefilter_report is None else Path(args.prefilter_report).resolve()
        ),
        show_progress=not args.no_progress,
        progress_every=args.progress_every,
        progress_seconds=args.progress_seconds,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_run_integrated_v29(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    load_regression_config(
        config_path=config_path,
        context="crisp-regression run-integrated-v29",
    )
    try:
        payload = run_integrated_v29(
            repo_root=args.repo_root,
            config_path=config_path,
            library_path=Path(args.library).resolve(),
            stageplan_path=Path(args.stageplan).resolve(),
            out_dir=Path(args.out).resolve(),
            integrated_config_path=(
                None if args.integrated is None else Path(args.integrated).resolve()
            ),
            run_mode=args.run_mode,
            caps_path=(None if args.caps is None else Path(args.caps).resolve()),
            assays_path=(None if args.assays is None else Path(args.assays).resolve()),
        )
    except RepoRootResolutionError as exc:
        print(
            json.dumps({"error_code": exc.code, "message": str(exc)}, ensure_ascii=False),
        )
        return 2
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crisp-regression")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run-mef-library")
    p.add_argument("--config", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_run_mef_library)

    p = sub.add_parser("run-phase1-single")
    p.add_argument("--config", required=True)
    p.add_argument("--smiles", required=True)
    p.set_defaults(func=cmd_run_phase1_single)

    p = sub.add_parser("run-phase1-library")
    p.add_argument("--config", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--stageplan", required=True)
    p.add_argument("--prefilter-report")
    p.add_argument("--progress-every", type=int, default=25)
    p.add_argument("--progress-seconds", type=float, default=15.0)
    p.add_argument("--no-progress", action="store_true")
    p.set_defaults(func=cmd_run_phase1_library)

    p = sub.add_parser("run-integrated-v29")
    p.add_argument("--repo-root")
    p.add_argument("--config", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--stageplan", required=True)
    p.add_argument("--integrated")
    p.add_argument("--out", required=True)
    p.add_argument("--caps")
    p.add_argument("--assays")
    p.add_argument(
        "--run-mode",
        choices=["core-only", "core+rule1", "core+rule1+cap", "full", "rule1-bootstrap"],
        default="core-only",
    )
    p.set_defaults(func=cmd_run_integrated_v29)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
