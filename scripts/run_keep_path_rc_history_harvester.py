from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crisp.v3.keep_path_rc_history import (
    harvest_keep_path_rc_history,
    write_keep_path_rc_history_report,
    write_keep_path_rc_history_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest extracted hosted keep-path RC artifact bundles into a non-authorizing history report")
    parser.add_argument("--history-root", required=True)
    parser.add_argument("--run-glob", default="hosted-run-*")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    payload = harvest_keep_path_rc_history(
        history_root=args.history_root,
        run_glob=args.run_glob,
    )
    report_path = write_keep_path_rc_history_report(
        output_dir=args.output_dir,
        payload=payload,
    )
    summary_path = write_keep_path_rc_history_summary(
        output_dir=args.output_dir,
        payload=payload,
    )
    print(report_path)
    print(summary_path)
    return 0 if payload.get("history_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
