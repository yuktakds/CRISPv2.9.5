from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crisp.v3.keep_path_rc_gate import evaluate_keep_path_rc_gate, write_keep_path_rc_gate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run keep-path RC gate checks and emit a single gate report")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--docs-root", default=str(REPO_ROOT / "docs"))
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(args.evidence_dir)
    payload = evaluate_keep_path_rc_gate(
        run_dir=args.run_dir,
        docs_root=args.docs_root,
        evidence_dir=args.evidence_dir,
    )
    path = write_keep_path_rc_gate_report(
        output_dir=output_dir,
        payload=payload,
    )
    print(path)
    return 0 if payload.get("gate_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
