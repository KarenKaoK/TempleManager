"""
信徒表格報表產生器。
- monthly：每月信徒清單（僅 ACTIVE，含戶長與戶員）
"""
from __future__ import annotations

import sqlite3
from csv import writer
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_ymd_to_date(text: Optional[str]) -> Optional[date]:
    s = (text or "").strip()
    if not s:
        return None
    s = s.replace("-", "/")
    try:
        return datetime.strptime(s, "%Y/%m/%d").date()
    except Exception:
        return None


def _calc_age_by_birthday(birthday_text: Optional[str], today: date) -> Optional[int]:
    birthday = _parse_ymd_to_date(birthday_text)
    if not birthday:
        return None
    age = today.year - birthday.year + 1
    return max(0, age)


def _apply_effective_age(person: dict, today: date) -> dict:
    data = dict(person)
    auto_age = _calc_age_by_birthday(data.get("birthday_ad"), today)
    if auto_age is None:
        return data
    try:
        offset = int(data.get("age_offset") or 0)
    except Exception:
        offset = 0
    data["age"] = max(0, auto_age + offset)
    return data


def _fmt_date(text: str) -> str:
    """將 YYYY-MM-DD 或 YYYY/MM/DD 轉為 YYYY/MM/DD 顯示。"""
    s = (text or "").strip()
    if not s:
        return ""
    return s.replace("-", "/")


def _get_all_active_people(conn: sqlite3.Connection) -> List[dict]:
    """
    取得所有 ACTIVE 信眾，依 household_id、戶長優先、joined_at 排序。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id, household_id, role_in_household, status,
            name, gender, birthday_ad, birthday_lunar, lunar_is_leap,
            birth_time, age, age_offset, zodiac,
            phone_home, phone_mobile, address, zip_code,
            note, joined_at
        FROM people
        WHERE status = 'ACTIVE'
        ORDER BY
            household_id ASC,
            CASE role_in_household WHEN 'HEAD' THEN 0 ELSE 1 END,
            COALESCE(joined_at, '') ASC,
            id ASC
        """
    )
    return [dict(row) for row in cur.fetchall()]


def generate_monthly_believer_report(
    db_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    產生「每月」信徒表格報表（CSV）。
    僅包含 status='ACTIVE' 的信眾，含戶長與戶員。

    Args:
        db_path: 資料庫路徑
        output_path: 輸出路徑。None 則用 reports/每月信眾資料表_yyyymm.csv

    Returns:
        輸出檔案的絕對路徑
    """
    today = date.today()
    if output_path is None:
        base = Path(db_path).resolve().parents[2] / "reports"
        output_path = str(base / f"每月信眾資料表_{today:%Y%m}.csv")
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect(db_path)
    try:
        rows = _get_all_active_people(conn)
        people = [_apply_effective_age(p, today) for p in rows]
    finally:
        conn.close()

    headers = [
        "類型", "姓名", "性別", "國曆生日", "農曆生日", "時辰", "生肖", "年齡",
        "聯絡電話", "手機號碼", "郵遞區號", "聯絡地址", "備註",
    ]

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = writer(f)
        w.writerow(headers)
        for p in people:
            role_text = "戶長" if p.get("role_in_household") == "HEAD" else "戶員"
            lunar = _fmt_date(p.get("birthday_lunar") or "")
            if int(p.get("lunar_is_leap") or 0) == 1 and lunar:
                lunar = f"{lunar}(閏)"
            age_val = p.get("age")
            age_str = "" if age_val is None else str(age_val)
            w.writerow([
                role_text,
                str(p.get("name") or ""),
                str(p.get("gender") or ""),
                _fmt_date(p.get("birthday_ad") or ""),
                lunar,
                str(p.get("birth_time") or ""),
                str(p.get("zodiac") or ""),
                age_str,
                str(p.get("phone_home") or ""),
                str(p.get("phone_mobile") or ""),
                str(p.get("zip_code") or ""),
                str(p.get("address") or ""),
                str(p.get("note") or ""),
            ])

    return str(out)
