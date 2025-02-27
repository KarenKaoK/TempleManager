import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from income_dialog import IncomeSetupDialog  # 🔹 確保正確載入 IncomeSetupDialog

class MainWindow(QMainWindow):
    """主視窗"""
    def __init__(self, username, role):
        super().__init__()

        self.username = username
        self.role = role

        self.setWindowTitle("宮廟管理系統")
        self.setGeometry(300, 150, 800, 600)

        # 建立選單
        menu_bar = self.menuBar()
        category_menu = menu_bar.addMenu("類別設定")

        # 建立選單項目
        income_action = QAction("收入項目建檔作業", self)
        income_action.triggered.connect(self.open_income_setup)

        category_menu.addAction(income_action)

    def open_income_setup(self):
        """開啟收入項目建檔作業視窗"""
        self.income_dialog = IncomeSetupDialog()
        self.income_dialog.exec_()  # 🔹 確保彈出視窗

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow("測試用戶", "測試角色")
    main_window.show()
    sys.exit(app.exec_())
