import pytest
import sqlite3
from unittest import mock
from PyQt5.QtWidgets import QApplication
from app.dialogs.member_identity_dialog import MemberIdentityDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QMessageBox

# 測試 1：有資料時正確載入到表格
def test_load_data_with_records(qtbot):
    test_data = [(1, '會員'), (2, '志工')]
    
    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect:
        mock_cursor = mock.Mock()
        mock_cursor.fetchall.return_value = test_data
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog = MemberIdentityDialog()
        qtbot.addWidget(dialog)
        dialog.load_data()

        assert dialog.table.rowCount() == len(test_data)
        for i, (_, name) in enumerate(test_data):
            assert dialog.table.item(i, 0).text() == name

# 測試 2：無資料時表格清空顯示
def test_load_data_with_empty_table(qtbot):
    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect:
        mock_cursor = mock.Mock()
        mock_cursor.fetchall.return_value = []
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog = MemberIdentityDialog()
        qtbot.addWidget(dialog)
        dialog.load_data()

        assert dialog.table.rowCount() == 0

# 測試 3：點擊新增後顯示新增對話框
def test_click_add_button_shows_dialog(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    dialog_shown = {}

    class FakeDialog:
        def __init__(self, parent=None):
            dialog_shown['opened'] = True
        def setWindowTitle(self, title): pass
        def setLayout(self, layout): pass
        def exec_(self): return
        def reject(self): pass  # 加上這行，模擬 dialog 有 reject 方法

    monkeypatch.setattr("app.dialogs.member_identity_dialog.QDialog", FakeDialog)

    dialog.btn_add.click()
    assert dialog_shown.get("opened", False) is True

# 測試 4：新增身份名稱成功時寫入資料庫並顯示成功訊息
def test_confirm_add_identity_success(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    mock_dialog = mock.Mock()

    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect, \
         mock.patch("app.dialogs.member_identity_dialog.QMessageBox.information") as mock_info:

        mock_cursor = mock.Mock()
        mock_cursor.fetchall.return_value = []  # 避免 load_data 出錯
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog.confirm_add_identity(mock_dialog, "新身份")

        # 修正這一行！
        mock_cursor.execute.assert_any_call(
            "INSERT INTO member_identity (name) VALUES (?)", ("新身份",)
        )

        mock_connect.return_value.commit.assert_called_once()
        mock_info.assert_called_once_with(dialog, "成功", "身份名稱新增成功！")
        mock_dialog.accept.assert_called_once()



# 測試 5：新增身份名稱為空白時跳出錯誤訊息
def test_confirm_add_identity_empty_name(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    mock_dialog = mock.Mock()

    with mock.patch("app.dialogs.member_identity_dialog.QMessageBox.warning") as mock_warn:
        dialog.confirm_add_identity(mock_dialog, "   ")  # 空白字串
        mock_warn.assert_called_once_with(dialog, "錯誤", "請輸入身份名稱！")
        mock_dialog.accept.assert_not_called()

# 測試 6：新增重複的身份名稱時跳出錯誤訊息
def test_confirm_add_identity_duplicate_name(qtbot):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    mock_dialog = mock.Mock()

    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect, \
         mock.patch("app.dialogs.member_identity_dialog.QMessageBox.warning") as mock_warn:

        mock_cursor = mock.Mock()
        mock_cursor.execute.side_effect = sqlite3.IntegrityError
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog.confirm_add_identity(mock_dialog, "會員")

        mock_warn.assert_called_once_with(dialog, "錯誤", "身份名稱已存在！")
        mock_dialog.accept.assert_not_called() 

# 測試 7：未選取列時點擊修改跳出錯誤訊息
def test_edit_identity_without_selection(qtbot):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    with mock.patch("app.dialogs.member_identity_dialog.QMessageBox.warning") as mock_warn:
        dialog.table.setRowCount(0)  # 沒有選取任何列
        dialog.edit_identity()
        mock_warn.assert_called_once_with(dialog, "錯誤", "請選擇要修改的身份名稱！")

# 測試 8：點擊修改後顯示編輯對話框並帶入原值
def test_edit_identity_opens_dialog_with_current_value(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    dialog.table.setRowCount(1)
    dialog.table.setItem(0, 0, QTableWidgetItem("原身份"))
    dialog.table.selectRow(0)

    dialog_shown = {"opened": False, "value": None}

    class FakeDialog:
        def __init__(self, parent=None):
            dialog_shown["opened"] = True
        def setWindowTitle(self, title): pass
        def setLayout(self, layout): pass
        def exec_(self): return
        def reject(self): pass

    class FakeLineEdit(QLineEdit):
        def __init__(self, val):
            super().__init__()
            dialog_shown["value"] = val

    monkeypatch.setattr("app.dialogs.member_identity_dialog.QDialog", FakeDialog)
    monkeypatch.setattr("app.dialogs.member_identity_dialog.QLineEdit", FakeLineEdit)

    dialog.edit_identity()
    assert dialog_shown["opened"] is True
    assert dialog_shown["value"] == "原身份"

# 測試 9：修改身份名稱成功時更新資料並顯示成功訊息
def test_confirm_edit_identity_success(qtbot):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    mock_dialog = mock.Mock()

    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect, \
         mock.patch("app.dialogs.member_identity_dialog.QMessageBox.information") as mock_info:

        mock_cursor = mock.Mock()
        mock_cursor.fetchall.return_value = []
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog.confirm_edit_identity(mock_dialog, "原身份", "新身份")

        # ✅ 修正這裡
        mock_cursor.execute.assert_any_call(
            "UPDATE member_identity SET name = ? WHERE name = ?", ("新身份", "原身份")
        )

        mock_connect.return_value.commit.assert_called_once()
        mock_info.assert_called_once_with(dialog, "成功", "身份名稱修改成功！")
        mock_dialog.accept.assert_called_once()


# 測試 10：修改身份名稱為空白時跳出錯誤訊息
def test_confirm_edit_identity_empty_name(qtbot):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    mock_dialog = mock.Mock()

    with mock.patch("app.dialogs.member_identity_dialog.QMessageBox.warning") as mock_warn:
        dialog.confirm_edit_identity(mock_dialog, "原身份", "   ")  # 空白新值
        mock_warn.assert_called_once_with(dialog, "錯誤", "請輸入新身份名稱！")
        mock_dialog.accept.assert_not_called()

# 測試 11：未選取列時點擊刪除跳出錯誤訊息
def test_delete_identity_without_selection(qtbot):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    with mock.patch("app.dialogs.member_identity_dialog.QMessageBox.warning") as mock_warn:
        dialog.table.setRowCount(0)  # 無資料也無選取
        dialog.delete_identity()
        mock_warn.assert_called_once_with(dialog, "錯誤", "請選擇要刪除的身份名稱！")

# 測試 12：點擊刪除後顯示確認訊息框
def test_delete_identity_shows_confirmation(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    dialog.table.setRowCount(1)
    dialog.table.setItem(0, 0, QTableWidgetItem("測試身份"))
    dialog.table.selectRow(0)

    captured_box = {}

    class FakeMessageBox:
        class StandardButton:
            Yes = QMessageBox.Yes
            No = QMessageBox.No

        def __init__(self, parent=None):
            self.text_value = ""
            captured_box["instance"] = self  # 把目前實例記下來
        def setWindowTitle(self, title): pass
        def setText(self, text): self.text_value = text
        def setStandardButtons(self, buttons): pass
        def button(self, button): return mock.Mock()
        def exec_(self): return QMessageBox.No

    monkeypatch.setattr("app.dialogs.member_identity_dialog.QMessageBox", FakeMessageBox)

    dialog.delete_identity()

    # 這裡用儲存的實例去斷言 text
    assert "測試身份" in captured_box["instance"].text_value


# 測試 13：刪除身份名稱成功時更新資料並顯示成功訊息
def test_delete_identity_success(qtbot, monkeypatch):
    dialog = MemberIdentityDialog()
    qtbot.addWidget(dialog)

    dialog.table.setRowCount(1)
    dialog.table.setItem(0, 0, QTableWidgetItem("刪除身份"))
    dialog.table.selectRow(0)

    with mock.patch("app.dialogs.member_identity_dialog.sqlite3.connect") as mock_connect, \
         mock.patch("app.dialogs.member_identity_dialog.QMessageBox.exec_", return_value=QMessageBox.Yes), \
         mock.patch("app.dialogs.member_identity_dialog.QMessageBox.information") as mock_info:

        mock_cursor = mock.Mock()
        mock_cursor.fetchall.return_value = []  # ✅ 加上這行避免 TypeError
        mock_connect.return_value.cursor.return_value = mock_cursor

        dialog.delete_identity()

        # 確認 SQL 執行正確
        mock_cursor.execute.assert_any_call("DELETE FROM member_identity WHERE name = ?", ("刪除身份",))
        mock_info.assert_called_once_with(dialog, "成功", "身份名稱刪除成功！")
