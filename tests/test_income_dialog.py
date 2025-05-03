import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QMessageBox
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



def test_income_dialog_add_item_success(qtbot, temp_income_db):
    """測試成功新增收入項目，不跳出 QMessageBox"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.income_dialog.QMessageBox.information"):
        dialog.confirm_add_income_item(
            dialog=dialog,
            id="I03",
            name="平安金",
            amount=3000
        )

    # 查詢表格內容
    row_count = dialog.table.rowCount()
    last_row = row_count - 1

    assert row_count == 3
    assert dialog.table.item(last_row, 0).text() == "I03"
    assert dialog.table.item(last_row, 1).text() == "平安金"
    assert dialog.table.item(last_row, 2).text() == "3000"

def test_income_dialog_add_duplicate_id(qtbot, temp_income_db):
    """測試新增收入項目時，若 ID 重複，則不新增並顯示錯誤訊息"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # ID 'I01' 已存在於 temp_income_db 中
    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_income_item(
            dialog=dialog,
            id="I01",  # 已存在
            name="重複項目",
            amount=999
        )
        # ✅ 應該會觸發 warning
        mock_warning.assert_called_once_with(dialog, "錯誤", "收入項目代號 I01 已存在，請輸入其他代號！")

    # ✅ 表格仍為原本 2 筆資料
    assert dialog.table.rowCount() == 2

def test_income_dialog_add_blank_id(qtbot, temp_income_db):
    """測試新增收入項目時，若 ID 為空，則顯示錯誤訊息並不新增"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_income_item(
            dialog=dialog,
            id="   ",  # 空白 ID
            name="空白測試項目",
            amount=100
        )
        # ✅ 預期跳出錯誤訊息
        mock_warning.assert_called_once_with(dialog, "錯誤", "收入項目代號不可為空！")

    # ✅ 表格不應增加資料
    assert dialog.table.rowCount() == 2

def test_income_dialog_add_blank_name(qtbot, temp_income_db):
    """測試新增收入項目時，若名稱為空，則顯示錯誤訊息並不新增"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_add_income_item(
            dialog=dialog,
            id="I03",  # 合法 ID
            name="   ",  # 名稱為空白
            amount=200
        )
        mock_warning.assert_called_once_with(dialog, "錯誤", "請填寫收入項目名稱！")

    # ✅ 表格應維持原本兩筆資料
    assert dialog.table.rowCount() == 2

def test_income_dialog_edit_no_selection(qtbot, temp_income_db):
    """測試未選取任何收入項目時，點擊修改應跳出錯誤訊息"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 確保沒有任何選取
    dialog.table.clearSelection()

    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.edit_income_item()
        mock_warning.assert_called_once_with(dialog, "錯誤", "請選擇要修改的收入項目！")

def test_income_dialog_edit_success(qtbot, temp_income_db):
    """測試成功修改收入項目"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 模擬選取第一列
    dialog.table.selectRow(0)

    # 取得原始 ID（不可變動）
    item_id = dialog.table.item(0, 0).text()

    with patch("app.dialogs.income_dialog.QMessageBox.information") as mock_info:
        # 直接呼叫 confirm_edit_income_item 模擬編輯成功流程
        dialog.confirm_edit_income_item(dialog, item_id, "改名香油", 999)

        # 驗證 UI 表格已更新
        assert dialog.table.item(0, 0).text() == item_id
        assert dialog.table.item(0, 1).text() == "改名香油"
        assert dialog.table.item(0, 2).text() == "999"

        mock_info.assert_called_once_with(dialog, "成功", "收入項目修改成功！")
        
def test_income_dialog_edit_fail_empty_name(qtbot, temp_income_db):
    """測試修改收入項目失敗（名稱為空）"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 模擬選取第一筆資料
    dialog.table.selectRow(0)

    item_id = dialog.table.item(0, 0).text()
    original_name = dialog.table.item(0, 1).text()
    original_amount = dialog.table.item(0, 2).text()

    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.confirm_edit_income_item(dialog, item_id, "", 888)

        # 資料應未變動
        assert dialog.table.item(0, 0).text() == item_id
        assert dialog.table.item(0, 1).text() == original_name
        assert dialog.table.item(0, 2).text() == original_amount

        mock_warning.assert_called_once_with(dialog, "錯誤", "請填寫收入項目名稱！")


def test_income_dialog_delete_fail_no_selection(qtbot, temp_income_db):
    """測試未選取任何項目時刪除，跳出錯誤訊息"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # ❌ 不選取任何列
    dialog.table.clearSelection()

    with patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:
        dialog.delete_income_item()

        mock_warning.assert_called_once_with(dialog, "錯誤", "請選擇要刪除的收入項目！")

