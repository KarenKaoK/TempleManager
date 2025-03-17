import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from income_dialog import IncomeSetupDialog  # 🔹 確保正確載入 IncomeSetupDialog
from expense_dialog import ExpenseSetupDialog
from member_identity_dialog import MemberIdentityDialog


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
        expense_action = QAction("支出項目建檔作業", self)
        identity_action = QAction("信眾身份名稱設定", self)


        # 綁定選單項目點擊事件
        income_action.triggered.connect(self.open_income_setup)
        expense_action.triggered.connect(self.open_expense_setup)
        identity_action.triggered.connect(self.open_identity_setup) 

        category_menu.addAction(income_action)
        category_menu.addAction(expense_action) 
        category_menu.addAction(identity_action)

    def open_income_setup(self):
        """開啟收入項目建檔作業視窗"""
        self.income_dialog = IncomeSetupDialog()
        self.income_dialog.exec_()  

    def open_expense_setup(self):
        """開啟支出項目建檔作業視窗"""
        self.expense_dialog = ExpenseSetupDialog()  # ✅ 連接到 `expense_dialog.py`
        self.expense_dialog.exec_()

    def open_identity_setup(self):
        """開啟信眾身份設定作業視窗"""
        self.identity_dialog = MemberIdentityDialog()  
        self.identity_dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow("測試用戶", "測試角色")
    main_window.show()
    sys.exit(app.exec_())
