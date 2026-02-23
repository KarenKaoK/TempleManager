"""
活動報名報表產生器。
- 每日活動報表：活動期間內當日的報名狀況，含報名摘要、報名人明細、各項品數量（拆解到細品項）
"""
from __future__ import annotations

import json
import re
import sqlite3
from csv import writer
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_plan_items(items_raw: Any) -> List[Dict[str, Any]]:
    """解析 activity_plans.items：支援 JSON 陣列或純文字。"""
    text = str(items_raw or "").strip()
    if not text:
        return []

    if text.startswith("["):
        try:
            arr = json.loads(text)
            result: List[Dict[str, Any]] = []
            for x in arr or []:
                name = str((x or {}).get("name", "")).strip()
                if not name:
                    continue
                try:
                    qty = int((x or {}).get("qty", 1))
                except Exception:
                    qty = 1
                result.append({"name": name, "qty": max(1, qty)})
            return result
        except Exception:
            pass

    parts = re.split(r"[\/、,\n]+", text)
    result = []
    for p in parts:
        token = p.strip()
        if not token:
            continue
        m = re.match(r"^(.*?)(?:[xX＊*×]\s*(\d+))?$", token)
        if not m:
            continue
        name = (m.group(1) or "").strip()
        if not name:
            continue
        qty = int(m.group(2) or 1)
        result.append({"name": name, "qty": max(1, qty)})
    return result


def _parse_plan_items_text(text: str) -> List[Tuple[str, int]]:
    """將 plan items 轉成 [(品項名稱, 每方案數量)]。"""
    items: List[Tuple[str, int]] = []
    for token in re.split(r"[、,\n/]+", str(text or "")):
        t = token.strip()
        if not t:
            continue
        m = re.match(r"^(.*?)(?:[xX×*＊]\s*(\d+))?$", t)
        if not m:
            continue
        name = (m.group(1) or "").strip()
        if not name:
            continue
        qty = int(m.group(2) or 1)
        items.append((name, max(1, qty)))
    return items


def _plan_qty_map_from_summary(summary: str) -> Dict[str, int]:
    """解析 plan_summary 字串（如 雙虎祝壽×2、隨喜500元）得到 {方案名: 總數量}。"""
    out: Dict[str, int] = {}
    for token in re.split(r"[、,\n]+", str(summary or "")):
        t = token.strip()
        if not t:
            continue
        m = re.match(r"^(.*?)[xX×*＊]\s*(\d+)$", t)
        if not m:
            continue
        name = (m.group(1) or "").strip()
        qty = int(m.group(2) or 0)
        if name and qty > 0:
            out[name] = out.get(name, 0) + qty
    return out


def _build_item_stats_rows(
    plans: List[dict],
    signups: List[dict],
) -> List[Tuple[str, int]]:
    """
    從方案與報名資料彙整各細品項總數量。
    參考 ActivityDetailPanel._build_item_stats_rows。
    """
    plan_item_map: Dict[str, List[Tuple[str, int]]] = {}
    for p in plans or []:
        name = str(p.get("name") or "").strip()
        items_raw = p.get("items") or p.get("description") or ""
        parsed = _parse_plan_items(items_raw)
        plan_item_map[name] = [(x.get("name", ""), int(x.get("qty") or 1)) for x in parsed if x.get("name")]

    agg: Dict[str, int] = {}
    for r in signups or []:
        plan_qty_map = _plan_qty_map_from_summary(str((r or {}).get("plan_summary", "")))
        for plan_name, plan_qty in plan_qty_map.items():
            for item_name, item_qty in plan_item_map.get(plan_name, []):
                if item_name:
                    agg[item_name] = agg.get(item_name, 0) + plan_qty * item_qty

    return sorted(agg.items(), key=lambda x: x[0])


def _get_activities_in_range(conn: sqlite3.Connection, report_date: date) -> List[dict]:
    """取得 report_date 當天在活動期間內的活動。"""
    today_str = report_date.strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, activity_start_date, activity_end_date
        FROM activities
        WHERE COALESCE(status, 1) != -1
          AND date(replace(activity_start_date, '/', '-')) <= ?
          AND date(replace(activity_end_date, '/', '-')) >= ?
        ORDER BY activity_start_date ASC, id ASC
        """,
        (today_str, today_str),
    )
    return [dict(row) for row in cur.fetchall()]


def _get_activity_signups(conn: sqlite3.Connection, activity_id: str) -> List[dict]:
    """取得活動報名清單，與 AppController.get_activity_signups 相同邏輯。"""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            s.id AS signup_id,
            p.name AS person_name,
            p.phone_mobile AS person_phone,
            s.total_amount,
            COALESCE(s.is_paid, 0) AS is_paid,
            s.payment_receipt_number,
            GROUP_CONCAT(
                CASE
                    WHEN ap.price_type = 'FREE'
                        THEN ap.name || COALESCE(CAST(sp.line_total AS TEXT), '0') || '元'
                    ELSE ap.name || '×' || COALESCE(CAST(sp.qty AS TEXT), '0')
                END,
                '、'
            ) AS plan_summary
        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        JOIN activity_signup_plans sp ON sp.signup_id = s.id
        JOIN activity_plans ap ON ap.id = sp.plan_id
        WHERE s.activity_id = ?
        GROUP BY s.id
        ORDER BY
            datetime(replace(COALESCE(s.signup_time, s.created_at), '/', '-')) ASC,
            s.id ASC
        """,
        (activity_id,),
    )
    col_names = [d[0] for d in cur.description]
    return [dict(zip(col_names, r)) for r in cur.fetchall()]


