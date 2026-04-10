from __future__ import annotations

import argparse
import json
from pathlib import Path

from crisp.v3.m2_ops import (
    M2_POST_CUTOVER_MONITORING_ARTIFACT,
    M2_REHEARSAL_REPORT_ARTIFACT,
    M2_ROLLBACK_DRILL_REPORT_ARTIFACT,
    evaluate_post_cutover_monitoring_window,
    execute_m2_rehearsal,
    execute_m2_rollback_drill,
)


def _load_json_object(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected object payload at {path}, got {type(payload).__name__}")
    return payload


def _write_report(output_dir: Path, artifact_name: str, payload: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / artifact_name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M-2 authority rollback/rehearsal/monitoring package")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rollback_parser = subparsers.add_parser("rollback-drill")
    rollback_parser.add_argument("--run-dir", required=True)
    rollback_parser.add_argument("--output-dir", required=True)

    rehearsal_parser = subparsers.add_parser("rehearsal")
    rehearsal_parser.add_argument("--primary-run-dir", required=True)
    rehearsal_parser.add_argument("--rerun-run-dir", required=True)
    rehearsal_parser.add_argument("--output-dir", required=True)

    monitoring_parser = subparsers.add_parser("monitoring")
    monitoring_parser.add_argument("--readiness-files", nargs="+", required=True)
    monitoring_parser.add_argument("--output-dir", required=True)
    monitoring_parser.add_argument("--required-window-size", type=int, default=30)

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.command == "rollback-drill":
        payload = execute_m2_rollback_drill(args.run_dir)
        path = _write_report(output_dir, M2_ROLLBACK_DRILL_REPORT_ARTIFACT, payload)
        print(path)
        return 0
    if args.command == "rehearsal":
        payload = execute_m2_rehearsal(args.primary_run_dir, args.rerun_run_dir)
        path = _write_report(output_dir, M2_REHEARSAL_REPORT_ARTIFACT, payload)
        print(path)
        return 0

    readiness_payloads = [
        _load_json_object(Path(path_value))
        for path_value in args.readiness_files
    ]
    payload = evaluate_post_cutover_monitoring_window(
        readiness_payloads,
        required_window_size=args.required_window_size,
    )
    path = _write_report(output_dir, M2_POST_CUTOVER_MONITORING_ARTIFACT, payload)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
