# tests/test_activity_controller.py
import sqlite3
import pytest
from datetime import datetime

from app.controller.app_controller import AppController


@pytest.fixture
def controller_with_activity_db(tmp_path, monkeypatch):
    """
    建立只包含 activities table 的測試 DB，回傳 AppController。
    並把 app_controller.datetime 固定在同一天，讓 activity_id 可預測。
    """
    db_path = tmp_path / "test_activity.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # activities schema（需符合你 controller insert / query 使用的欄位）
    cur.execute("""
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            scheme_name TEXT,
            scheme_item TEXT,
            amount REAL,
            note TEXT,
            is_closed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # additional tables used by plans/signup operations
    cur.execute("""
        CREATE TABLE activity_plans (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            name TEXT,
            items TEXT,
            price_type TEXT,
            fixed_price INTEGER,
            suggested_price INTEGER,
            min_price INTEGER,
            note TEXT,
            allow_qty INTEGER,
            sort_order INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE activity_signups (
            id TEXT PRIMARY KEY,
            activity_id TEXT,
            person_id TEXT,
            signup_time TEXT,
            note TEXT,
            total_amount INTEGER,
            is_paid INTEGER DEFAULT 0,
            paid_at TEXT,
            payment_txn_id INTEGER,
            payment_receipt_number TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE activity_signup_plans (
            id TEXT PRIMARY KEY,
            signup_id TEXT,
            plan_id TEXT,
            qty INTEGER,
            unit_price_snapshot INTEGER,
            amount_override INTEGER,
            line_total INTEGER,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()

    # freeze datetime.now() for predictable activity_id
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 13, 10, 0, 0)  # 2026-01-13

    import app.controller.app_controller as app_controller_module
    monkeypatch.setattr(app_controller_module, "datetime", FixedDateTime)

    controller = AppController(db_path=str(db_path))
    yield controller

    try:
        controller.conn.close()
    except Exception:
        pass


def _insert_sample_activity(controller, name="安燈", start="2026-02-09", end="2026-02-09", actor: str | None = None):
    data = {
        "activity_name": name,
        "start_date": start,
        "end_date": end,
        "content": "活動備註",
        "scheme_rows": [
            {"scheme_name": "方案A", "scheme_item": "光明燈", "amount": "1000"},
            {"scheme_name": "方案B", "scheme_item": "太歲燈", "amount": 2000},
        ],
    }
    controller.insert_activity(data, actor=actor)


# ---- test_plan_crud_and_logging ----

def test_plan_crud_and_logging(controller_with_activity_db, monkeypatch):
    calls = []
    def fake_log(**kw):
        calls.append(kw)
    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_log)

    c = controller_with_activity_db
    _insert_sample_activity(c, name="活動A", actor="planner")
    # legacy schema returns activity_id separately
    activity_id = c.get_all_activities()[0]["activity_id"]

    plan_id = c.create_activity_plan(
        activity_id=activity_id,
        name="方案1",
        items="物品",
        fee_type="fixed",
        amount=500,
        actor="planner",
    )
    assert plan_id
    assert any(call.get("action") == "新增方案" for call in calls), f"logs: {calls}"

    ok = c.update_activity_plan(
        plan_id,
        {"name": "方案一改", "fee_type": "fixed", "amount": 999},
        actor="planner",
    )
    assert ok
    assert any(call.get("action") == "修改方案" for call in calls), f"logs: {calls}"

    ok2 = c.delete_activity_plan(plan_id, actor="planner")
    assert ok2
    assert any(call.get("action") == "刪除方案" for call in calls), f"logs: {calls}"


def test_activity_crud_and_signup_update_logging(controller_with_activity_db, monkeypatch):
    calls = []
    def fake_log(**kw):
        calls.append(kw)
    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_log)

    c = controller_with_activity_db
    _insert_sample_activity(c, name="活動Log", actor="planner")
    activity_id = c.get_all_activities()[0]["activity_id"]
    assert any(call.get("action") == "新增活動" for call in calls), f"logs: {calls}"

    c.update_activity({
        "activity_id": activity_id,
        "activity_name": "活動Log-改",
        "start_date": "2026-02-10",
        "end_date": "2026-02-10",
        "content": "更新備註",
        "scheme_rows": [{"scheme_name": "方案A", "scheme_item": "物品A", "amount": 300}],
    }, actor="planner")
    assert any(call.get("action") == "修改活動" for call in calls), f"logs: {calls}"


# ---- test_signup_crud_and_logging ----

def test_signup_crud_and_logging(controller_with_activity_db, monkeypatch):
    calls = []
    def fake_log(**kw):
        calls.append(kw)
    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_log)

    c = controller_with_activity_db
    _insert_sample_activity(c, name="報名活動", actor="signupper")
    activity_id = c.get_all_activities()[0]["activity_id"]

    # need a plan to signup
    plan_id = c.create_activity_plan(
        activity_id=activity_id,
        name="入場",
        items="",
        fee_type="fixed",
        amount=100,
        actor="signupper",
    )
    signup_id = c.create_activity_signup(
        activity_id=activity_id,
        person_id="P1",
        selected_plans=[{"plan_id": plan_id, "qty": 1}],
        note="ok",
        actor="signupper",
    )
    assert signup_id
    assert any(call.get("action") == "新增報名" for call in calls), f"logs: {calls}"
    signup_create_logs = [call for call in calls if call.get("action") == "新增報名"]
    assert signup_create_logs, f"logs: {calls}"
    assert "plan_fee_detail" in (signup_create_logs[-1].get("after") or {}), f"logs: {calls}"

    ok_update = c.update_activity_signup_items(
        signup_id,
        {plan_id: 2},
        {},
        actor="signupper",
    )
    assert ok_update
    assert any(call.get("action") == "修改報名" for call in calls), f"logs: {calls}"
    signup_update_logs = [call for call in calls if call.get("action") == "修改報名"]
    assert "plan_fee_detail" in (signup_update_logs[-1].get("after") or {}), f"logs: {calls}"

    ok = c.delete_activity_signup(signup_id, actor="signupper")
    assert ok
    assert any(call.get("action") == "刪除報名" for call in calls), f"logs: {calls}"

    ok3 = c.delete_activity(activity_id, actor="planner")
    assert ok3
    assert any(call.get("action") == "刪除活動" for call in calls), f"logs: {calls}"
