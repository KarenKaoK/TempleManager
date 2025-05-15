import sqlite3
import bcrypt
from PyQt5.QtWidgets import QDialog, QMessageBox
from app.dialogs.login_ui import Ui_Dialog  
from app.config import DB_NAME

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

        # 初始化登入結果
        self.username = None
        self.role = None

    def check_login(self):
        """驗證帳號密碼並設定登入資訊"""
        username = self.ui.lineEditUsername.text()
        password = self.ui.lineEditPassword.text()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            stored_hash = user[0]
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode("utf-8")

            if bcrypt.checkpw(password.encode(), stored_hash):
                self.username = username
                self.role = user[1]
                QMessageBox.information(self, "登入成功", f"登入成功，歡迎 {self.role} 使用！")
                self.accept()  # 關閉登入視窗
                return

        QMessageBox.warning(self, "登入失敗", "帳號或密碼錯誤")
