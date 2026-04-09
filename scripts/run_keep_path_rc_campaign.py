from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crisp.v3.keep_path_rc_campaign import materialize_keep_path_rc_campaign, write_keep_path_rc_campaign_index


def _resolve_run_dirs(*, runs_root: Path, run_glob: str) -> list[Path]:
    return sorted(
        [path for path in runs_root.glob(run_glob) if path.is_dir()],
        key=lambda item: item.name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run keep-path RC gate checks across a fixed run set")
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--run-glob", default="run-*")
    parser.add_argument("--docs-root", default=str(REPO_ROOT / "docs"))
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    run_dirs = _resolve_run_dirs(runs_root=runs_root, run_glob=args.run_glob)
    payload = materialize_keep_path_rc_campaign(
        run_dirs=run_dirs,
        docs_root=args.docs_root,
        evidence_dir=args.evidence_dir,
        output_dir=args.output_dir,
    )
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.evidence_dir)
    path = write_keep_path_rc_campaign_index(
        output_dir=output_dir,
        payload=payload,
    )
    print(path)
    return 0 if payload.get("aggregate", {}).get("campaign_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
