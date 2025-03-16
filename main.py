import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction

class MainWindow(QMainWindow):
    """主視窗"""
    def __init__(self, username, role):
        super().__init__()

        self.username = username
        self.role = role

        self.setWindowTitle("宮廟管理系統")
        self.setGeometry(300, 150, 800, 600)

       
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow("測試用戶", "測試角色")
    main_window.show()
    sys.exit(app.exec_())
