from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crisp.v3.release_packet_smoke import (
    KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT,
    build_keep_path_release_packet_snapshot,
    evaluate_keep_path_release_packet_smoke,
    write_keep_path_release_packet_smoke_report,
    write_keep_path_release_packet_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the keep-path RC release packet snapshot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--packet-dir", required=True)
    snapshot_parser.add_argument("--evidence-dir", required=True)
    snapshot_parser.add_argument("--output-dir", required=True)

    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--packet-dir", required=True)
    smoke_parser.add_argument("--evidence-dir", required=True)
    smoke_parser.add_argument("--snapshot-path")
    smoke_parser.add_argument("--output-dir", required=True)

    args = parser.parse_args()

    if args.command == "snapshot":
        payload = build_keep_path_release_packet_snapshot(
            packet_dir=args.packet_dir,
            evidence_dir=args.evidence_dir,
        )
        path = write_keep_path_release_packet_snapshot(
            output_dir=args.output_dir,
            payload=payload,
        )
        print(path)
        return 0

    snapshot_path = (
        Path(args.snapshot_path)
        if args.snapshot_path
        else Path(args.output_dir) / KEEP_PATH_RC_RELEASE_PACKET_SNAPSHOT_ARTIFACT
    )
    payload = evaluate_keep_path_release_packet_smoke(
        packet_dir=args.packet_dir,
        evidence_dir=args.evidence_dir,
        snapshot_path=snapshot_path,
    )
    path = write_keep_path_release_packet_smoke_report(
        output_dir=args.output_dir,
        payload=payload,
    )
    print(path)
    return 0 if payload.get("smoke_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
