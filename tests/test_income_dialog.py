import pytest
import sqlite3
from app.dialogs.income_dialog import IncomeSetupDialog

# ✅ 測試用資料庫 fixture（有資料）
@pytest.fixture
def temp_income_db(tmp_path):
    db_path = tmp_path / "test_income.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT INTO income_items (id, name, amount) VALUES ('I01', '香油錢', 1000)")
    cursor.execute("INSERT INTO income_items (id, name, amount) VALUES ('I02', '補運金', 5000)")
    conn.commit()
    conn.close()

    return db_path

# ✅ 測試：有資料時載入正確
def test_income_dialog_load_data(qtbot, temp_income_db):
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "I01"
    assert dialog.table.item(0, 1).text() == "香油錢"
    assert dialog.table.item(0, 2).text() == "1000"

    assert dialog.table.item(1, 0).text() == "I02"
    assert dialog.table.item(1, 1).text() == "補運金"
    assert dialog.table.item(1, 2).text() == "5000"

# ✅ 測試用資料庫 fixture（無資料）
@pytest.fixture
def empty_income_db(tmp_path):
    db_path = tmp_path / "test_empty_income.db"
    print("test db path:", db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

    return db_path

# ✅ 測試：資料庫為空時表格應該為空
def test_income_dialog_load_empty_data(qtbot, empty_income_db):
    dialog = IncomeSetupDialog(db_path=str(empty_income_db))
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 0
