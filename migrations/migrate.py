from __future__ import annotations

import argparse
import json
import sys

from migrations.engine import MigrationOptions, run_migration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offline TempleManager DB migration.")
    parser.add_argument("--source", required=True, help="Old source SQLite DB path.")
    parser.add_argument("--target", required=True, help="New target SQLite DB path.")
    parser.add_argument("--version", required=True, help="Migration version module name.")
    parser.add_argument("--backup-dir", required=True, help="Directory for source DB backup.")
    parser.add_argument("--report-dir", required=True, help="Directory for migration reports.")
    parser.add_argument("--dry-run", action="store_true", help="Run against a temporary target DB.")
    parser.add_argument(
        "--replace-target",
        action="store_true",
        help="Delete and rebuild target DB if it already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    options = MigrationOptions(
        source=args.source,
        target=args.target,
        version=args.version,
        backup_dir=args.backup_dir,
        report_dir=args.report_dir,
        dry_run=args.dry_run,
        replace_target=args.replace_target,
    )
    try:
        report = run_migration(options)
    except (FileNotFoundError, FileExistsError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
