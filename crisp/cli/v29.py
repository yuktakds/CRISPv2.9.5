from __future__ import annotations

import argparse
import json
from pathlib import Path

from crisp.v29.cli import run_integrated_v29
from crisp.v29.console import ConsoleReporter
from crisp.v29.repo import RepoRootResolutionError
from crisp.v29.runtime_contract import IntegratedCliGuardError, resolve_integrated_run_contract


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root")
    parser.add_argument("--config", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--stageplan", required=True)
    parser.add_argument("--integrated")
    parser.add_argument("--out", required=True)
    parser.add_argument("--caps")
    parser.add_argument("--assays")
    parser.add_argument(
        "--run-mode",
        choices=["core-only", "core+rule1", "core+rule1+cap", "full", "rule1-bootstrap"],
        default="core-only",
    )
    parser.add_argument("--comparison-type")


def cmd_run_role_safe(args: argparse.Namespace) -> int:
    reporter = ConsoleReporter()
    try:
        contract = resolve_integrated_run_contract(
            config_path=args.config,
            integrated_config_path=args.integrated,
            run_mode=args.run_mode,
            expected_config_role=args.expected_config_role,
            comparison_type_override=args.comparison_type,
            context="crisp-v29 role-safe run",
        )
    except IntegratedCliGuardError as exc:
        reporter.fail_fast(str(exc))
        return 2
    except ValueError as exc:
        reporter.fail_fast(str(exc))
        return 2

    reporter.banner(contract, out_dir=args.out)
    reporter.progress("starting integrated run")
    try:
        payload = run_integrated_v29(
            repo_root=args.repo_root,
            config_path=Path(args.config).resolve(),
            library_path=Path(args.library).resolve(),
            stageplan_path=Path(args.stageplan).resolve(),
            out_dir=Path(args.out).resolve(),
            integrated_config_path=(
                None if args.integrated is None else Path(args.integrated).resolve()
            ),
            run_mode=args.run_mode,
            caps_path=(None if args.caps is None else Path(args.caps).resolve()),
            assays_path=(None if args.assays is None else Path(args.assays).resolve()),
            reporter=reporter,
        )
    except RepoRootResolutionError as exc:
        reporter.fail_fast(f"{exc.code}: {exc}")
        return 2
    except Exception as exc:
        reporter.fail_fast(str(exc))
        return 2

    reporter.summary(
        f"run_id={payload['run_id']} complete={str(bool(payload['run_mode_complete'])).lower()} "
        f"missing={len(payload['missing_outputs'])}"
    )
    for artifact_name in payload["generated_outputs"]:
        reporter.artifact(Path(payload["out_dir"]) / artifact_name)
    if payload["missing_outputs"]:
        reporter.warn(f"missing outputs: {json.dumps(payload['missing_outputs'], ensure_ascii=False)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crisp-v29")
    sub = parser.add_subparsers(dest="command", required=True)

    for role in ("benchmark", "smoke", "production", "lowsampling"):
        p = sub.add_parser(role)
        _add_run_args(p)
        p.set_defaults(func=cmd_run_role_safe, expected_config_role=role)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
