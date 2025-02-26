import sys
import sqlite3
import bcrypt
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QMainWindow
from login_ui import Ui_Dialog  # Qt Designer 轉換的 UI

class LoginDialog(QDialog):
    """登入視窗"""
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # 設定按鈕事件
        self.ui.pushButtonLogin.clicked.connect(self.check_login)

    def check_login(self):
        """驗證帳號密碼"""
        username = self.ui.lineEdiUsername.text()
        password = self.ui.lineEditPassword.text()

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode(), user[0]):
            QMessageBox.information(self, "登入成功", "歡迎使用系統！")
            self.accept()  # 關閉登入視窗
        else:
            QMessageBox.warning(self, "登入失敗", "帳號或密碼錯誤")

class MainWindow(QMainWindow):
    """主視窗"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("宮廟管理系統")
        self.setGeometry(300, 150, 800, 600)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 顯示登入視窗
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())
