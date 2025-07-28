from PyQt5.QtWidgets import QMainWindow, QAction, QMessageBox
from app.dialogs.income_dialog import IncomeSetupDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog
from app.dialogs.member_identity_dialog import MemberIdentityDialog
from app.dialogs.household_dialog import NewHouseholdDialog
from app.widgets.main_page import MainPageWidget
from app.widgets.activity_manage_page import ActivityManagePage

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, QTabWidget, QTableWidgetItem,
    QDialog, QMessageBox, QComboBox, QDateEdit, QCheckBox
)

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

        activity_menu = menu_bar.addMenu("活動頁面")
        activity_manage_action = QAction("活動管理", self)
        activity_manage_action.triggered.connect(self.open_activity_manage)
        activity_menu.addAction(activity_manage_action)

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
        self.main_page = MainPageWidget(self.controller)  # 👈 這裡很關鍵，要存成屬性
        self.main_page.search_bar.search_triggered.connect(self.perform_search)
        self.main_page.new_household_triggered.connect(self.open_new_household_dialog)
        self.setCentralWidget(self.main_page)

    def perform_search(self, keyword):
        print(f"🔍 正在查詢關鍵字: {keyword}")

        # 改為新的通用查詢：可能是戶長，也可能是戶員
        head_result, members = self.controller.search_by_any_name(keyword)
        
        if head_result:
            print("✅ 查到戶長或戶員，戶長資訊如下：")
            print(dict(head_result))

            # 格式化欄位（tuple → dict），假設你已有這個方法
            head_data = self.controller.format_head_data(head_result)

            # 更新上方戶長表格（只顯示一筆）
            self.main_page.update_household_table([head_data])
            self.main_page.fill_head_detail(head_data)

            # 更新下方戶員表格
            self.main_page.update_member_table(members)

            # 統計成員身份
            num_adults = sum(1 for m in members if m.get("identity") == "丁")
            num_dependents = sum(1 for m in members if m.get("identity") == "口")
            self.main_page.stats_label.setText(
                f"戶號：{head_data['id']}　戶長：{head_data['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
            )
        else:
            print("❌ 查無資料")
            QMessageBox.information(self, "查無結果", f"找不到關鍵字：{keyword}")

    def open_new_household_dialog(self):
        dialog = NewHouseholdDialog(self.controller)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.controller.insert_household(data)
            QMessageBox.information(self, "新增成功", f"已新增戶長：{data['head_name']}")
            self.perform_search(data["head_name"])

    def open_activity_manage(self):
        self.activity_page = ActivityManagePage(self.controller)
        self.setCentralWidget(self.activity_page)

    