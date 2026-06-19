from __future__ import annotations

import sqlite3
from typing import Any

from migrations.schema_inventory import quote_identifier, table_columns


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
    issues.extend(validate_row_counts(source_conn, target_conn, tables))
    issues.extend(validate_required_columns(target_conn, tables))
    issues.extend(validate_transaction_totals(source_conn, target_conn))
    issues.extend(validate_signup_payment_refs(target_conn))
    return issues
