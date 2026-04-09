from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crisp.v3.keep_path_rc_audit import (
    evaluate_keep_path_rc_hostile_audit,
    write_keep_path_rc_hostile_audit_report,
    write_keep_path_rc_hostile_audit_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a keep-path RC hostile audit bundle from fixed docs and evidence"
    )
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--history-report-path")
    parser.add_argument(
        "--workflow-path",
        default=".github/workflows/v3-keep-path-rc-exploratory.yml",
    )
    args = parser.parse_args()

    payload = evaluate_keep_path_rc_hostile_audit(
        docs_root=args.docs_root,
        evidence_dir=args.evidence_dir,
        repo_root=args.repo_root,
        history_report_path=args.history_report_path,
        workflow_path=args.workflow_path,
    )
    report_path = write_keep_path_rc_hostile_audit_report(
        output_dir=args.output_dir,
        payload=payload,
    )
    summary_path = write_keep_path_rc_hostile_audit_summary(
        output_dir=args.output_dir,
        payload=payload,
    )
    print(report_path)
    print(summary_path)
    return 0 if payload.get("audit_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
