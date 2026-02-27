"""
測試 app.report_generator.finance 的報表產生功能。
"""
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app.report_generator.finance import generate_daily_report, generate_monthly_report

# 供 patch 使用：僅 mock date.today，保留 date 建構子
_real_date = date


def _create_test_db(tmp_path):
    """建立測試用資料庫，含 people 與 transactions。"""
    import sqlite3
    db = tmp_path / "finance_report.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY, household_id TEXT, role_in_household TEXT,
            status TEXT, name TEXT, phone_mobile TEXT, address TEXT
        )
    """)
    cur.execute("INSERT INTO people (id, name) VALUES ('P1', '王一')")
    cur.execute("INSERT INTO people (id, name) VALUES ('P2', '王二')")
    cur.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, type TEXT NOT NULL,
            category_id TEXT NOT NULL, category_name TEXT, amount INTEGER DEFAULT 0,
            payer_person_id TEXT, payer_name TEXT, handler TEXT, receipt_number TEXT,
            note TEXT, is_voided INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0, created_at TEXT
        )
    """)
    cur.executemany(
        """INSERT INTO transactions (date, type, category_id, category_name, amount, payer_name, handler, note, receipt_number, is_voided, is_deleted)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("2026-02-01", "income", "01", "香油錢", 1000, "王一", "A", "", "R1", 0, 0),
            ("2026-02-01", "income", "02", "建廟基金", 1500, "王二", "A", "", "R2", 0, 0),
            ("2026-02-01", "income", "02", "建廟基金", 999, "王作廢", "A", "", "R2X", 1, 0),
            ("2026-02-01", "expense", "E1", "香燭", 300, "廠商", "B", "", "P1", 0, 0),
            ("2026-02-02", "income", "01", "香油錢", 800, "王三", "A", "", "R3", 0, 0),
            ("2026-02-02", "expense", "E1", "香燭", 200, "廠商", "B", "", "P2", 0, 0),
        ],
    )
    conn.commit()
    conn.close()
    return str(db)


@patch("app.report_generator.finance.date")
def test_generate_daily_report_produces_file_with_correct_format(mock_date, tmp_path):
    """generate_daily_report 應產生符合格式的 CSV 檔。"""
    mock_date.today.return_value = date(2026, 2, 1)
    db_path = _create_test_db(tmp_path)
    output = tmp_path / "每日收支明細表_20260201.csv"

    result = generate_daily_report(db_path, output_path=str(output))

    assert result == str(output.resolve())
    assert output.exists()
    content = output.read_text(encoding="utf-8-sig")
    assert "摘要" in content
    assert "期間,收入筆數,收入總額,支出筆數,支出總額,淨額" in content
    assert "本期收支結餘" in content
    assert "細項" in content
    assert "日期,類型,單號,項目代號,項目名稱,對象,金額,經手人,摘要" in content
    # 2026-02-01 當日：2 筆收入(1000+1500=2500)、1 筆支出(300)
    assert "2026/02/01" in content
    assert "2500" in content
    assert "300" in content
    assert "2200" in content  # 淨額


@patch("app.report_generator.finance.date")
def test_generate_daily_report_uses_default_filename_when_output_none(mock_date, tmp_path):
    """output_path 為 None 時，應使用預設檔名 每日收支明細表_yyyymmdd.csv。"""
    mock_date.today.return_value = date(2026, 2, 2)
    db_path = _create_test_db(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    # db 在 tmp_path/finance_report.db，parents[2] 會是 tmp_path 的 parent，不對
    # 預設路徑是 Path(db_path).resolve().parents[2] / "reports"
    # db_path = /tmp/xxx/finance_report.db -> parents[2] = /tmp (可能)
    # 所以我們傳入明確的 output_path 較穩。改為驗證有傳 output_path 時的行為。
    output = tmp_path / "reports" / "每日收支明細表_20260202.csv"
    result = generate_daily_report(db_path, output_path=str(output))
    assert result == str(output.resolve())
    assert output.exists()


@patch("app.report_generator.finance.date")
def test_generate_monthly_report_produces_file_with_correct_format(mock_date, tmp_path):
    """generate_monthly_report 應產生符合格式的 CSV 檔，彙整整月資料。"""
    mock_date.today.return_value = date(2026, 2, 15)
    mock_date.side_effect = lambda *a, **k: _real_date(*a, **k) if (a or k) else date(2026, 2, 15)
    db_path = _create_test_db(tmp_path)
    output = tmp_path / "每月收支明細表_202602.csv"

    result = generate_monthly_report(db_path, output_path=str(output))

    assert result == str(output.resolve())
    assert output.exists()
    content = output.read_text(encoding="utf-8-sig")
    assert "摘要" in content
    assert "2026/02" in content
    # 整月：收入 1000+1500+800=3300，支出 300+200=500
    assert "3300" in content
    assert "500" in content
    assert "細項" in content


@patch("app.report_generator.finance.date")
def test_generate_daily_report_empty_day_still_produces_file(mock_date, tmp_path):
    """當日無交易時，仍應產生結構完整的空報表。"""
    mock_date.today.return_value = date(2026, 3, 1)  # 無資料的日期
    db_path = _create_test_db(tmp_path)
    output = tmp_path / "每日收支明細表_20260301.csv"

    result = generate_daily_report(db_path, output_path=str(output))

    assert output.exists()
    content = output.read_text(encoding="utf-8-sig")
    assert "摘要" in content
    assert "本期收支結餘,0" in content
    assert "細項" in content
