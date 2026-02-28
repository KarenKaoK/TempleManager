import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def controller_with_tx_db(tmp_path):
    db_path = tmp_path / "tx_logging.db"
    c = AppController(db_path=str(db_path))
    cur = c.conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
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
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.conn.commit()
    yield c
    try:
        c.conn.close()
    except Exception:
        pass


def _latest_tx_id(controller):
    row = controller.conn.cursor().execute(
        "SELECT id FROM transactions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def test_income_transaction_crud_writes_data_change_log(controller_with_tx_db, monkeypatch):
    calls = []

    def fake_log(**kw):
        calls.append(kw)

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_log)
    c = controller_with_tx_db

    c.add_transaction({
        "date": "2026-02-25",
        "type": "income",
        "category_id": "90",
        "category_name": "活動收入",
        "amount": 1200,
        "payer_person_id": "P001",
        "payer_name": "王小明",
        "handler": "櫃台A",
        "receipt_number": "1150001",
        "note": "測試收入",
    })
    tx_id = _latest_tx_id(c)
    assert tx_id is not None
    assert any(call.get("action") == "INCOME.CREATE" for call in calls), f"logs: {calls}"

    c.update_transaction(tx_id, {
        "date": "2026-02-26",
        "category_id": "90",
        "category_name": "活動收入",
        "amount": 1500,
        "payer_person_id": "P001",
        "payer_name": "王小明",
        "handler": "櫃台B",
        "note": "測試收入更新",
    })
    assert any(call.get("action") == "INCOME.UPDATE" for call in calls), f"logs: {calls}"

    c.delete_transaction(tx_id)
    assert any(call.get("action") == "INCOME.DELETE" for call in calls), f"logs: {calls}"


def test_expense_transaction_crud_writes_data_change_log(controller_with_tx_db, monkeypatch):
    calls = []

    def fake_log(**kw):
        calls.append(kw)

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_log)
    c = controller_with_tx_db

    c.add_transaction({
        "date": "2026-02-25",
        "type": "expense",
        "category_id": "E01",
        "category_name": "採買",
        "amount": 800,
        "payer_person_id": None,
        "payer_name": "廠商甲",
        "handler": "會計A",
        "receipt_number": "1150002",
        "note": "測試支出",
    })
    tx_id = _latest_tx_id(c)
    assert tx_id is not None
    assert any(call.get("action") == "EXPENSE.CREATE" for call in calls), f"logs: {calls}"

    c.update_transaction(tx_id, {
        "date": "2026-02-26",
        "category_id": "E01",
        "category_name": "採買",
        "amount": 900,
        "payer_person_id": None,
        "payer_name": "廠商甲",
        "handler": "會計B",
        "note": "測試支出更新",
    })
    assert any(call.get("action") == "EXPENSE.UPDATE" for call in calls), f"logs: {calls}"

    c.delete_transaction(tx_id)
    assert any(call.get("action") == "EXPENSE.DELETE" for call in calls), f"logs: {calls}"
