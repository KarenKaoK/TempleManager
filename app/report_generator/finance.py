"""
收支明細報表產生器。
- daily：每日收支明細表
- monthly：每月收支明細表

參考 FinanceReportDialog.export_csv 的格式與 AppController 查詢邏輯。
"""
from __future__ import annotations

import sqlite3
from csv import writer
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_transactions(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    transaction_type: Optional[str] = None,
) -> List[dict]:
    """取得指定區間的收支明細。"""
    query = """
        SELECT t.*, p.phone_mobile, p.address
        FROM transactions t
        LEFT JOIN people p ON t.payer_person_id = p.id
        WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
          AND t.date >= ?
          AND t.date <= ?
    """
    params: List[str] = [start_date, end_date]
    if transaction_type:
        query += " AND t.type = ?"
        params.append(transaction_type)
    query += " ORDER BY (CASE WHEN t.type = 'income' THEN 0 ELSE 1 END), t.date ASC, t.receipt_number ASC"
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    return [dict(row) for row in cur.fetchall()]


def _get_finance_summary(
    conn: sqlite3.Connection,
    granularity: str,
    start_date: str,
    end_date: str,
) -> List[dict]:
    """取得指定區間的收支摘要（依 granularity 彙整）。"""
    if granularity == "day":
        period_expr = "strftime('%Y/%m/%d', t.date)"
    elif granularity == "month":
        period_expr = "strftime('%Y/%m', t.date)"
    else:
        raise ValueError("granularity must be 'day' or 'month'")

    query = f"""
        SELECT
            {period_expr} AS period_key,
            MIN(t.date) AS period_start,
            MAX(t.date) AS period_end,
            COALESCE(SUM(CASE WHEN t.type = 'income' THEN 1 ELSE 0 END), 0) AS income_count,
            COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income_total,
            COALESCE(SUM(CASE WHEN t.type = 'expense' THEN 1 ELSE 0 END), 0) AS expense_count,
            COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense_total
        FROM transactions t
        WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
          AND t.date >= ?
          AND t.date <= ?
        GROUP BY period_key
        ORDER BY period_key ASC
    """
    cur = conn.cursor()
    cur.execute(query, (start_date, end_date))
    return [dict(row) for row in cur.fetchall()]


def _safe_date(value) -> datetime:
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d")
    except Exception:
        return datetime.min


def _write_finance_csv(
    output_path: Path,
    summary_rows: List[dict],
    detail_rows: List[dict],
) -> None:
    """寫入與 FinanceReportDialog.export_csv 相同的 CSV 格式。"""
    summary_headers = ["期間", "收入筆數", "收入總額", "支出筆數", "支出總額", "淨額"]
    detail_headers = ["日期", "類型", "單號", "項目代號", "項目名稱", "對象", "金額", "經手人", "摘要"]

    total_net = 0
    for row in summary_rows:
        income_total = int(row.get("income_total") or 0)
        expense_total = int(row.get("expense_total") or 0)
        total_net += income_total - expense_total

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        w = writer(f)
        w.writerow(["摘要"])
        w.writerow(summary_headers)
        for row in summary_rows:
            income_total = int(row.get("income_total") or 0)
            expense_total = int(row.get("expense_total") or 0)
            net = income_total - expense_total
            period_key = str(row.get("period_key") or "").replace("-", "/")
            w.writerow([
                period_key,
                str(row.get("income_count") or 0),
                str(income_total),
                str(row.get("expense_count") or 0),
                str(expense_total),
                str(net),
            ])
        w.writerow([])
        w.writerow(["本期收支結餘", total_net])
        w.writerow([])
        w.writerow(["細項"])
        w.writerow(detail_headers)
        for row_data in detail_rows:
            tx_type = "收入" if row_data.get("type") == "income" else "支出"
            w.writerow([
                str(row_data.get("date") or "").replace("-", "/"),
                tx_type,
                str(row_data.get("receipt_number") or ""),
                str(row_data.get("category_id") or ""),
                str(row_data.get("category_name") or ""),
                str(row_data.get("payer_name") or ""),
                str(row_data.get("amount") or 0),
                str(row_data.get("handler") or ""),
                str(row_data.get("note") or ""),
            ])


def generate_daily_report(db_path: str, output_path: Optional[str] = None) -> str:
    """
    產生「每日」收支明細報表（CSV）。

    Args:
        db_path: 資料庫路徑
        output_path: 輸出路徑。若為 None，則使用 reports/每日收支明細表_yyyymmdd.csv
                    （以今日為基準）

    Returns:
        輸出檔案的絕對路徑
    """
    today = date.today()
    start_str = end_str = today.strftime("%Y-%m-%d")

    if output_path is None:
        # db_path 通常為 .../app/database/temple.db，parents[2] = 專案根目錄
        base = Path(db_path).resolve().parents[2] / "reports"
        output_path = str(base / f"每日收支明細表_{today:%Y%m%d}.csv")
    out = Path(output_path).resolve()

    conn = _connect(db_path)
    try:
        summary = _get_finance_summary(conn, "day", start_str, end_str)
        details = _get_transactions(conn, start_str, end_str, transaction_type=None)
        details.sort(
            key=lambda d: (
                0 if d.get("type") == "income" else 1,
                _safe_date(d.get("date")),
                str(d.get("receipt_number") or ""),
            )
        )
        _write_finance_csv(out, summary, details)
    finally:
        conn.close()

    return str(out)


def generate_monthly_report(db_path: str, output_path: Optional[str] = None) -> str:
    """
    產生「每月」收支明細報表（CSV）。

    Args:
        db_path: 資料庫路徑
        output_path: 輸出路徑。若為 None，則使用 reports/每月收支明細表_yyyymm.csv
                    （以當月為基準）

    Returns:
        輸出檔案的絕對路徑
    """
    today = date.today()
    first_day = today.replace(day=1)
    next_month = date(today.year + (today.month // 12), (today.month % 12) + 1, 1)
    last_day = next_month - timedelta(days=1)
    start_str = first_day.strftime("%Y-%m-%d")
    end_str = last_day.strftime("%Y-%m-%d")

    if output_path is None:
        base = Path(db_path).resolve().parents[2] / "reports"
        output_path = str(base / f"每月收支明細表_{today:%Y%m}.csv")
    out = Path(output_path).resolve()

    conn = _connect(db_path)
    try:
        summary = _get_finance_summary(conn, "month", start_str, end_str)
        details = _get_transactions(conn, start_str, end_str, transaction_type=None)
        details.sort(
            key=lambda d: (
                0 if d.get("type") == "income" else 1,
                _safe_date(d.get("date")),
                str(d.get("receipt_number") or ""),
            )
        )
        _write_finance_csv(out, summary, details)
    finally:
        conn.close()

    return str(out)
