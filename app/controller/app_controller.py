import sys
from PyQt5.QtWidgets import QApplication, QDialog
from app.auth.login import LoginDialog
from app.main_window import MainWindow


def run_app():
    app = QApplication(sys.argv)

    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        username = login_dialog.username
        role = login_dialog.role
        main_window = MainWindow(username, role)
        main_window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
