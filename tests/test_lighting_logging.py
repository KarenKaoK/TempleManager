import sqlite3
import pytest

from app.controller.app_controller import AppController
from app.database.setup_db import (
    create_security_tables,
    create_lighting_items_table,
    create_lighting_signup_tables,
)


@pytest.fixture
def controller_with_lighting_log_db(tmp_path):
    db_path = tmp_path / "lighting_logging.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone_mobile TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category_id TEXT NOT NULL,
            category_name TEXT,
            amount INTEGER DEFAULT 0,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            receipt_number TEXT,
            note TEXT,
            source_type TEXT,
            source_id TEXT,
            adjustment_kind TEXT,
            adjusts_txn_id INTEGER,
            is_system_generated INTEGER DEFAULT 0,
            is_voided INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("INSERT INTO people (id, name, phone_mobile) VALUES ('P1', '王大明', '0912000000')")
    conn.commit()
    conn.close()

    create_security_tables(str(db_path))
    create_lighting_items_table(str(db_path))
    create_lighting_signup_tables(str(db_path))
    c = AppController(db_path=str(db_path))
    yield c
    try:
        c.conn.close()
    except Exception:
        pass


def test_create_lighting_item_writes_data_log(controller_with_lighting_log_db, monkeypatch):
    calls = []

    def fake_data(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_data)

    c = controller_with_lighting_log_db
    item_id = c.create_lighting_item(name="文昌燈", fee=888, kind="JI_XIANG")
    assert item_id
    log = next(
        call["kwargs"]
        for call in calls
        if call["kwargs"].get("action") == "LIGHTING.ITEM.CREATE"
    )
    assert "文昌燈" in log.get("message", "")
    assert f"燈別ID {item_id}" in log.get("message", "")


def test_update_missing_lighting_item_writes_system_log(controller_with_lighting_log_db, monkeypatch):
    calls = []

    def fake_system(message: str, level: str = "INFO"):
        calls.append({"message": message, "level": level})

    monkeypatch.setattr("app.controller.app_controller.log_system", fake_system)

    c = controller_with_lighting_log_db
    ok = c.update_lighting_item("L99", "不存在燈別", 100, "JI_XIANG")
    assert ok is False
    assert any(
        call.get("level") == "WARN" and "修改安燈燈別失敗" in call.get("message", "")
        for call in calls
    )


def test_upsert_lighting_signup_writes_data_log(controller_with_lighting_log_db, monkeypatch):
    calls = []

    def fake_data(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_data)

    c = controller_with_lighting_log_db
    sid = c.upsert_lighting_signup(2026, "P1", ["L01", "L02"], note="安燈測試")
    assert sid
    log = next(
        call["kwargs"]
        for call in calls
        if call["kwargs"].get("action") == "LIGHTING.SIGNUP.CREATE"
    )
    msg = log.get("message", "")
    assert f"signup_id {sid}" in msg
    assert "報名人 王大明" in msg
    assert "L01" in msg


def test_mark_lighting_paid_writes_data_log_with_person(controller_with_lighting_log_db, monkeypatch):
    data_calls = []

    def fake_data(*args, **kwargs):
        data_calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_data)

    c = controller_with_lighting_log_db
    sid = c.upsert_lighting_signup(2026, "P1", ["L01"], note="付款測試")
    result = c.mark_lighting_signups_paid(2026, [sid], handler="櫃台A")
    assert result["paid_count"] == 1
    receipt = result["receipt_numbers"][0]

    log = next(
        call["kwargs"]
        for call in data_calls
        if call["kwargs"].get("action") == "LIGHTING.SIGNUP.PAY"
    )
    msg = log.get("message", "")
    assert "王大明" in msg
    assert f"signup_id {sid}" in msg
    assert f"收據 {receipt}" in msg


def test_mark_lighting_paid_empty_handler_writes_system_log(controller_with_lighting_log_db, monkeypatch):
    system_calls = []

    def fake_system(message: str, level: str = "INFO"):
        system_calls.append({"message": message, "level": level})

    monkeypatch.setattr("app.controller.app_controller.log_system", fake_system)

    c = controller_with_lighting_log_db
    sid = c.upsert_lighting_signup(2026, "P1", ["L01"], note="付款測試")
    assert sid
    with pytest.raises(ValueError, match="經手人為必填"):
        c.mark_lighting_signups_paid(2026, [sid], handler="")

    assert any(
        call.get("level") == "WARN" and "安燈報名繳費失敗" in call.get("message", "")
        for call in system_calls
    )
