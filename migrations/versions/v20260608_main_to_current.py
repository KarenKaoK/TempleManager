from __future__ import annotations

import sqlite3
from typing import Any

from migrations.engine import MigrationSpec
from migrations.schema_inventory import quote_identifier, table_columns


EXPECTED_ADDED_COLUMN_DEFAULTS: dict[str, dict[str, Any]] = {
    "activity_signups": {
        "prayer": None,
        "receipt_method": "ELECTRONIC",
        "paper_receipt_number": None,
    },
    "lighting_signups": {
        "receipt_method": "ELECTRONIC",
        "paper_receipt_number": None,
    },
    "transactions": {
        "payment_method": "cash",
        "transfer_last5": None,
        "receipt_method": "ELECTRONIC",
        "paper_receipt_number": None,
    },
}


def validate_added_column_defaults(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    tables: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for table_name, defaults in EXPECTED_ADDED_COLUMN_DEFAULTS.items():
        if table_name not in tables:
            continue
        source_columns = {
            column.name for column in table_columns(source_conn, table_name)
        }
        for column_name, expected_value in defaults.items():
            if column_name in source_columns:
                continue
            quoted_table = quote_identifier(table_name)
            quoted_column = quote_identifier(column_name)
            if expected_value is None:
                row = target_conn.execute(
                    f"SELECT COUNT(*) FROM {quoted_table} "
                    f"WHERE {quoted_column} IS NOT NULL"
                ).fetchone()
            else:
                row = target_conn.execute(
                    f"SELECT COUNT(*) FROM {quoted_table} "
                    f"WHERE {quoted_column} IS NULL OR {quoted_column} != ?",
                    (expected_value,),
                ).fetchone()
            mismatch_count = int(row[0] if row is not None else 0)
            if mismatch_count:
                issues.append(
                    {
                        "type": "unexpected_added_column_default",
                        "table": table_name,
                        "column": column_name,
                        "expected": expected_value,
                        "mismatch_count": mismatch_count,
                    }
                )
    return issues


MIGRATION = MigrationSpec(
    name="v20260608_main_to_current",
    column_defaults=EXPECTED_ADDED_COLUMN_DEFAULTS,
    validators=[validate_added_column_defaults],
    allowed_target_only_columns={
        table_name: set(defaults)
        for table_name, defaults in EXPECTED_ADDED_COLUMN_DEFAULTS.items()
    },
)
