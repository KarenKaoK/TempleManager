import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QDate, Qt
from app.dialogs.income_expense_dialog import IncomeExpenseDialog
from app.controller.app_controller import AppController

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_integration.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Transactions
    cur.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            date TEXT,
            type TEXT,
            category_id TEXT,
            category_name TEXT,
            amount INTEGER,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            note TEXT,
            receipt_number TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    
    # 2. People
    cur.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone_mobile TEXT,
            phone_home TEXT,
            address TEXT,
            gender TEXT,
            birthday_ad TEXT,
            birthday_lunar TEXT,
            birth_time TEXT,
            role_in_household TEXT,
            status TEXT,
            household_id TEXT,
            joined_at TEXT
        )
    """)
    # 插入測試信徒 (有地址)
    cur.execute("""
        INSERT INTO people (id, name, phone_mobile, address) 
        VALUES ('P001', '王小明', '0912345678', '台北市信義區測試路100號')
    """)
    
    # 3. Income Items
    cur.execute("""
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT,
            amount INTEGER DEFAULT 0
        )
    """)
    cur.execute("INSERT INTO income_items (id, name, amount) VALUES ('I01', '香油錢', 100)")
    
    # 4. Expense Items (Optional)
    cur.execute("""
        CREATE TABLE expense_items (
            id TEXT PRIMARY KEY,
            name TEXT,
            amount INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    return db_path

@pytest.fixture
def dialog(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    # Corrected: No t_type in __init__
    dlg = IncomeExpenseDialog(controller, parent=None)
    qtbot.addWidget(dlg)
    return dlg

def test_save_and_print_includes_address(qtbot, dialog):
    """
    整合測試：
    1. 開啟視窗
    2. 選擇信徒 (模擬)
    3. 填入資料
    4. 按下「存檔並列印」
    5. 驗證 PrintHelper.print_receipt 被呼叫，且 data 含有正確 address
    """
    
    # 1. 模擬選擇信徒 (透過 income_tab)
    person_data = {
        'id': 'P001',
        'name': '王小明',
        'phone_mobile': '0912345678',
        'phone_home': '',
        'address': '台北市信義區測試路100號'
    }
    dialog.income_tab.set_person(person_data)
    
    # 2. 填入其他必要欄位 (透過 income_tab)
    dialog.income_tab.amount_input.setText("1000")
    dialog.income_tab.category_combo.setCurrentIndex(0) # 選到香油錢
    
    # 3. Mock PrintHelper 和 QMessageBox
    with patch("app.dialogs.income_expense_dialog.PrintHelper") as MockPrintHelper, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.information") as mock_info:
        
        # 4. 觸發存檔並列印
        dialog.income_tab.save_data(print_receipt=True)
        
        # 5. 驗證
        assert MockPrintHelper.print_receipt.called, "print_receipt 應該被呼叫"
        
        # 取得呼叫參數
        call_args = MockPrintHelper.print_receipt.call_args
        payload = call_args[0][0]
        
        assert payload['payer_name'] == '王小明'
        assert payload['amount'] == 1000
        # 關鍵驗證：地址是否有帶入
        assert payload['address'] == '台北市信義區測試路100號'
        
        mock_info.assert_called() # 成功訊息


def test_edit_income_then_save_and_print_calls_print(qtbot, dialog):
    """
    編輯模式下按「存檔並列印」也要觸發列印。
    """
    tab = dialog.income_tab

    # 先建立一筆既有收入資料（要有 id 才會進入編輯模式）
    cur = tab.controller.conn.cursor()
    cur.execute("""
        INSERT INTO transactions (
            id, date, type, category_id, category_name, amount,
            payer_person_id, payer_name, handler, receipt_number, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "T-EDIT-001", "2026-02-16", "income", "I01", "香油錢", 500,
        "P001", "王小明", "測試員", "1150001", "舊備註"
    ))
    tab.controller.conn.commit()

    rows = tab.controller.get_transactions("income")
    assert rows, "應該至少有一筆收入資料可供編輯"
    original = rows[0]

    # 模擬從列表右鍵「修改資料」帶入表單
    tab.load_transaction_to_form(original)
    tab.amount_input.setText("888")
    tab.note_input.setText("更新後備註")

    with patch("app.dialogs.income_expense_dialog.PrintHelper") as MockPrintHelper, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.information"):
        tab.save_data(print_receipt=True)

        assert MockPrintHelper.print_receipt.called, "編輯後存檔並列印應該觸發列印"
        payload = MockPrintHelper.print_receipt.call_args[0][0]
        assert payload["receipt_number"] == "1150001"
        assert payload["amount"] == 888
        assert payload["payer_name"] == "王小明"

    # 驗證資料確實更新
    updated_rows = tab.controller.get_transactions("income")
    updated = next(r for r in updated_rows if r["id"] == original["id"])
    assert updated["amount"] == 888
    assert updated["note"] == "更新後備註"
