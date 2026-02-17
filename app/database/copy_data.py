import argparse
import sqlite3


DEFAULT_TABLES = [
    "people",
    "member_identity",
    "income_items",
    "expense_items",
    "activities",
    "activity_plans",
    "activity_signups",
    "activity_signup_plans",
    "transactions",
]


def table_exists(conn, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def columns_of(conn, table_name: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return [r[1] for r in cur.fetchall()]


def copy_table(source_conn, target_conn, table_name: str):
    if not table_exists(source_conn, table_name):
        print(f"⚠️ source 缺少資料表：{table_name}，略過")
        return
    if not table_exists(target_conn, table_name):
        print(f"⚠️ target 缺少資料表：{table_name}，略過")
        return
    src_cols = set(columns_of(source_conn, table_name))
    tgt_cols = columns_of(target_conn, table_name)
    common_cols = [c for c in tgt_cols if c in src_cols]
    if not common_cols:
        print(f"⚠️ {table_name} 無共同欄位，略過")
        return

    placeholders = ", ".join(["?"] * len(common_cols))
    cols_sql = ", ".join(common_cols)
    src_cur = source_conn.cursor()
    src_cur.execute(f"SELECT {cols_sql} FROM {table_name}")
    rows = src_cur.fetchall()

    tgt_cur = target_conn.cursor()
    tgt_cur.execute(f"DELETE FROM {table_name}")
    tgt_cur.executemany(f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})", rows)
    target_conn.commit()
    print(f"✅ {table_name}: copied {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="Copy data from old sqlite db to new sqlite db")
    parser.add_argument("--source", required=True, help="old db path")
    parser.add_argument("--target", required=True, help="new db path")
    parser.add_argument("--include-users", action="store_true", help="copy users table as well")
    args = parser.parse_args()

    tables = list(DEFAULT_TABLES)
    if args.include_users:
        tables.insert(0, "users")

    src = sqlite3.connect(args.source)
    tgt = sqlite3.connect(args.target)
    try:
        for t in tables:
            copy_table(src, tgt, t)
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    main()
