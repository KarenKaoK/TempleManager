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
    controller.insert_activity(data)


# -------------------------
# generate_activity_id
# -------------------------

def test_generate_activity_id_increments(controller_with_activity_db):
    c = controller_with_activity_db

    # 第一次：DB 內還沒資料
    activity_id_1 = c.generate_activity_id()
    assert activity_id_1 == "20260113-001"

    # 插入一筆活動（會用 generate_activity_id 再生成一次）
    _insert_sample_activity(c, name="安燈")

    # 第二次：同一天應該變 002
    activity_id_2 = c.generate_activity_id()
    assert activity_id_2 == "20260113-002"


# -------------------------
# insert_activity + get_all_activities
# -------------------------

def test_insert_activity_and_get_all_activities(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="安燈")

    rows = c.get_all_activities()
    assert len(rows) == 1

    row = rows[0]
    # row is sqlite3.Row
    assert row["activity_id"].startswith("20260113-")
    assert row["name"] == "安燈"
    assert row["start_date"] == "2026-02-09"
    assert row["end_date"] == "2026-02-09"
    assert row["is_closed"] == 0

    # scheme_names/items/amounts should be joined with newline
    assert "方案A" in row["scheme_names"]
    assert "方案B" in row["scheme_names"]
    assert "光明燈" in row["scheme_items"]
    assert "太歲燈" in row["scheme_items"]
    assert "1000" in str(row["amounts"])
    assert "2000" in str(row["amounts"])


# -------------------------
# search_activities
# -------------------------

def test_search_activities_by_name_or_date(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="年度安燈")

    # 用 name 搜
    rows = c.search_activities("安燈")
    assert len(rows) == 1
    assert rows[0]["name"] == "年度安燈"

    # 用 start_date 搜
    rows2 = c.search_activities("2026-02-09")
    assert len(rows2) == 1
    assert rows2[0]["name"] == "年度安燈"

    # 用 activity_id 前綴搜（同一天）
    rows3 = c.search_activities("20260113")
    assert len(rows3) == 1
    assert rows3[0]["name"] == "年度安燈"


# -------------------------
# get_activity_by_id
# -------------------------

def test_get_activity_by_id_returns_basic_and_schemes(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="活動一")

    activity_id = c.get_all_activities()[0]["activity_id"]
    basic, schemes = c.get_activity_by_id(activity_id)

    assert basic["activity_id"] == activity_id
    assert basic["activity_name"] == "活動一"
    assert basic["start_date"] == "2026-02-09"
    assert basic["end_date"] == "2026-02-09"
    assert basic["content"] == "活動備註"

    assert isinstance(schemes, list)
    assert len(schemes) == 2
    assert schemes[0].keys() == {"scheme_name", "scheme_item", "amount"}


# -------------------------
# update_activity
# -------------------------

def test_update_activity_replaces_rows(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="活動一")

    activity_id = c.get_all_activities()[0]["activity_id"]

    update_data = {
        "activity_id": activity_id,
        "activity_name": "活動一(更新)",
        "start_date": "2026-02-10",
        "end_date": "2026-02-11",
        "content": "更新備註",
        "scheme_rows": [
            {"scheme_name": "新版", "scheme_item": "點燈", "amount": "888"},
        ],
    }

    c.update_activity(update_data)

    # 重新查
    rows = c.get_all_activities()
    assert len(rows) == 1
    row = rows[0]
    assert row["activity_id"] == activity_id
    assert row["name"] == "活動一(更新)"
    assert row["start_date"] == "2026-02-10"
    assert row["end_date"] == "2026-02-11"
    assert "新版" in row["scheme_names"]
    assert "點燈" in row["scheme_items"]
    assert "888" in str(row["amounts"])

    basic, schemes = c.get_activity_by_id(activity_id)
    assert basic["activity_name"] == "活動一(更新)"
    assert len(schemes) == 1
    assert schemes[0]["scheme_name"] == "新版"


# -------------------------
# delete_activity
# -------------------------

def test_delete_activity_success_and_not_found(controller_with_activity_db):
    c = controller_with_activity_db
    _insert_sample_activity(c, name="活動一")

    activity_id = c.get_all_activities()[0]["activity_id"]

    ok = c.delete_activity(activity_id)
    assert ok is True
    assert c.get_all_activities() == []

    ok2 = c.delete_activity(activity_id)  # already deleted
    assert ok2 is False
