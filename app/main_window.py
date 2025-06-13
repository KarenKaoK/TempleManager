from PyQt5.QtWidgets import QMainWindow, QAction
from app.dialogs.income_dialog import IncomeSetupDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog
from app.dialogs.member_identity_dialog import MemberIdentityDialog
from app.widgets.main_page import MainPageWidget


class MainWindow(QMainWindow):
    def __init__(self, username, role, controller):
        super().__init__()
        self.username = username
        self.role = role
        self.controller = controller  # ✅ 加上這行
        self.setWindowTitle(f"宮廟管理系統 - {role}")
        self.setGeometry(300, 150, 1000, 700)
        self.setup_menu()

    def setup_menu(self):
        menu_bar = self.menuBar()

        category_menu = menu_bar.addMenu("類別設定")
        income_action = QAction("收入項目建檔作業", self)
        expense_action = QAction("支出項目建檔作業", self)
        identity_action = QAction("信眾身份名稱設定", self)
        income_action.triggered.connect(self.open_income_setup)
        expense_action.triggered.connect(self.open_expense_setup)
        identity_action.triggered.connect(self.open_identity_setup)
        category_menu.addAction(income_action)
        category_menu.addAction(expense_action)
        category_menu.addAction(identity_action)

        data_entry_menu = menu_bar.addMenu("資料建檔")
        household_entry_action = QAction("信眾資料建檔", self)
        household_entry_action.triggered.connect(self.open_household_entry)
        data_entry_menu.addAction(household_entry_action)

    def open_income_setup(self):
        self.income_dialog = IncomeSetupDialog()
        self.income_dialog.exec_()

    def open_expense_setup(self):
        self.expense_dialog = ExpenseSetupDialog()
        self.expense_dialog.exec_()

    def open_identity_setup(self):
        self.identity_dialog = MemberIdentityDialog()
        self.identity_dialog.exec_()

    def open_household_entry(self):
        self.main_page = MainPageWidget()  # 👈 這裡很關鍵，要存成屬性
        self.main_page.search_bar.search_triggered.connect(self.perform_search)
        self.setCentralWidget(self.main_page)

    def perform_search(self, keyword):
        print(f"🔍 正在查詢關鍵字: {keyword}")
        results = self.controller.search_households(keyword)
        print(f"查詢結果筆數：{len(results)}")
        for r in results:
            print(r)

        self.main_page.update_household_table(results)

        if results:
            household_id = results[0]["id"]
            self.main_page.fill_head_detail(results[0])

            # 🔥 這裡由 MainWindow 來查 members，結果傳進去
            members = self.controller.get_household_members(household_id)
            self.main_page.update_member_table(members)
            
            # ✅ 顯示統計標籤
            num_adults = sum(1 for m in members if m.get("identity") == "丁")
            num_dependents = sum(1 for m in members if m.get("identity") == "口")
            self.main_page.stats_label.setText(
                f"戶號：{household_id}　戶長：{results[0]['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
            )
