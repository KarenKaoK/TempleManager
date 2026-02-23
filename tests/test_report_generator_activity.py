"""
測試 app.report_generator.activity 的每日活動報表產生功能。
"""
from datetime import date
from pathlib import Path
import pytest

from app.report_generator.activity import generate_daily_activity_report


def _create_test_db_with_activity(tmp_path):
    """建立含活動、方案、報名的測試 DB。"""
    import sqlite3
    db = tmp_path / "activity_report.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY, name TEXT, phone_mobile TEXT, household_id TEXT,
            role_in_household TEXT, status TEXT
        )
    """)
    cur.execute("INSERT INTO people (id, name, phone_mobile) VALUES ('P1', '王大明', '0912345678')")

    cur.execute("""
        CREATE TABLE activities (
            id TEXT PRIMARY KEY, name TEXT, activity_start_date TEXT, activity_end_date TEXT,
            note TEXT, status INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
        )
    """)
    cur.execute(
        "INSERT INTO activities (id, name, activity_start_date, activity_end_date, status) VALUES (?, ?, ?, ?, 1)",
        ("ACT001", "虎爺聖誕", "2026-02-20", "2026-02-25"),
    )

    cur.execute("""
        CREATE TABLE activity_plans (
            id TEXT PRIMARY KEY, activity_id TEXT, name TEXT, items TEXT,
            price_type TEXT, fixed_price INTEGER, sort_order INTEGER, is_active INTEGER DEFAULT 1,
            created_at TEXT, updated_at TEXT
        )
    """)
    cur.execute(
        "INSERT INTO activity_plans (id, activity_id, name, items, price_type, fixed_price, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("PL1", "ACT001", "雙虎祝壽", '[{"name":"疏文","qty":1},{"name":"供品","qty":2}]', "FIXED", 300, 0),
    )

    cur.execute("""
        CREATE TABLE activity_signups (
            id TEXT PRIMARY KEY, activity_id TEXT, person_id TEXT, signup_time TEXT,
            note TEXT, total_amount INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT,
            is_paid INTEGER DEFAULT 0, paid_at TEXT, payment_receipt_number TEXT
        )
    """)
    cur.execute(
        "INSERT INTO activity_signups (id, activity_id, person_id, signup_time, total_amount) VALUES (?, ?, ?, ?, ?)",
        ("S1", "ACT001", "P1", "2026-02-21 10:00:00", 300),
    )

    cur.execute("""
        CREATE TABLE activity_signup_plans (
            id TEXT PRIMARY KEY, signup_id TEXT, plan_id TEXT, qty INTEGER,
            unit_price_snapshot INTEGER, line_total INTEGER
        )
    """)
    cur.execute(
        "INSERT INTO activity_signup_plans (id, signup_id, plan_id, qty, unit_price_snapshot, line_total) VALUES (?, ?, ?, ?, ?, ?)",
        ("SP1", "S1", "PL1", 2, 300, 600),
    )

    conn.commit()
    conn.close()
    return str(db)


def test_generate_daily_activity_report_produces_file(tmp_path):
    """活動期間內應產生報表檔。"""
    db_path = _create_test_db_with_activity(tmp_path)
    output = tmp_path / "每日活動報表_20260222.csv"

    result = generate_daily_activity_report(db_path, report_date=date(2026, 2, 22), output_path=str(output))

    assert result == str(output.resolve())
    assert output.exists()
    content = output.read_text(encoding="utf-8-sig")
    assert "=== 虎爺聖誕" in content
    assert "【報名摘要】" in content
    assert "【報名人明細】" in content
    assert "【各項品數量】" in content
    assert "王大明" in content
    assert "疏文" in content or "供品" in content


def test_generate_daily_activity_report_no_activities_raises(tmp_path):
    """當日無進行中活動時應拋出 ValueError。"""
    import sqlite3
    db = tmp_path / "empty.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE activities (id TEXT, name TEXT, activity_start_date TEXT, activity_end_date TEXT, status INTEGER)")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="無進行中活動"):
        generate_daily_activity_report(str(db), report_date=date(2030, 1, 1))
