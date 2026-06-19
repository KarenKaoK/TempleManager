from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    not_null: bool
    default_value: str | None
    primary_key: bool


@dataclass(frozen=True)
class TableInventory:
    name: str
    columns: list[ColumnInfo]
    row_count: int


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def connect_readonly(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"DB not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def table_columns(conn: sqlite3.Connection, table_name: str) -> list[ColumnInfo]:
    rows = conn.execute(f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
    return [
        ColumnInfo(
            name=str(row["name"]),
            type=str(row["type"] or ""),
            not_null=bool(row["notnull"]),
            default_value=row["dflt_value"],
            primary_key=bool(row["pk"]),
        )
        for row in rows
    ]


def table_row_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {quote_identifier(table_name)}").fetchone()
    return int(row["count"] if row is not None else 0)


def inventory_database(db_path: str) -> dict[str, TableInventory]:
    conn = connect_readonly(db_path)
    try:
        return {
            table: TableInventory(
                name=table,
                columns=table_columns(conn, table),
                row_count=table_row_count(conn, table),
            )
            for table in list_user_tables(conn)
        }
    finally:
        conn.close()


def diff_inventories(
    source: dict[str, TableInventory],
    target: dict[str, TableInventory],
) -> dict[str, Any]:
    source_tables = set(source)
    target_tables = set(target)
    common_tables = sorted(source_tables & target_tables)
    column_diffs: dict[str, dict[str, list[str]]] = {}

    for table in common_tables:
        source_cols = {col.name for col in source[table].columns}
        target_cols = {col.name for col in target[table].columns}
        added = sorted(target_cols - source_cols)
        removed = sorted(source_cols - target_cols)
        if added or removed:
            column_diffs[table] = {
                "added_in_target": added,
                "missing_in_target": removed,
            }

    return {
        "tables_only_in_source": sorted(source_tables - target_tables),
        "tables_only_in_target": sorted(target_tables - source_tables),
        "column_diffs": column_diffs,
        "row_counts": {
            table: {"source": source[table].row_count, "target": target[table].row_count}
            for table in common_tables
        },
    }


def inventory_to_dict(inventory: dict[str, TableInventory]) -> dict[str, Any]:
    return {
        table: {
            "row_count": info.row_count,
            "columns": [col.__dict__ for col in info.columns],
        }
        for table, info in inventory.items()
    }
