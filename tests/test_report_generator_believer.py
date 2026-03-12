"""
測試 app.report_generator.believer 的每月信眾資料表產生功能。
"""
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app.report_generator.believer import generate_monthly_believer_report


def _create_test_db(tmp_path):
    """建立含戶長與戶員的測試 DB。"""
    import sqlite3
    db = tmp_path / "believer_report.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY, household_id TEXT NOT NULL, role_in_household TEXT,
            status TEXT, name TEXT, gender TEXT, birthday_ad TEXT, birthday_lunar TEXT,
            lunar_is_leap INTEGER DEFAULT 0, birth_time TEXT, age INTEGER, age_offset INTEGER,
            zodiac TEXT, phone_home TEXT, phone_mobile TEXT, address TEXT, zip_code TEXT,
            note TEXT, joined_at TEXT
        )
    """)
    cur.executemany(
        """INSERT INTO people (
            id, household_id, role_in_household, status, name, gender, birthday_ad,
            birthday_lunar, birth_time, zodiac, phone_home, phone_mobile, address, zip_code, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("P1", "H1", "HEAD", "ACTIVE", "王大明", "男", "1960-01-15", "己亥年臘月", "", "鼠", "0212345678", "0912345678", "台北市信義區", "110", "戶長"),
            ("P2", "H1", "MEMBER", "ACTIVE", "王小華", "女", "1990-05-20", "庚午年四月", "", "馬", "", "0923456789", "台北市信義區", "110", ""),
            ("P3", "H2", "HEAD", "ACTIVE", "李四", "男", "1975-08-01", "", "午時", "兔", "0312345678", "0934567890", "新北市板橋區", "220", ""),
        ],
    )
    conn.commit()
    conn.close()
    return str(db)


@patch("app.report_generator.believer.date")
def test_generate_monthly_believer_report_produces_file(mock_date, tmp_path):
    """應產生含戶長與戶員的 CSV 檔。"""
    mock_date.today.return_value = date(2026, 2, 15)
    db_path = _create_test_db(tmp_path)
    output = tmp_path / "每月信眾資料表_202602.csv"

    result = generate_monthly_believer_report(db_path, output_path=str(output))

    assert result == str(output.resolve())
    assert output.exists()
    content = output.read_text(encoding="utf-8-sig")
    assert "類型" in content
    assert "姓名" in content
    assert "郵遞區號" in content
    assert "戶長" in content
    assert "戶員" in content
    assert "王大明" in content
    assert "王小華" in content
    assert "李四" in content
    assert "110" in content
    assert "220" in content
    assert "67" in content
    assert "37" in content


@patch("app.report_generator.believer.date")
def test_generate_monthly_believer_report_excludes_inactive(mock_date, tmp_path):
    """僅包含 ACTIVE 信眾，排除 INACTIVE。"""
    import sqlite3
    mock_date.today.return_value = date(2026, 2, 1)
    db = tmp_path / "believer_inactive.db"
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE people (
            id TEXT, household_id TEXT, role_in_household TEXT, status TEXT,
            name TEXT, gender TEXT, birthday_ad TEXT, birthday_lunar TEXT, lunar_is_leap INTEGER,
            birth_time TEXT, age INTEGER, age_offset INTEGER, zodiac TEXT,
            phone_home TEXT, phone_mobile TEXT, address TEXT, zip_code TEXT, note TEXT, joined_at TEXT
        )
    """)
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES ('P1', 'H1', 'HEAD', 'INACTIVE', '停用戶長')"
    )
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES ('P2', 'H1', 'MEMBER', 'ACTIVE', '活躍戶員')"
    )
    conn.commit()
    conn.close()

    output = tmp_path / "believer_test.csv"
    result = generate_monthly_believer_report(str(db), output_path=str(output))

    content = Path(result).read_text(encoding="utf-8-sig")
    assert "活躍戶員" in content
    assert "停用戶長" not in content
