import sys
import sqlite3
import bcrypt
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from login_ui import Ui_Dialog  # 來自 Qt Designer 轉換的 UI
from main import MainWindow  # 🔹 匯入主畫面

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


class LoginDialog(QDialog):
    """登入視窗"""
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # 設定按鈕事件
        self.ui.pushButtonLogin.clicked.connect(self.check_login)

    def check_login(self):
        """驗證帳號密碼並顯示權限"""
        username = self.ui.lineEditUsername.text()
        password = self.ui.lineEditPassword.text()

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user[0]):
            role = user[1]
            QMessageBox.information(self, "登入成功", f"登入成功，歡迎 {role} 使用！")

            self.accept()  # 關閉登入視窗
            self.open_main_window(username, role)  # 開啟主畫面
        else:
            QMessageBox.warning(self, "登入失敗", "帳號或密碼錯誤")

    def open_main_window(self, username, role):
        """開啟主畫面，並傳遞登入資訊"""
        self.main_window = MainWindow(username, role)  # 🔹 傳遞 username & role
        self.main_window.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 顯示登入視窗
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        sys.exit(app.exec_())  # 🔹 確保程式不會異常結束
