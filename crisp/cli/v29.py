from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent

from crisp.v29.cli import run_integrated_v29
from crisp.v29.console import ConsoleReporter
from crisp.v29.repo import RepoRootResolutionError
from crisp.v29.runtime_contract import IntegratedCliGuardError, resolve_integrated_run_contract

ROLE_SUMMARIES = {
    "benchmark": "Frozen regression baseline. Default comparison_type is same-config.",
    "smoke": "Pipeline health-check regime. Default comparison_type is cross-regime.",
    "production": "Operational run path. Use cross-regime labeling and do not treat it as a regression baseline.",
    "lowsampling": "Diagnostic low-sampling regime for search-collapse inspection only.",
}

HELP_EXAMPLE_LINES = {
    "benchmark": "uv run crisp-v29 benchmark --config configs/9kr6_cys328.benchmark.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-benchmark-smoke",
    "smoke": "uv run crisp-v29 smoke --config configs/9kr6_cys328.smoke.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-smoke-cap --run-mode core+rule1+cap --caps outputs/fixtures/caps.parquet",
    "production": "uv run crisp-v29 production --config configs/9kr6_cys328.production.yaml --library data/libraries/fACR2240.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-production-full --run-mode full --caps outputs/fixtures/caps.parquet --assays outputs/fixtures/assays.parquet",
    "lowsampling": "uv run crisp-v29 lowsampling --config configs/9kr6_cys328.lowsampling.yaml --library data/libraries/CYS-3200.smiles --stageplan configs/stageplan.empty.json --out outputs/runs/9kr6-lowsampling-core",
}

COMPARISON_TYPE_GUIDANCE = dedent(
    """\
    comparison_type guidance:
      same-config  = benchmark-only regression label for identical configs
      cross-regime = cross-config/regime label only; never interpret it as an algorithm comparison
    """
)


def _build_help_epilog() -> str:
    return dedent(
        f"""\
        Role-safe examples:
          benchmark   {HELP_EXAMPLE_LINES['benchmark']}
          smoke       {HELP_EXAMPLE_LINES['smoke']}
          production  {HELP_EXAMPLE_LINES['production']}
          lowsampling {HELP_EXAMPLE_LINES['lowsampling']}

        {COMPARISON_TYPE_GUIDANCE}
        """
    )


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", help="Explicit repository root. Default: auto-resolve from --out.")
    parser.add_argument("--config", required=True, help="Target config YAML. Must match the selected role-safe subcommand.")
    parser.add_argument("--library", required=True, help="Input library file (.smiles/.smi/.parquet/.jsonl).")
    parser.add_argument("--stageplan", required=True, help="Stageplan JSON used by the frozen core bridge.")
    parser.add_argument("--integrated", help="Optional integrated companion config for PAT/theta/seeds.")
    parser.add_argument("--out", required=True, help="Run output directory. Existing stale manifests are guarded before execution.")
    parser.add_argument("--caps", help="Cap fixture/table path. Required for core+rule1+cap and full.")
    parser.add_argument("--assays", help="Assay table path. Required for full.")
    parser.add_argument(
        "--run-mode",
        choices=["core-only", "core+rule1", "core+rule1+cap", "full", "rule1-bootstrap"],
        default="core-only",
        help=(
            "Integrated run envelope. rule1-bootstrap aliases to core+rule1. "
            "full is a local heavy-run boundary, not a required CI claim."
        ),
    )
    parser.add_argument(
        "--comparison-type",
        help=(
            "Explicit report/replay comparison label. cross-regime means cross-config/regime labeling only; "
            "same-config is benchmark-only."
        ),
    )


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
    parser = argparse.ArgumentParser(
        prog="crisp-v29",
        description="Role-safe wrapper for v2.9.5 integrated runs.",
        epilog=_build_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for role in ("benchmark", "smoke", "production", "lowsampling"):
        p = sub.add_parser(
            role,
            help=ROLE_SUMMARIES[role],
            description=f"{ROLE_SUMMARIES[role]}\n\n{COMPARISON_TYPE_GUIDANCE}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        _add_run_args(p)
        p.set_defaults(func=cmd_run_role_safe, expected_config_role=role)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
