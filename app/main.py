# app/main.py
import sys
from PyQt5.QtWidgets import QApplication, QDialog
from app.controller.app_controller import AppController
from app.auth.login import LoginDialog
from app.main_window import MainWindow

def run_app():
    app = QApplication(sys.argv)

    while True:
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            break  # 使用者取消登入 → 結束程式

        username = login_dialog.username
        role = login_dialog.role
        controller = AppController()
        main_window = MainWindow(username, role, controller)
        main_window._is_logout = False
        main_window.show()
        app.exec_()

        # 檢查是否為「登出」→ 回到登入畫面；否則直接結束
        if not getattr(main_window, '_is_logout', False):
            break

    sys.exit(0)

if __name__ == "__main__":
    run_app()
