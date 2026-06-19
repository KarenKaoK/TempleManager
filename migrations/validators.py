from __future__ import annotations

import sqlite3
from typing import Any

from migrations.schema_inventory import quote_identifier, table_columns


MAX_VALIDATION_SAMPLES = 20


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def row_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}").fetchone()
    return int(row[0] if row is not None else 0)


def validate_row_counts(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    tables: list[str],
) -> list[dict[str, Any]]:
    issues = []
    for table in tables:
        if not table_exists(source_conn, table) or not table_exists(target_conn, table):
            continue
        source_count = row_count(source_conn, table)
        target_count = row_count(target_conn, table)
        if source_count != target_count:
            issues.append(
                {
                    "type": "row_count_mismatch",
                    "table": table,
                    "source": source_count,
                    "target": target_count,
                }
            )
    return issues


def validate_database_integrity(
    target_conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    try:
        rows = target_conn.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.DatabaseError as exc:
        return [{"type": "integrity_check_error", "error": str(exc)}]

    messages = [str(row[0]) for row in rows]
    if messages == ["ok"]:
        return []
    return [
        {
            "type": "integrity_check_failed",
            "message_count": len(messages),
            "messages": messages[:MAX_VALIDATION_SAMPLES],
        }
    ]


def validate_foreign_keys(
    target_conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    try:
        rows = target_conn.execute("PRAGMA foreign_key_check").fetchall()
    except sqlite3.DatabaseError as exc:
        return [{"type": "foreign_key_check_error", "error": str(exc)}]

    if not rows:
        return []
    samples = [
        {
            "table": row[0],
            "rowid": row[1],
            "parent": row[2],
            "foreign_key_index": row[3],
        }
        for row in rows[:MAX_VALIDATION_SAMPLES]
    ]
    return [
        {
            "type": "foreign_key_violations",
            "violation_count": len(rows),
            "samples": samples,
        }
    ]


def _display_primary_key(key: tuple[Any, ...]) -> Any:
    if len(key) == 1:
        return key[0]
    return list(key)


def validate_source_rows_preserved(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    tables: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for table_name in tables:
        if not table_exists(source_conn, table_name) or not table_exists(target_conn, table_name):
            continue

        source_column_info = table_columns(source_conn, table_name)
        source_columns = [column.name for column in source_column_info]
        target_columns = {
            column.name for column in table_columns(target_conn, table_name)
        }
        missing_target_columns = [
            column for column in source_columns if column not in target_columns
        ]
        if missing_target_columns:
            issues.append(
                {
                    "type": "row_comparison_missing_target_columns",
                    "table": table_name,
                    "columns": missing_target_columns,
                }
            )
            continue

        primary_key_columns = [
            column.name for column in source_column_info if column.primary_key
        ]
        if not primary_key_columns:
            issues.append(
                {
                    "type": "row_comparison_missing_primary_key",
                    "table": table_name,
                }
            )
            continue

        selected_columns = ", ".join(
            quote_identifier(column) for column in source_columns
        )
        quoted_table = quote_identifier(table_name)
        source_rows = source_conn.execute(
            f"SELECT {selected_columns} FROM {quoted_table}"
        ).fetchall()
        target_rows = target_conn.execute(
            f"SELECT {selected_columns} FROM {quoted_table}"
        ).fetchall()

        def index_rows(rows):
            return {
                tuple(row[column] for column in primary_key_columns):
                tuple(row[column] for column in source_columns)
                for row in rows
            }

        source_by_key = index_rows(source_rows)
        target_by_key = index_rows(target_rows)
        source_keys = set(source_by_key)
        target_keys = set(target_by_key)
        missing_keys = sorted(source_keys - target_keys, key=repr)
        unexpected_keys = sorted(target_keys - source_keys, key=repr)
        if missing_keys or unexpected_keys:
            issues.append(
                {
                    "type": "primary_key_mismatch",
                    "table": table_name,
                    "primary_key_columns": primary_key_columns,
                    "missing_count": len(missing_keys),
                    "unexpected_count": len(unexpected_keys),
                    "missing_samples": [
                        _display_primary_key(key)
                        for key in missing_keys[:MAX_VALIDATION_SAMPLES]
                    ],
                    "unexpected_samples": [
                        _display_primary_key(key)
                        for key in unexpected_keys[:MAX_VALIDATION_SAMPLES]
                    ],
                }
            )

        mismatched_keys = sorted(
            (
                key
                for key in source_keys & target_keys
                if source_by_key[key] != target_by_key[key]
            ),
            key=repr,
        )
        if mismatched_keys:
            issues.append(
                {
                    "type": "row_data_mismatch",
                    "table": table_name,
                    "primary_key_columns": primary_key_columns,
                    "mismatch_count": len(mismatched_keys),
                    "samples": [
                        _display_primary_key(key)
                        for key in mismatched_keys[:MAX_VALIDATION_SAMPLES]
                    ],
                }
            )
    return issues


def validate_required_columns(target_conn: sqlite3.Connection, tables: list[str]) -> list[dict[str, Any]]:
    issues = []
    for table in tables:
        if not table_exists(target_conn, table):
            continue
        for col in table_columns(target_conn, table):
            if not col.not_null or col.primary_key:
                continue
            row = target_conn.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(table)} WHERE {quote_identifier(col.name)} IS NULL"
            ).fetchone()
            null_count = int(row[0] if row is not None else 0)
            if null_count:
                issues.append(
                    {
                        "type": "required_column_null",
                        "table": table,
                        "column": col.name,
                        "null_count": null_count,
                    }
                )
    return issues


def _transaction_totals(conn: sqlite3.Connection) -> dict[str, int]:
    if not table_exists(conn, "transactions"):
        return {}
    rows = conn.execute(
        """
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        GROUP BY type
        """
    ).fetchall()
    return {str(row[0]): int(row[1] or 0) for row in rows}


def validate_transaction_totals(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
) -> list[dict[str, Any]]:
    source_totals = _transaction_totals(source_conn)
    target_totals = _transaction_totals(target_conn)
    if source_totals == target_totals:
        return []
    return [
        {
            "type": "transaction_total_mismatch",
            "source": source_totals,
            "target": target_totals,
        }
    ]


def validate_signup_payment_refs(target_conn: sqlite3.Connection) -> list[dict[str, Any]]:
    issues = []
    for table in ("activity_signups", "lighting_signups"):
        if not table_exists(target_conn, table) or not table_exists(target_conn, "transactions"):
            continue
        row = target_conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {quote_identifier(table)} s
            LEFT JOIN transactions t ON t.id = s.payment_txn_id
            WHERE s.payment_txn_id IS NOT NULL
              AND t.id IS NULL
            """
        ).fetchone()
        missing_count = int(row[0] if row is not None else 0)
        if missing_count:
            issues.append(
                {
                    "type": "missing_payment_transaction",
                    "table": table,
                    "missing_count": missing_count,
                }
            )
    return issues


def run_common_validations(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    tables: list[str],
) -> list[dict[str, Any]]:
    issues = []
    issues.extend(validate_database_integrity(target_conn))
    issues.extend(validate_foreign_keys(target_conn))
    issues.extend(validate_source_rows_preserved(source_conn, target_conn, tables))
    issues.extend(validate_row_counts(source_conn, target_conn, tables))
    issues.extend(validate_required_columns(target_conn, tables))
    issues.extend(validate_transaction_totals(source_conn, target_conn))
    issues.extend(validate_signup_payment_refs(target_conn))
    return issues
