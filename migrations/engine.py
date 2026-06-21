from __future__ import annotations

import importlib
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.database.setup_db import initialize_database
from migrations.backup import backup_source_db
from migrations.reports import write_reports
from migrations.schema_inventory import (
    diff_inventories,
    inventory_database,
    list_user_tables,
    quote_identifier,
    table_columns,
)
from migrations.validators import run_common_validations


Validator = Callable[[sqlite3.Connection, sqlite3.Connection, list[str]], list[dict[str, Any]]]


@dataclass(frozen=True)
class MigrationSpec:
    name: str
    tables: list[str] | None = None
    column_defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    validators: list[Validator] = field(default_factory=list)
    allowed_target_only_tables: set[str] = field(default_factory=set)
    allowed_target_only_columns: dict[str, set[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class MigrationOptions:
    source: str
    target: str
    version: str
    backup_dir: str
    report_dir: str
    dry_run: bool = False
    replace_target: bool = False


def load_migration_spec(version: str) -> MigrationSpec:
    module_name = f"migrations.versions.{version}"
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ValueError(f"Migration version not found: {version}") from exc
    spec = getattr(module, "MIGRATION", None)
    if not isinstance(spec, MigrationSpec):
        raise TypeError(f"{module_name}.MIGRATION must be a MigrationSpec")
    return spec


def open_connection(db_path: str, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def prepare_target_db(target_db: str, *, replace_target: bool) -> None:
    target = Path(target_db)
    if target.exists():
        if not replace_target:
            raise FileExistsError(
                f"Target DB already exists: {target}. Use --replace-target to rebuild it."
            )
        _remove_sqlite_files(target)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Failed to create target DB directory: {target.parent}") from exc

    initialize_database(str(target))


def _remove_sqlite_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(db_path) + suffix)
        if not target.exists():
            continue
        try:
            target.unlink()
        except OSError as exc:
            raise OSError(f"Failed to remove existing target artifact: {target}") from exc


def resolve_tables(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    spec: MigrationSpec,
) -> list[str]:
    if spec.tables is not None:
        return list(spec.tables)
    source_tables = set(list_user_tables(source_conn))
    target_tables = set(list_user_tables(target_conn))
    return sorted(source_tables & target_tables)


def copy_table(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table_name: str,
    column_defaults: dict[str, Any],
) -> int:
    source_cols = [col.name for col in table_columns(source_conn, table_name)]
    target_cols = [col.name for col in table_columns(target_conn, table_name)]
    insert_cols = [
        col for col in target_cols
        if col in source_cols or col in column_defaults
    ]
    select_cols = [col for col in insert_cols if col in source_cols]

    if not insert_cols:
        return 0

    source_sql = ", ".join(quote_identifier(col) for col in select_cols)
    insert_sql = ", ".join(quote_identifier(col) for col in insert_cols)
    placeholders = ", ".join("?" for _ in insert_cols)

    rows = source_conn.execute(
        f"SELECT {source_sql} FROM {quote_identifier(table_name)}"
    ).fetchall()
    payload = []
    for row in rows:
        payload.append(
            tuple(row[col] if col in source_cols else column_defaults[col] for col in insert_cols)
        )

    target_conn.execute(f"DELETE FROM {quote_identifier(table_name)}")
    if payload:
        target_conn.executemany(
            f"INSERT INTO {quote_identifier(table_name)} ({insert_sql}) VALUES ({placeholders})",
            payload,
        )
    return len(payload)


def validate_schema_compatibility(
    source_db: str,
    spec: MigrationSpec,
) -> None:
    with tempfile.TemporaryDirectory(prefix="temple_migration_preflight_") as temp_dir:
        reference_target = str(Path(temp_dir) / "current_schema.db")
        initialize_database(reference_target)
        schema_diff = diff_inventories(
            inventory_database(source_db),
            inventory_database(reference_target),
        )

    incompatible_entries = [
        f"source-only table: {table_name}"
        for table_name in schema_diff["tables_only_in_source"]
    ]
    for table_name, column_diff in schema_diff["column_diffs"].items():
        incompatible_entries.extend(
            f"source-only column: {table_name}.{column_name}"
            for column_name in column_diff["missing_in_target"]
        )

    incompatible_entries.extend(
        f"unexpected target-only table: {table_name}"
        for table_name in schema_diff["tables_only_in_target"]
        if table_name not in spec.allowed_target_only_tables
    )
    for table_name, column_diff in schema_diff["column_diffs"].items():
        allowed_columns = spec.allowed_target_only_columns.get(table_name, set())
        incompatible_entries.extend(
            f"unexpected target-only column: {table_name}.{column_name}"
            for column_name in column_diff["added_in_target"]
            if column_name not in allowed_columns
        )

    if incompatible_entries:
        details = "\n".join(f"- {entry}" for entry in incompatible_entries)
        raise ValueError(
            "Migration preflight rejected incompatible schema entries:\n"
            f"{details}"
        )


def run_migration(options: MigrationOptions) -> dict[str, Any]:
    source = Path(options.source)
    if not source.is_file():
        raise FileNotFoundError(f"Source DB not found: {source}")

    spec = load_migration_spec(options.version)
    validate_schema_compatibility(options.source, spec)
    backup_path = backup_source_db(options.source, options.backup_dir)

    if options.dry_run:
        with tempfile.TemporaryDirectory(prefix="temple_migration_") as temp_dir:
            temp_target = str(Path(temp_dir) / "dry_run_target.db")
            return _run_migration_to_target(
                options=options,
                spec=spec,
                backup_path=backup_path,
                actual_target=temp_target,
                display_target=options.target,
                replace_target=True,
            )

    return _run_migration_to_target(
        options=options,
        spec=spec,
        backup_path=backup_path,
        actual_target=options.target,
        display_target=options.target,
        replace_target=options.replace_target,
    )


def _run_migration_to_target(
    *,
    options: MigrationOptions,
    spec: MigrationSpec,
    backup_path: str,
    actual_target: str,
    display_target: str,
    replace_target: bool,
) -> dict[str, Any]:
    prepare_target_db(actual_target, replace_target=replace_target)

    source_conn = open_connection(options.source, readonly=True)
    target_conn = open_connection(actual_target)
    copied_tables: list[dict[str, Any]] = []
    validation_issues: list[dict[str, Any]] = []
    try:
        tables = resolve_tables(source_conn, target_conn, spec)
        target_conn.execute("PRAGMA foreign_keys = OFF")
        target_conn.execute("BEGIN")
        for table in tables:
            rows = copy_table(
                source_conn,
                target_conn,
                table,
                spec.column_defaults.get(table, {}),
            )
            copied_tables.append({"table": table, "rows": rows})
        target_conn.commit()

        validation_issues.extend(run_common_validations(source_conn, target_conn, tables))
        for validator in spec.validators:
            validation_issues.extend(validator(source_conn, target_conn, tables))

        source_inventory = inventory_database(options.source)
        target_inventory = inventory_database(actual_target)
        schema_diff = diff_inventories(source_inventory, target_inventory)
        report = {
            "version": spec.name,
            "dry_run": options.dry_run,
            "source": options.source,
            "target": display_target,
            "actual_target": actual_target,
            "backup": backup_path,
            "copied_tables": copied_tables,
            "schema_diff": schema_diff,
            "validation_issues": validation_issues,
            "success": not validation_issues,
        }
        report["report_files"] = write_reports(report, options.report_dir)
        return report
    except sqlite3.Error as exc:
        target_conn.rollback()
        raise RuntimeError(f"Migration failed while writing target DB {actual_target}: {exc}") from exc
    finally:
        target_conn.close()
        source_conn.close()
