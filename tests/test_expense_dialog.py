import pytest
import sqlite3
from PyQt5.QtWidgets import QDialog
from unittest.mock import patch, MagicMock
from app.dialogs.expense_dialog import ExpenseSetupDialog
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QTableWidgetItem

@pytest.fixture
def temp_expense_db(tmp_path):
    db_path = tmp_path / "test_expense.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT INTO expense_items (id, name, amount) VALUES ('E01', '香油支出', 800)")
    cursor.execute("INSERT INTO expense_items (id, name, amount) VALUES ('E02', '廟務費用', 1200)")
    conn.commit()
    conn.close()

    return db_path

def test_expense_dialog_load_data(qtbot, temp_expense_db):
    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "E01"
    assert dialog.table.item(0, 1).text() == "香油支出"
    assert dialog.table.item(0, 2).text() == "800"

    assert dialog.table.item(1, 0).text() == "E02"
    assert dialog.table.item(1, 1).text() == "廟務費用"
    assert dialog.table.item(1, 2).text() == "1200"


@pytest.fixture
def empty_expense_db(tmp_path):
    db_path = tmp_path / "test_expense_empty.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

    return db_path

def test_expense_dialog_load_empty_data(qtbot, empty_expense_db):
    """測試資料庫為空時，表格應為空"""
    dialog = ExpenseSetupDialog(db_path=str(empty_expense_db))
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 0

def test_expense_dialog_add_duplicate_id(qtbot, temp_expense_db):
    """測試新增失敗（ID 重複）"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_expense_item(
            dialog=dialog,
            id="E01",  # 已存在
            name="重複項目",
            amount=999
        )

        mock_warning.assert_called_once_with(
            dialog,
            "錯誤",
            "支出項目代號 E01 已存在，請輸入其他代號！"
        )

    # ✅ 表格仍為原始 2 筆資料
    assert dialog.table.rowCount() == 2

def test_expense_dialog_add_blank_id(qtbot, temp_expense_db):
    """測試新增失敗（ID 空白）"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_expense_item(
            dialog=dialog,
            id="   ",  # 空白 ID
            name="測試項目",
            amount=100
        )

        # 預期跳出錯誤訊息
        mock_warning.assert_called_once_with(dialog, "錯誤", "支出項目代號不可為空！")

    # 確保表格未新增新資料
    assert dialog.table.rowCount() == 2

def test_expense_dialog_add_blank_name(qtbot, temp_expense_db):
    """測試新增失敗（名稱空白）"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_expense_item(
            dialog=dialog,
            id="E03",            # 合法 ID
            name="   ",          # 名稱為空白
            amount=500
        )

        # 預期跳出錯誤訊息
        mock_warning.assert_called_once_with(dialog, "錯誤", "請填寫支出項目名稱！")

    # 確保沒有新增資料
    assert dialog.table.rowCount() == 2

def test_expense_dialog_edit_no_selection(qtbot, temp_expense_db):
    """測試沒有選擇項目時點修改，跳錯誤訊息"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.clearSelection()  # 確保沒有任何選取

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.edit_expense_item()
        mock_warning.assert_called_once_with(dialog, "錯誤", "請選擇要修改的支出項目！")

def test_expense_dialog_edit_success(qtbot, temp_expense_db):
    """測試成功修改支出項目"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.selectRow(0)  # 選取第一筆資料
    item_id = dialog.table.item(0, 0).text()  # ID 不可變

    with patch("app.dialogs.expense_dialog.QMessageBox.information") as mock_info:
        # 直接呼叫 confirm_edit_expense_item 模擬使用者修改成功
        dialog.confirm_edit_expense_item(dialog, item_id, "修改項目", 888)

        # 驗證資料已更新
        assert dialog.table.item(0, 0).text() == item_id
        assert dialog.table.item(0, 1).text() == "修改項目"
        assert dialog.table.item(0, 2).text() == "888"

        mock_info.assert_called_once_with(dialog, "成功", "支出項目修改成功！")

def test_expense_dialog_edit_fail_empty_name(qtbot, temp_expense_db):
    """測試修改失敗（名稱空白）"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.selectRow(0)  # 選取第一筆資料

    item_id = dialog.table.item(0, 0).text()
    original_name = dialog.table.item(0, 1).text()
    original_amount = dialog.table.item(0, 2).text()

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_edit_expense_item(dialog, item_id, "", 999)

        # 驗證未更新
        assert dialog.table.item(0, 0).text() == item_id
        assert dialog.table.item(0, 1).text() == original_name
        assert dialog.table.item(0, 2).text() == original_amount

        mock_warning.assert_called_once_with(dialog, "錯誤", "請填寫支出項目名稱！")