def test_income_dialog_delete_success(qtbot, temp_income_db):
    """測試成功刪除已存在的收入項目"""
    from app.dialogs.income_dialog import IncomeSetupDialog

    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 模擬選取第一列 (I01)
    dialog.table.selectRow(0)

    # 準備模擬 QMessageBox
    mock_box = MagicMock()
    mock_box.exec_.return_value = QMessageBox.Yes
    mock_yes_button = object()
    mock_box.clickedButton.return_value = mock_yes_button
    mock_box.addButton.side_effect = lambda label, role: mock_yes_button if label == "是" else object()

    with patch("app.dialogs.income_dialog.QMessageBox", return_value=mock_box), \
         patch("app.dialogs.income_dialog.QMessageBox.information") as mock_info:

        dialog.delete_income_item()

        # 驗證成功刪除
        assert dialog.table.rowCount() == 1
        assert dialog.table.item(0, 0).text() == "I02"
        assert dialog.table.item(0, 1).text() == "補運金"
        assert dialog.table.item(0, 2).text() == "5000"

        mock_info.assert_called_once_with(dialog, "成功", "收入項目刪除成功！")

def test_income_dialog_delete_nonexistent_item(qtbot, temp_income_db):
    """測試刪除不存在的收入項目時跳出錯誤訊息"""
    from app.dialogs.income_dialog import IncomeSetupDialog
    import sqlite3

    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 模擬選取第一列
    dialog.table.selectRow(0)
    item_id = dialog.table.item(0, 0).text()

    # 手動從資料庫刪掉該項目（模擬 DB 不存在）
    conn = sqlite3.connect(str(temp_income_db))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM income_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    # 準備模擬 QMessageBox
    mock_box = MagicMock()
    mock_box.exec_.return_value = QMessageBox.Yes
    mock_yes_button = object()
    mock_box.clickedButton.return_value = mock_yes_button
    mock_box.addButton.side_effect = lambda label, role: mock_yes_button if label == "是" else object()

    with patch("app.dialogs.income_dialog.QMessageBox", return_value=mock_box), \
         patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warning:

        dialog.delete_income_item()

        # 驗證有跳出錯誤訊息
        mock_warning.assert_called_once_with(dialog, "錯誤", "收入項目不存在，無法刪除！")

def test_income_dialog_delete_cancelled(qtbot, temp_income_db):
    """測試使用者選擇「否」後取消刪除收入項目"""
    from app.dialogs.income_dialog import IncomeSetupDialog

    dialog = IncomeSetupDialog(db_path=str(temp_income_db))
    qtbot.addWidget(dialog)

    # 原始資料筆數
    original_row_count = dialog.table.rowCount()

    # 模擬選取第一列
    dialog.table.selectRow(0)

    # 模擬 QMessageBox 行為：點選「否」
    mock_box = MagicMock()
    mock_box.exec_.return_value = QMessageBox.No
    mock_no_button = object()
    mock_box.clickedButton.return_value = mock_no_button
    mock_box.addButton.side_effect = lambda label, role: mock_no_button if label == "否" else object()

    with patch("app.dialogs.income_dialog.QMessageBox", return_value=mock_box), \
         patch("app.dialogs.income_dialog.QMessageBox.information") as mock_info, \
         patch("app.dialogs.income_dialog.QMessageBox.warning") as mock_warn:

        dialog.delete_income_item()

        # 確認沒有刪除（資料筆數不變）
        assert dialog.table.rowCount() == original_row_count

        # 不應跳出成功或錯誤訊息
        mock_info.assert_not_called()
        mock_warn.assert_not_called()