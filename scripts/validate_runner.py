"""CLI validate runner: invokes the validator and prints a fixed-format summary."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ATLAS Open Data remote validation and print a summary."
    )
    parser.add_argument(
        "--dataset-ref",
        default="dsid:410470",
        help="Dataset reference (default: dsid:410470 = ttbar MC)",
    )
    parser.add_argument(
        "--protocol",
        choices=["root", "https"],
        default="root",
        help="Access protocol: 'root' (xrootd) or 'https' (default: root)",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Local cache directory (optional; uses fsspec simplecache)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Number of files in subset (default: 3 collision / 1 MC)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    from atlas_workbench.core.manifest_builder import build_manifest
    from atlas_workbench.core.subset_planner import select_subset
    from atlas_workbench.core.validator import run_validation

    try:
        manifest = build_manifest(
            dataset_ref=args.dataset_ref,
            protocol=args.protocol,
        )
    except Exception as exc:
        print(f"RESULT: ERROR\nMANIFEST BUILD FAILED: {exc}")
        sys.exit(1)

    collection_type = "mc" if "dsid:" in args.dataset_ref else "collision"
    plan = select_subset(
        urls=[f.file_url_root for f in manifest.files],
        collection_type=collection_type,
        n=args.n,
        dataset_ref=args.dataset_ref,
    )

    try:
        report = run_validation(plan, protocol=args.protocol)
    except Exception as exc:
        print(f"RESULT: ERROR\nVALIDATION EXCEPTION: {exc}")
        sys.exit(1)

    print(f"RESULT: {'PASS' if report.success else 'FAIL'}")
    print(f"BYTES_READ: {report.bytes_read}")
    print(f"WALL_TIME: {report.wall_time:.3f}s")
    print(f"BRANCHES_READ: {', '.join(report.branches_read) or 'none'}")
    if report.error_logs:
        print("ERRORS:")
        for e in report.error_logs:
            print(f"  {e}")

    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