def test_expense_dialog_delete_no_selection(qtbot, temp_expense_db):
    """測試未選擇項目時點刪除，跳錯誤訊息"""
    from app.dialogs.expense_dialog import ExpenseSetupDialog
    from unittest.mock import patch

    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.clearSelection()  # 清除所有選取

    with patch("app.dialogs.expense_dialog.QMessageBox.warning") as mock_warning:
        dialog.delete_expense_item()

        mock_warning.assert_called_once_with(dialog, "錯誤", "請選擇要刪除的支出項目！")


def test_expense_dialog_delete_success(qtbot, temp_expense_db):
    """測試刪除存在的支出項目成功"""
    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)
    dialog.table.selectRow(0)  # 選取第一筆資料

    with patch.object(dialog, "ask_confirm", return_value=True), \
         patch.object(dialog, "show_info") as mock_info:

        dialog.delete_expense_item()

        # ✅ 確認資料已刪除，只剩一筆
        assert dialog.table.rowCount() == 1
        assert dialog.table.item(0, 0).text() == "E02"
        assert dialog.table.item(0, 1).text() == "廟務費用"
        assert dialog.table.item(0, 2).text() == "1200"

        mock_info.assert_called_once_with("成功", "支出項目刪除成功！")

def test_expense_dialog_delete_invalid_id_not_found(qtbot, temp_expense_db):
    """測試刪除不存在 ID 時應跳錯誤訊息"""
    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.insertRow(0)
    dialog.table.setItem(0, 0, QTableWidgetItem("Z99"))  # 不存在的 ID
    dialog.table.setItem(0, 1, QTableWidgetItem("測試項目"))
    dialog.table.setItem(0, 2, QTableWidgetItem("999"))

    dialog.table.selectRow(0)

    with patch.object(dialog, "ask_confirm", return_value=True), \
         patch.object(dialog, "show_warning") as mock_warning:

        dialog.delete_expense_item()

        mock_warning.assert_called_once_with("錯誤", "刪除失敗，請檢查 ID 是否存在！")

def test_expense_dialog_delete_cancelled(qtbot, temp_expense_db):
    """測試點刪除後選「否」，應取消刪除並保留資料"""
    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.selectRow(0)  # 選取第一筆資料（E01）

    with patch.object(dialog, "ask_confirm", return_value=False), \
         patch.object(dialog, "show_info") as mock_info:

        dialog.delete_expense_item()

        # ✅ 應無刪除（仍然是兩筆）
        assert dialog.table.rowCount() == 2

        # ✅ 應無顯示成功訊息
        mock_info.assert_not_called()

        # ✅ 原資料仍存在
        assert dialog.table.item(0, 0).text() == "E01"
        assert dialog.table.item(0, 1).text() == "香油支出"
        assert dialog.table.item(0, 2).text() == "800"

def test_expense_dialog_delete_confirmed_but_not_found(qtbot, temp_expense_db):
    """測試點選「是」但資料未刪除（rowcount == 0）應顯示錯誤訊息"""
    dialog = ExpenseSetupDialog(db_path=str(temp_expense_db))
    qtbot.addWidget(dialog)

    dialog.table.selectRow(0)
    item_id = dialog.table.item(0, 0).text()

    # 模擬該筆資料已經被刪除，先從資料庫手動刪除
    conn = sqlite3.connect(str(temp_expense_db))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expense_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    with patch.object(dialog, "ask_confirm", return_value=True), \
         patch.object(dialog, "show_warning") as mock_warning, \
         patch.object(dialog, "show_info") as mock_info:

        dialog.delete_expense_item()

        # ✅ 表格資料應該仍有兩筆（因為沒 reload）
        assert dialog.table.rowCount() == 2

        # ✅ 顯示刪除失敗的錯誤訊息
        mock_warning.assert_called_once_with("錯誤", "刪除失敗，請檢查 ID 是否存在！")

        # ✅ 不應該呼叫成功訊息
        mock_info.assert_not_called()