def _get_activity_plans(conn: sqlite3.Connection, activity_id: str) -> List[dict]:
    """取得活動方案。"""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(activity_plans)")
    cols = [c[1] for c in cur.fetchall()]
    item_col = "items" if "items" in cols else "description"
    cur.execute(
        f"""
        SELECT id, name, {item_col} AS items, sort_order
        FROM activity_plans
        WHERE activity_id = ? AND COALESCE(is_active, 1) = 1
        ORDER BY sort_order ASC, created_at ASC
        """,
        (activity_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def _write_activity_section(
    w: writer,
    activity: dict,
    signups: List[dict],
    plans: List[dict],
) -> None:
    """寫入單一活動的區塊。"""
    name = str(activity.get("name") or "").strip() or "（未命名活動）"
    start_s = str(activity.get("activity_start_date") or "").strip()
    end_s = str(activity.get("activity_end_date") or "").strip()
    date_range = f"{start_s} ~ {end_s}" if (start_s and end_s) else (start_s or end_s or "")

    w.writerow([f"{name}（{date_range}）"])
    w.writerow([])

    # 報名摘要
    total_count = len(signups)
    paid_count = sum(1 for r in signups if int(r.get("is_paid") or 0) == 1)
    unpaid_count = total_count - paid_count
    total_amount = sum(int(r.get("total_amount") or 0) for r in signups)

    w.writerow(["【報名摘要】"])
    w.writerow(["總報名人數", "已繳費人數", "未繳費人數", "報名總金額"])
    w.writerow([str(total_count), str(paid_count), str(unpaid_count), str(total_amount)])
    w.writerow([])

    # 報名人明細
    w.writerow(["【報名人明細】"])
    w.writerow(["繳費", "姓名", "電話", "方案", "金額"])
    for r in signups:
        paid_mark = "✓" if int(r.get("is_paid") or 0) == 1 else ""
        w.writerow([
            paid_mark,
            str(r.get("person_name") or ""),
            str(r.get("person_phone") or ""),
            str(r.get("plan_summary") or ""),
            str(int(r.get("total_amount") or 0)),
        ])
    w.writerow([])

    # 各項品數量（拆解到細品項）
    item_stats = _build_item_stats_rows(plans, signups)
    w.writerow(["【各項品數量】"])
    w.writerow(["品項", "總數量"])
    for item_name, qty in item_stats:
        w.writerow([item_name, str(qty)])
    w.writerow([])


def generate_daily_activity_report(
    db_path: str,
    report_date: Optional[date] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    產生「每日」活動報表（CSV）。
    僅包含 report_date 當天在活動期間內的活動；若無活動則不產檔、拋出 ValueError。

    Args:
        db_path: 資料庫路徑
        report_date: 報表日期，None 則用今日
        output_path: 輸出路徑。None 則用 reports/每日活動報表_yyyymmdd.csv

    Returns:
        輸出檔案的絕對路徑
    """
    today = report_date or date.today()
    today_str = today.strftime("%Y-%m-%d")

    if output_path is None:
        base = Path(db_path).resolve().parents[2] / "reports"
        output_path = str(base / f"每日活動報表_{today:%Y%m%d}.csv")
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect(db_path)
    try:
        activities = _get_activities_in_range(conn, today)
        if not activities:
            raise ValueError(f"當日 {today_str} 無進行中活動，不產生活動報表")

        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = writer(f)
            for act in activities:
                aid = str(act.get("id") or "")
                signups = _get_activity_signups(conn, aid) if aid else []
                plans = _get_activity_plans(conn, aid) if aid else []
                _write_activity_section(w, act, signups, plans)
    finally:
        conn.close()

    return str(out)


def generate_activity_signup_report(
    db_path: str,
    activity_id: str,
    output_path: Optional[str] = None,
) -> str:
    """
    產生指定單一活動的報名名單報表（CSV）。
    供手動匯出使用；排程請用 generate_daily_activity_report。
    """
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, activity_start_date, activity_end_date FROM activities WHERE id = ?",
            (activity_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"找不到活動：{activity_id}")
        activity = dict(row)
        signups = _get_activity_signups(conn, activity_id)
        plans = _get_activity_plans(conn, activity_id)
    finally:
        conn.close()

    if output_path is None:
        base = Path(db_path).resolve().parents[2] / "reports"
        output_path = str(base / f"活動報表_{activity_id[:12]}.csv")
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = writer(f)
        _write_activity_section(w, activity, signups, plans)

    return str(out)
