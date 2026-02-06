from PyQt5.QtWidgets import (
    QMainWindow, QAction, QMessageBox, QWidget, QStackedWidget, QDialog
)

from app.dialogs.income_dialog import IncomeSetupDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog
from app.dialogs.member_identity_dialog import MemberIdentityDialog

from app.dialogs.new_household_dialog import NewHouseholdDialog
from app.widgets.main_page import MainPageWidget
from app.widgets.activity_manage_page import ActivityManagePage
from app.widgets.activity_signup_page import ActivitySignupPage





class MainWindow(QMainWindow):
    def __init__(self, username, role, controller):
        super().__init__()
        self.username = username
        self.role = role
        self.controller = controller

        self.setWindowTitle(f"宮廟管理系統 - {role}")
        self.setGeometry(300, 150, 1000, 700)

        # ✅ 中央容器：StackedWidget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ✅ Pages（一定要先宣告）
        self.main_page = None
        self.activity_manage_page = None
        self.activity_signup_page = None

        # ✅ 空白頁
        self._blank_page = QWidget()
        self.stack.addWidget(self._blank_page)
        self.stack.setCurrentWidget(self._blank_page)

        self.setup_menu()

    # -------------------------
    # Helpers
    # -------------------------
    def _show_page(self, page: QWidget):
        if self.stack.indexOf(page) == -1:
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def _back_to_blank(self):
        self.stack.setCurrentWidget(self._blank_page)

    # -------------------------
    # Menu
    # -------------------------
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
        activity_signup_action = QAction("活動報名", self)

        activity_manage_action.triggered.connect(self.open_activity_manage)
        activity_signup_action.triggered.connect(self.open_activity_signup)

        activity_menu.addAction(activity_manage_action)
        activity_menu.addAction(activity_signup_action)  # ✅ 你原本漏掉這行

    # -------------------------
    # Dialogs
    # -------------------------
    def open_income_setup(self):
        dlg = IncomeSetupDialog()
        dlg.exec_()

    def open_expense_setup(self):
        dlg = ExpenseSetupDialog()
        dlg.exec_()

    def open_identity_setup(self):
        dlg = MemberIdentityDialog()
        dlg.exec_()

    # -------------------------
    # Household page
    # -------------------------
    def open_household_entry(self):
        if self.main_page is None:
            self.main_page = MainPageWidget(self.controller)
            self.main_page.search_bar.search_triggered.connect(self.perform_search)
            self.main_page.new_household_triggered.connect(self.open_new_household_dialog)

        self._show_page(self.main_page)

    def perform_search(self, keyword):
        head_result, members = self.controller.search_by_any_name(keyword)

        if head_result:
            head_data = self.controller.format_head_data(head_result)
            self.main_page.update_household_table([head_data])
            self.main_page.fill_head_detail(head_data)
            self.main_page.update_member_table(members)

            num_adults = sum(1 for m in members if m.get("identity") == "丁")
            num_dependents = sum(1 for m in members if m.get("identity") == "口")
            self.main_page.stats_label.setText(
                f"戶號：{head_data['id']}　戶長：{head_data['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
            )
        else:
            QMessageBox.information(self, "查無結果", f"找不到關鍵字：{keyword}")

    def open_new_household_dialog(self):
        dialog = NewHouseholdDialog(self.controller, self)
        if dialog.exec_() == QDialog.Accepted:
            payload = dialog.get_data()
            try:
                person_id, household_id = self.controller.create_household(payload)
                QMessageBox.information(self, "成功", f"已新增戶籍\n戶號：{household_id}\n戶長ID：{person_id}")

                # 建議：新增成功後刷新主畫面戶籍清單（看你目前怎麼做 refresh）
                if hasattr(self, "main_page") and self.main_page:
                    self.main_page.refresh_all_panels()  # 若你有這支
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"新增戶籍失敗：{e}")

    # -------------------------
    # Activity pages
    # -------------------------
    def open_activity_manage(self):
        if self.activity_manage_page is None:
            self.activity_manage_page = ActivityManagePage(self.controller)

            # 返回/關閉 → 回空白頁（或你要回戶籍頁也可以）
            self.activity_manage_page.request_close.connect(self._back_to_blank)

            # 從管理頁跳到報名頁（ActivityManagePage 要有 request_open_signup signal）
            if hasattr(self.activity_manage_page, "request_open_signup"):
                self.activity_manage_page.request_open_signup.connect(self.open_activity_signup)

        self._show_page(self.activity_manage_page)

    def open_activity_signup(self, activity_data=None):
        if self.activity_signup_page is None:
            self.activity_signup_page = ActivitySignupPage(self.controller)
            self.activity_signup_page.request_back_to_manage.connect(self.open_activity_manage)

        if activity_data:
            self.activity_signup_page.set_activity(activity_data)

        self._show_page(self.activity_signup_page)
