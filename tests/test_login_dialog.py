# tests/test_login_dialog.py
import pytest
from unittest import mock
from PyQt5.QtCore import Qt
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
