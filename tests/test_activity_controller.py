import sqlite3
import re
import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def mock_activity_logs(monkeypatch):
    calls = {"data": [], "system": []}

    def fake_data(*args, **kwargs):
        calls["data"].append({"args": args, "kwargs": kwargs})

    def fake_system(message: str, level: str = "INFO"):
        calls["system"].append({"message": message, "level": level})

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_data)
    monkeypatch.setattr("app.controller.app_controller.log_system", fake_system)
    return calls


@pytest.fixture
def controller_with_activity_db(tmp_path):
    """
    建立新版活動 schema 測試 DB，回傳 AppController。
    """
    db_path = tmp_path / "test_activity.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            activity_start_date TEXT NOT NULL,
            activity_end_date TEXT NOT NULL,
            note TEXT,
            status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE activity_plans (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            items TEXT,
            price_type TEXT NOT NULL,
            fixed_price INTEGER DEFAULT 0,
            note TEXT,
            suggested_price INTEGER DEFAULT 0,
            min_price INTEGER DEFAULT 0,
            allow_qty INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE activity_signups (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            signup_kind TEXT NOT NULL DEFAULT 'INITIAL',
            signup_time TEXT NOT NULL,
            note TEXT,
            total_amount INTEGER NOT NULL DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            paid_at TEXT,
            payment_txn_id INTEGER,
            payment_receipt_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    controller = AppController(db_path=str(db_path))
    yield controller

    try:
        controller.conn.close()
    except Exception:
        pass


def _insert_sample_activity(controller, name="安燈", start="2026-02-09", end="2026-02-09"):
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
    return controller.insert_activity(data)


def test_generate_activity_id_returns_14_digits(controller_with_activity_db):
    c = controller_with_activity_db
    aid = c.generate_activity_id()
    assert re.fullmatch(r"\d{14}", aid)


def test_insert_activity_and_get_all_activities(controller_with_activity_db):
    c = controller_with_activity_db
    aid = _insert_sample_activity(c, name="安燈")

    rows = c.get_all_activities()
    assert len(rows) == 1

    row = rows[0]
    assert row["id"] == aid
    assert row["name"] == "安燈"
    assert row["activity_start_date"] == "2026-02-09"
    assert row["activity_end_date"] == "2026-02-09"
    assert int(row["status"]) == 1

    plans = c.get_activity_plans(aid, active_only=False)
    assert len(plans) == 2
    assert {p["name"] for p in plans} == {"方案A", "方案B"}


def test_search_activities_by_name_or_date(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="年度安燈")

    rows = c.search_activities("安燈")
    assert len(rows) == 1
    assert rows[0]["name"] == "年度安燈"

    rows2 = c.search_activities("2026-02-09")
    assert len(rows2) == 1
    assert rows2[0]["name"] == "年度安燈"


def test_get_activity_by_id_returns_new_schema_row(controller_with_activity_db):
    c = controller_with_activity_db
    aid = _insert_sample_activity(c, name="活動一")
    row = c.get_activity_by_id(aid)

    assert row is not None
    assert row["id"] == aid
    assert row["name"] == "活動一"
    assert row["activity_start_date"] == "2026-02-09"
    assert row["activity_end_date"] == "2026-02-09"
    assert row["note"] == "活動備註"


def test_update_activity_replaces_rows(controller_with_activity_db):
    c = controller_with_activity_db
    aid = _insert_sample_activity(c, name="活動一")

    update_data = {
        "name": "活動一(更新)",
        "activity_start_date": "2026-02-10",
        "activity_end_date": "2026-02-11",
        "note": "更新備註",
        "status": 1,
    }

    c.update_activity(aid, update_data)

    rows = c.get_all_activities()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == aid
    assert row["name"] == "活動一(更新)"
    assert row["activity_start_date"] == "2026-02-10"
    assert row["activity_end_date"] == "2026-02-11"

    got = c.get_activity_by_id(aid)
    assert got["name"] == "活動一(更新)"
    assert got["note"] == "更新備註"


def test_delete_activity_success_and_not_found(controller_with_activity_db):
    c = controller_with_activity_db
    aid = _insert_sample_activity(c, name="活動一")

    ok = c.delete_activity(aid)
    assert ok is True
    assert c.get_all_activities() == []

    ok2 = c.delete_activity(aid)
    assert ok2 is False


def test_insert_activity_writes_data_log(controller_with_activity_db, mock_activity_logs):
    c = controller_with_activity_db
    aid = _insert_sample_activity(c, name="活動Log測試")
    assert aid
    assert any(
        call["kwargs"].get("action") == "ACTIVITY.CREATE"
        for call in mock_activity_logs["data"]
    )


def test_update_missing_activity_writes_system_log(controller_with_activity_db, mock_activity_logs):
    c = controller_with_activity_db
    c.update_activity("NOT_EXISTS", {
        "name": "不存在",
        "activity_start_date": "2026-02-10",
        "activity_end_date": "2026-02-11",
        "note": "",
        "status": 1,
    })
    assert any(
        call.get("level") == "WARN" and "活動更新失敗" in call.get("message", "")
        for call in mock_activity_logs["system"]
    )


def test_delete_missing_activity_writes_system_log(controller_with_activity_db, mock_activity_logs):
    c = controller_with_activity_db
    ok = c.delete_activity("NOT_EXISTS")
    assert ok is False
    assert any(
        call.get("level") == "WARN" and "活動刪除失敗" in call.get("message", "")
        for call in mock_activity_logs["system"]
    )
