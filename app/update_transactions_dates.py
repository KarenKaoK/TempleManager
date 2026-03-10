import argparse
import sqlite3
from pathlib import Path


def parse_args():
    here = Path(__file__).resolve().parent
    default_db = here / "database" / "temple.db"

    parser = argparse.ArgumentParser(
        description="Update all transactions.date to 2026-02-01, then randomly set some to 2026-01-09."
    )
    parser.add_argument(
        "--db",
        default=str(default_db),
        help="SQLite DB path (default: app/database/temple.db)",
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.10,
        help="Random ratio to set as 2026-01-09 (0.0 ~ 1.0, default: 0.10)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ratio = max(0.0, min(1.0, float(args.ratio)))
    db_path = Path(args.db)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM transactions")
        total = int(cur.fetchone()[0] or 0)

        # 1) 全部先改成 2026-02-01
        cur.execute("UPDATE transactions SET date = '2026-02-01'")

        # 2) 隨機挑一部分改成 2026-01-09
        pick_count = int(total * ratio)
        if total > 0 and ratio > 0 and pick_count == 0:
            pick_count = 1

        changed_to_jan = 0
        if pick_count > 0:
            cur.execute(
                """
                UPDATE transactions
                SET date = '2026-01-09'
                WHERE id IN (
                    SELECT id
                    FROM transactions
                    ORDER BY RANDOM()
                    LIMIT ?
                )
                """,
                (pick_count,),
            )
            changed_to_jan = int(cur.rowcount or 0)

        conn.commit()
        print(f"DB: {db_path}")
        print(f"Total rows: {total}")
        print("Set to 2026-02-01: all rows")
        print(f"Randomly set to 2026-01-09: {changed_to_jan} rows (ratio={ratio:.2f})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
