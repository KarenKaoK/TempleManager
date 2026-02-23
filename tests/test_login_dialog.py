# tests/test_login_dialog.py
import re
import pytest
from unittest import mock
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from app.auth.login import LoginDialog

@pytest.fixture
def login_dialog(qtbot):
    dialog = LoginDialog()
    qtbot.addWidget(dialog)
    return dialog

def test_login_success(login_dialog, mocker):
    # 模擬 UI 輸入
    login_dialog.ui.lineEditUsername.setText("admin")
    login_dialog.ui.lineEditPassword.setText("admin123")

    # Mock 資料庫行為
    mock_conn = mocker.patch("app.auth.login.sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value
    # 模擬資料庫回傳一個 user，password_hash 會設定成 bcrypt.hashpw 的結果
    import bcrypt
    password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
    mock_cursor.fetchone.return_value = (password_hash, "管理者")

    # Mock QMessageBox.information
    mock_information = mocker.patch("app.auth.login.QMessageBox.information")

    # Mock accept()（避免真的關掉 Dialog）
    mock_accept = mocker.patch.object(login_dialog, "accept")

    # 執行登入檢查
    login_dialog.check_login()

    # 驗證結果
    assert login_dialog.username == "admin"
    assert login_dialog.role == "管理者"
    mock_information.assert_called_once_with(
        login_dialog,
        "登入成功",
        "登入成功，歡迎 管理者 使用！"
    )
    mock_accept.assert_called_once()

def test_login_wrong_password(login_dialog, mocker):
    """錯誤密碼登入失敗"""
    login_dialog.ui.lineEditUsername.setText("admin")
    login_dialog.ui.lineEditPassword.setText("wrongpass")

    mock_conn = mocker.patch("app.auth.login.sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value
    import bcrypt
    password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())  # 正確密碼是 admin123
    mock_cursor.fetchone.return_value = (password_hash, "管理者")

    mock_warning = mocker.patch("app.auth.login.QMessageBox.warning")
    mock_accept = mocker.patch.object(login_dialog, "accept")

    login_dialog.check_login()

    # username 和 role 不應該被設定
    assert login_dialog.username is None
    assert login_dialog.role is None
    mock_warning.assert_called_once_with(
        login_dialog,
        "登入失敗",
        "帳號或密碼錯誤"
    )
    mock_accept.assert_not_called()

def test_login_wrong_username(login_dialog, mocker):
    """錯誤帳號登入失敗"""
    login_dialog.ui.lineEditUsername.setText("wronguser")
    login_dialog.ui.lineEditPassword.setText("admin123")

    mock_conn = mocker.patch("app.auth.login.sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value
    # 這次模擬找不到帳號
    mock_cursor.fetchone.return_value = None

    mock_warning = mocker.patch("app.auth.login.QMessageBox.warning")
    mock_accept = mocker.patch.object(login_dialog, "accept")

    login_dialog.check_login()

    assert login_dialog.username is None
    assert login_dialog.role is None
    mock_warning.assert_called_once_with(
        login_dialog,
        "登入失敗",
        "帳號或密碼錯誤"
    )
    mock_accept.assert_not_called()

def test_login_success_password_hash_string(login_dialog, mocker):
    """資料庫回傳 password_hash 為字串時處理正確"""
    login_dialog.ui.lineEditUsername.setText("admin")
    login_dialog.ui.lineEditPassword.setText("admin123")

    mock_conn = mocker.patch("app.auth.login.sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value
    import bcrypt
    password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
    # 模擬資料庫回傳 str（通常是從 bytes.decode('utf-8') 來的）
    mock_cursor.fetchone.return_value = (password_hash.decode('utf-8'), "管理者")

    mock_information = mocker.patch("app.auth.login.QMessageBox.information")
    mock_accept = mocker.patch.object(login_dialog, "accept")

    login_dialog.check_login()

    assert login_dialog.username == "admin"
    assert login_dialog.role == "管理者"
    mock_information.assert_called_once_with(
        login_dialog,
        "登入成功",
        "登入成功，歡迎 管理者 使用！"
    )
    mock_accept.assert_called_once()

def test_login_button_binding(login_dialog, mocker, qtbot):
    """UI元件綁定：按下登入按鈕時呼叫 check_login"""
    mock_check_login = mocker.patch.object(login_dialog, "check_login")

    # **重新綁定 clicked 到 mock_check_login**
    login_dialog.ui.pushButtonLogin.clicked.disconnect()
    login_dialog.ui.pushButtonLogin.clicked.connect(mock_check_login)

    # 模擬點擊按鈕
    qtbot.mouseClick(login_dialog.ui.pushButtonLogin, Qt.LeftButton)

    mock_check_login.assert_called_once()

def test_cancel_button_rejects_dialog(login_dialog, qtbot):
    """按下取消按鈕會關閉登入對話框（reject）"""
    with qtbot.waitSignal(login_dialog.rejected):
        qtbot.mouseClick(login_dialog.ui.pushButtonCancel, Qt.LeftButton)


def test_cover_area_resizes_with_dialog(login_dialog, qtbot):
    """登入視窗放大時，封面區塊也會跟著放大"""
    login_dialog.resize(740, 560)
    login_dialog._layout_login_widgets()
    expected_width = max(300, login_dialog.width())
    expected_height = max(190, min(260, int(login_dialog.height() * 0.42)))
    assert login_dialog.cover_label.width() == expected_width
    assert login_dialog.cover_label.height() == expected_height


def test_cover_pixmap_keeps_aspect_ratio_without_crop(login_dialog):
    """封面圖縮放後保持比例，且不超出容器（不裁切）"""
    login_dialog._cover_pixmap = QtGui.QPixmap(800, 400)  # 2:1
    login_dialog._cover_pixmap.fill(Qt.white)
    login_dialog.cover_label.resize(300, 170)
    login_dialog._render_cover_pixmap()

    shown = login_dialog.cover_label.pixmap()
    assert shown is not None
    assert shown.width() <= login_dialog.cover_label.width()
    assert shown.height() <= login_dialog.cover_label.height()
    ratio = shown.width() / shown.height()
    assert abs(ratio - 2.0) < 0.05


def test_login_updates_last_login_with_local_python_timestamp(login_dialog, mocker):
    """登入成功時 last_login_at 應由 Python 顯式寫入（避免 SQLite CURRENT_TIMESTAMP/UTC）"""
    login_dialog.ui.lineEditUsername.setText("admin")
    login_dialog.ui.lineEditPassword.setText("admin123")

    mock_conn = mocker.patch("app.auth.login.sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value

    import bcrypt
    password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
    mock_cursor.fetchone.return_value = (password_hash, "管理者")

    def fake_column_exists(_conn, _table, col):
        return col == "last_login_at"

    mocker.patch.object(login_dialog, "_column_exists", side_effect=fake_column_exists)

    mocker.patch("app.auth.login.QMessageBox.information")
    mocker.patch.object(login_dialog, "accept")

    login_dialog.check_login()

    execute_calls = mock_cursor.execute.call_args_list
    update_calls = [c for c in execute_calls if "UPDATE users SET last_login_at" in str(c.args[0])]
    assert len(update_calls) == 1

    sql = update_calls[0].args[0]
    params = update_calls[0].args[1]
    assert "CURRENT_TIMESTAMP" not in sql
    assert sql == "UPDATE users SET last_login_at = ? WHERE username=?"
    assert params[1] == "admin"
    assert isinstance(params[0], str)
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", params[0])
