"""CRISP CLI エントリポイント。

サブコマンド:
  doctor              環境診断
  validate-target-config  TargetConfig の検証
  print-hashes        再現性ハッシュの出力
  write-run-manifest  run-level manifest の生成
  run-mef-library     ライブラリ全体の MEF census
  run-phase1-single   単一化合物の Phase 1 評価
  run-phase1-library  ライブラリ全体の Phase 1 評価
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from crisp.cli.mef import run_mef_library
from crisp.cli.phase1 import run_phase1_library, run_phase1_single
from crisp.config.loader import load_target_config
from crisp.repro.hashing import compute_config_hash, compute_input_hash, compute_requirements_hash
from crisp.repro.manifest import build_run_manifest, write_run_manifest
from crisp.v29.cli import run_integrated_v29, run_replay_audit_v29
from crisp.v29.validation import run_validation_batch
from crisp.v29.repo import RepoRootResolutionError, resolve_repo_root


def find_repo_root(start: Path | None = None) -> Path:
    """pyproject.toml を含むリポジトリルートを探索する。"""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repo root containing pyproject.toml")


def find_repo_root_v29(
    *, explicit_repo_root: str | None = None, start: Path | None = None,
) -> tuple[Path, str]:
    resolution = resolve_repo_root(explicit_repo_root=explicit_repo_root, start=start)
    return resolution.repo_root, resolution.source


def cmd_doctor(_: argparse.Namespace) -> int:
    info = {
        "repo_root": str(find_repo_root()),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "uv_version": None,
        "git_version": None,
    }
    try:
        import subprocess
        info["uv_version"] = subprocess.check_output(["uv", "--version"], text=True).strip()
        info["git_version"] = subprocess.check_output(["git", "--version"], text=True).strip()
    except Exception:
        pass
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def cmd_validate_target_config(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    cfg = load_target_config(Path(args.config).resolve())
    payload = {
        "target_name": cfg.target_name,
        "config_hash": compute_config_hash(cfg),
        "resolved_structure_path": str(cfg.resolve_structure_path(repo_root)),
        "path_model": cfg.pat.path_model,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_print_hashes(args: argparse.Namespace) -> int:
    cfg = load_target_config(Path(args.config).resolve())
    requirements_hash = compute_requirements_hash()
    payload = {
        "target_name": cfg.target_name,
        "requirements_hash": requirements_hash,
        "config_hash": compute_config_hash(cfg),
        "input_hash": compute_input_hash(args.smiles, requirements_hash),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_write_run_manifest(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    config_path = Path(args.config).resolve()
    cfg = load_target_config(config_path)
    manifest = build_run_manifest(
        run_id=args.run_id, repo_root=repo_root, config_path=config_path,
        config=cfg, library_path=Path(args.library).resolve(),
        stageplan_path=Path(args.stageplan).resolve(),
    )
    out = write_run_manifest(args.out, manifest)
    print(str(out))
    return 0


def cmd_run_phase1_single(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    result = run_phase1_single(
        repo_root=repo_root,
        config_path=Path(args.config).resolve(),
        smiles=args.smiles,
    )
    print(json.dumps(result.evidence, indent=2, ensure_ascii=False))
    return 0


def cmd_run_mef_library(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    payload = run_mef_library(
        repo_root=repo_root,
        config_path=Path(args.config).resolve(),
        library_path=Path(args.library).resolve(),
        run_id=args.run_id,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_run_phase1_library(args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    payload = run_phase1_library(
        repo_root=repo_root,
        config_path=Path(args.config).resolve(),
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
    try:
        payload = run_integrated_v29(
        repo_root=args.repo_root,
        config_path=Path(args.config).resolve(),
        library_path=Path(args.library).resolve(),
        stageplan_path=Path(args.stageplan).resolve(),
        out_dir=Path(args.out).resolve(),
        integrated_config_path=(None if args.integrated is None else Path(args.integrated).resolve()),
        run_mode=args.run_mode,
        caps_path=(None if args.caps is None else Path(args.caps).resolve()),
        assays_path=(None if args.assays is None else Path(args.assays).resolve()),
        )
    except RepoRootResolutionError as exc:
        print(json.dumps({"error_code": exc.code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_run_replay_audit_v29(args: argparse.Namespace) -> int:
    payload = run_replay_audit_v29(manifest_path=Path(args.manifest).resolve())
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_run_validation_v29(args: argparse.Namespace) -> int:
    payload = run_validation_batch(Path(args.manifest).resolve(), args.profile, Path(args.out).resolve())
    print(json.dumps({
        "conditions_run": payload.conditions_run,
        "qc_report_path": payload.qc_report_path,
        "eval_report_path": payload.eval_report_path,
        "collapse_figure_spec_path": payload.collapse_figure_spec_path,
        "result": payload.result,
    }, indent=2, ensure_ascii=False))
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crisp")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)

    p = sub.add_parser("validate-target-config")
    p.add_argument("--config", required=True)
    p.set_defaults(func=cmd_validate_target_config)

    p = sub.add_parser("print-hashes")
    p.add_argument("--config", required=True)
    p.add_argument("--smiles", required=True)
    p.set_defaults(func=cmd_print_hashes)

    p = sub.add_parser("write-run-manifest")
    p.add_argument("--config", required=True)
    p.add_argument("--stageplan", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_write_run_manifest)

    p = sub.add_parser("run-phase1-single")
    p.add_argument("--config", required=True)
    p.add_argument("--smiles", required=True)
    p.set_defaults(func=cmd_run_phase1_single)

    p = sub.add_parser("run-mef-library")
    p.add_argument("--config", required=True)
    p.add_argument("--library", required=True)
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_run_mef_library)

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
    p.add_argument("--run-mode", choices=["core-only", "core+rule1", "core+rule1+cap", "full", "rule1-bootstrap"], default="core-only")
    p.set_defaults(func=cmd_run_integrated_v29)

    p = sub.add_parser("run-replay-audit-v29")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=cmd_run_replay_audit_v29)

    p = sub.add_parser("run-validation-v29")
    p.add_argument("--manifest", required=True)
    p.add_argument("--profile", default="smoke")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_run_validation_v29)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
