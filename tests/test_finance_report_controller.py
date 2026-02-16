import sqlite3

from app.controller.app_controller import AppController


def _seed_transactions(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category_id TEXT,
            category_name TEXT,
            amount INTEGER,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            note TEXT,
            receipt_number TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
        """
    )
    cur.executemany(
        """
        INSERT INTO transactions (
            date, type, category_id, category_name, amount,
            payer_name, handler, note, receipt_number, is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2026-02-01", "income", "01", "香油錢", 1000, "王一", "A", "", "R1", 0),
            ("2026-02-01", "income", "02", "建廟基金", 1500, "王二", "A", "", "R2", 0),
            ("2026-02-01", "expense", "E1", "香燭", 300, "廠商", "B", "", "P1", 0),
            ("2026-02-02", "income", "01", "香油錢", 800, "王三", "A", "", "R3", 0),
            ("2026-02-02", "expense", "E1", "香燭", 200, "廠商", "B", "", "P2", 1),
        ],
    )
    conn.commit()


def test_finance_summary_by_period_and_detail(tmp_path):
    db = tmp_path / "finance.db"
    conn = sqlite3.connect(db)
    _seed_transactions(conn)
    conn.close()

    controller = AppController(db_path=str(db))
    summary = controller.get_finance_summary_by_period(
        granularity="day",
        start_date="2026-02-01",
        end_date="2026-02-28",
        include_category=False,
    )
    assert len(summary) == 2
    assert summary[0]["period_key"] == "2026/02/02"
    day1 = next(r for r in summary if r["period_key"] == "2026/02/01")
    assert day1["income_total"] == 2500
    assert day1["expense_total"] == 300

    detail = controller.get_finance_detail_for_summary(
        granularity="day",
        period_key="2026/02/01",
        transaction_type="income",
    )
    assert len(detail) == 2
    assert all(row["type"] == "income" for row in detail)


def test_finance_summary_with_category_dimension_and_detail(tmp_path):
    db = tmp_path / "finance2.db"
    conn = sqlite3.connect(db)
    _seed_transactions(conn)
    conn.close()

    controller = AppController(db_path=str(db))
    summary = controller.get_finance_summary_by_period(
        granularity="day",
        start_date="2026-02-01",
        end_date="2026-02-28",
        include_category=True,
    )
    assert len(summary) == 3
    expense_row = next(r for r in summary if r["category_id"] == "E1")
    assert expense_row["income_total"] == 0
    assert expense_row["expense_total"] == 300

    detail = controller.get_finance_detail_for_summary(
        granularity="day",
        period_key="2026/02/01",
        transaction_type="income",
        category_id="01",
    )
    assert len(detail) == 2
    assert all(row["category_id"] == "01" for row in detail)


def test_finance_week_summary_uses_monday_to_sunday_range(tmp_path):
    db = tmp_path / "finance_week.db"
    conn = sqlite3.connect(db)
    _seed_transactions(conn)
    conn.close()

    controller = AppController(db_path=str(db))
    summary = controller.get_finance_summary_by_period(
        granularity="week",
        start_date="2026-02-01",
        end_date="2026-02-28",
        include_category=False,
    )
    # 2026-02-01 (Sun) -> week 2026-01-26~2026-02-01
    row = next(r for r in summary if r["period_key"] == "2026-01-26")
    assert row["period_start"] == "2026-01-26"
    assert row["period_end"] == "2026-02-01"
