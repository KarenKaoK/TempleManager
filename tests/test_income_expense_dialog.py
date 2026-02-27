import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
from PyQt5.QtCore import QDate, Qt
from datetime import date, timedelta
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
            source_type TEXT,
            source_id TEXT,
            adjustment_kind TEXT,
            adjusts_txn_id INTEGER,
            is_system_generated INTEGER DEFAULT 0,
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
        "T-EDIT-001", date.today().isoformat(), "income", "I01", "香油錢", 500,
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


def _insert_income_tx(controller, tx_id, tx_date):
    cur = controller.conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions (
            id, date, type, category_id, category_name, amount,
            payer_person_id, payer_name, handler, receipt_number, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tx_id, tx_date, "income", "I01", "香油錢", 500,
            "P001", "王小明", "測試員", f"R-{tx_id}", "測試"
        ),
    )
    controller.conn.commit()


def test_staff_only_can_edit_today(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="廟務人員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-STAFF-Y", yesterday)
    tab.refresh_list()
    tab.table.selectRow(0)
    tab._sync_row_action_buttons()

    assert tab.btn_edit_row.isEnabled() is False
    with patch("app.dialogs.income_expense_dialog.QMessageBox.information") as mock_info:
        tab._edit_selected_row()
        mock_info.assert_called_once()
    assert tab.editing_transaction_id is None


def test_accountant_can_edit_non_today(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="會計")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-ACC-Y", yesterday)
    tab.refresh_list()
    tab.table.selectRow(0)
    tab._sync_row_action_buttons()

    assert tab.btn_edit_row.isEnabled() is True
    row_data = tab._get_selected_row_data()
    tab.load_transaction_to_form(row_data)
    assert tab.editing_transaction_id == "T-ACC-Y"


def test_admin_can_edit_non_today(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="管理員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-ADMIN-Y", yesterday)
    tab.refresh_list()
    tab.table.selectRow(0)
    tab._sync_row_action_buttons()

    assert tab.btn_edit_row.isEnabled() is True
    row_data = tab._get_selected_row_data()
    tab.load_transaction_to_form(row_data)
    assert tab.editing_transaction_id == "T-ADMIN-Y"


def test_admin_update_non_today_is_allowed(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="管理員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-ADMIN-SAVE", yesterday)

    tab.editing_transaction_id = "T-ADMIN-SAVE"
    tab.editing_source_date = yesterday
    tab.set_person({
        "id": "P001",
        "name": "王小明",
        "phone_mobile": "0912345678",
        "phone_home": "",
        "address": "台北市信義區測試路100號",
    })
    tab.amount_input.setText("777")
    tab.category_combo.setCurrentIndex(0)

    with patch.object(tab.controller, "update_transaction") as mock_update, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.warning") as mock_warn, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.information"):
        tab.save_data(print_receipt=False)
        mock_update.assert_called_once()
        mock_warn.assert_not_called()


def test_staff_update_is_blocked_when_editing_source_date_not_today(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="廟務人員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-STAFF-GUARD", yesterday)
    tab.editing_transaction_id = "T-STAFF-GUARD"
    tab.editing_source_date = yesterday

    tab.set_person({
        "id": "P001",
        "name": "王小明",
        "phone_mobile": "0912345678",
        "phone_home": "",
        "address": "台北市信義區測試路100號",
    })
    tab.amount_input.setText("999")
    tab.category_combo.setCurrentIndex(0)

    with patch.object(tab.controller, "update_transaction") as mock_update, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.warning") as mock_warn:
        tab.save_data(print_receipt=False)
        mock_update.assert_not_called()
        mock_warn.assert_called_once()

    assert tab.editing_transaction_id is None


def test_staff_delete_non_today_is_blocked(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="工作人員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-STAFF-DEL", yesterday)
    tab.refresh_list()
    tab.table.selectRow(0)
    row_data = tab._get_selected_row_data()

    with patch.object(tab.controller, "delete_transaction") as mock_delete, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.warning") as mock_warn:
        tab.delete_transaction(row_data)
        mock_delete.assert_not_called()
        mock_warn.assert_called_once()


def test_admin_delete_non_today_is_allowed(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    dlg = IncomeExpenseDialog(controller, parent=None, user_role="管理員")
    qtbot.addWidget(dlg)
    tab = dlg.income_tab

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _insert_income_tx(controller, "T-ADMIN-DEL", yesterday)
    tab.refresh_list()
    tab.table.selectRow(0)
    row_data = tab._get_selected_row_data()

    with patch.object(tab.controller, "delete_transaction") as mock_delete, \
         patch("app.dialogs.income_expense_dialog.QMessageBox.question", return_value=QMessageBox.Yes), \
         patch("app.dialogs.income_expense_dialog.QMessageBox.information"):
        tab.delete_transaction(row_data)
        mock_delete.assert_called_once_with("T-ADMIN-DEL")


def test_handler_input_prefills_operator_name_account(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    parent = QWidget()
    parent.operator_name = "王小明(admin01)"
    qtbot.addWidget(parent)

    dlg = IncomeExpenseDialog(controller, parent=parent)

    assert dlg.income_tab.handler_input.text() == "王小明(admin01)"
    assert dlg.expense_tab.handler_input.text() == "王小明(admin01)"


def test_handler_input_is_readonly_for_non_admin(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    parent = QWidget()
    parent.operator_name = "王小明(admin01)"
    qtbot.addWidget(parent)

    dlg = IncomeExpenseDialog(controller, parent=parent, user_role="工作人員")

    assert dlg.income_tab.handler_input.isReadOnly() is True
    assert dlg.expense_tab.handler_input.isReadOnly() is True


def test_handler_input_is_editable_for_admin(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    parent = QWidget()
    parent.operator_name = "王小明(admin01)"
    qtbot.addWidget(parent)

    dlg = IncomeExpenseDialog(controller, parent=parent, user_role="管理員")

    assert dlg.income_tab.handler_input.isReadOnly() is False
    assert dlg.expense_tab.handler_input.isReadOnly() is False


def test_handler_input_is_editable_for_accountant(qtbot, temp_db):
    controller = AppController(db_path=str(temp_db))
    parent = QWidget()
    parent.operator_name = "王小明(account01)"
    qtbot.addWidget(parent)

    dlg = IncomeExpenseDialog(controller, parent=parent, user_role="會計")

    assert dlg.income_tab.handler_input.isReadOnly() is False
    assert dlg.expense_tab.handler_input.isReadOnly() is False


def test_new_income_save_clears_form_fields(qtbot, dialog):
    tab = dialog.income_tab
    tab.set_person({
        "id": "P001",
        "name": "王小明",
        "phone_mobile": "0912345678",
        "phone_home": "",
        "address": "台北市信義區測試路100號",
    })
    tab.category_combo.setCurrentIndex(0)
    tab.amount_input.setText("1234")
    tab.note_input.setText("測試備註")

    with patch("app.dialogs.income_expense_dialog.QMessageBox.information"):
        tab.save_data(print_receipt=False)

    assert tab.amount_input.text() == ""
    assert tab.note_input.text() == ""
    assert tab.receipt_input.text() == ""
    assert tab.selected_person_id is None
    assert tab.selected_person_data is None
    assert tab.payer_name_display.text() == ""
    assert tab.payer_phone_display.text() == ""

    rows = tab.controller.get_transactions("income")
    assert any(int(r.get("amount") or 0) == 1234 for r in rows)
