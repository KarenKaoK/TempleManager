from PyQt5.QtWidgets import (
    QMainWindow, QAction, QMessageBox, QWidget, QStackedWidget, QDialog,
    QHBoxLayout, QPushButton, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt

from app.dialogs.income_dialog import IncomeSetupDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog
from app.dialogs.member_identity_dialog import MemberIdentityDialog

from app.dialogs.new_household_dialog import NewHouseholdDialog
from app.widgets.main_page import MainPageWidget
from app.widgets.activity_manage_page import ActivityManagePage
from app.widgets.activity_signup_page import ActivitySignupPage
from app.dialogs.income_expense_dialog import IncomeExpenseDialog

class MainWindow(QMainWindow):
    def __init__(self, username, role, controller):
        super().__init__()
        self.username = username
        self.role = role
        self.controller = controller

        self.setWindowTitle(f"宮廟管理系統 - {role}")
        self.setGeometry(300, 150, 1000, 700)

        # ✅ 主容器（垂直佈局：StackedWidget + 底部按鈕列）
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ✅ 中央容器：StackedWidget
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # ✅ 底部按鈕列
        self.bottom_bar = QFrame()
        self.bottom_bar.setStyleSheet("border-top: 1px solid #E6D8C7; background: #FAF5EF;")
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        bottom_layout.addStretch()  # 推到右邊

        logout_btn = QPushButton("登出")
        logout_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px; padding: 8px 22px;
                background-color: #F29B38; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #E08A28; }
        """)
        logout_btn.clicked.connect(self._on_logout)

        close_btn = QPushButton("關閉程式")
        close_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px; padding: 8px 22px;
                background-color: #C0392B; color: white;
                border: none; border-radius: 6px;
            }
            QPushButton:hover { background-color: #A93226; }
        """)
        close_btn.clicked.connect(self._on_close)

        bottom_layout.addWidget(logout_btn)
        bottom_layout.addWidget(close_btn)
        layout.addWidget(self.bottom_bar)

        self.setCentralWidget(central)

        # ✅ Pages（一定要先宣告）
        self.main_page = None
        self.activity_manage_page = None
        self.activity_signup_page = None

        # ✅ 空白頁
        self._blank_page = QWidget()
        self.stack.addWidget(self._blank_page)
        self.stack.setCurrentWidget(self._blank_page)

        self.setup_menu()
        
        # ✅ 自動進入「信眾資料建檔」（UX 優化）
        self.open_household_entry()

    # -------------------------
    # Helpers
    # -------------------------
    def _show_page(self, page: QWidget):
        if self.stack.indexOf(page) == -1:
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self._sync_bottom_bar_visibility(page)

    def _sync_bottom_bar_visibility(self, page: QWidget):
        """活動頁改用頁內「關閉返回」，隱藏全域底部列避免重複操作。"""
        hide_for_activity_pages = page in (self.activity_manage_page, self.activity_signup_page)
        self.bottom_bar.setVisible(not hide_for_activity_pages)

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
        activity_menu.addAction(activity_signup_action)

        # -------------------------
        # 收支管理
        # -------------------------
        finance_menu = menu_bar.addMenu("收支管理")
        income_entry_action = QAction("收入資料登錄作業", self)
        expense_entry_action = QAction("支出資料登錄作業", self)
        
        income_entry_action.triggered.connect(lambda: self.open_income_expense_dialog(0))
        expense_entry_action.triggered.connect(lambda: self.open_income_expense_dialog(1))
        
        finance_menu.addAction(income_entry_action)
        finance_menu.addAction(expense_entry_action)

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
            self.main_page.search_bar.show_all_triggered.connect(lambda: self.main_page.refresh_all_panels())
            self.main_page.new_household_triggered.connect(self.open_new_household_dialog)

        self._show_page(self.main_page)

    def perform_search(self, keyword):
        if not keyword:
            self.main_page.refresh_all_panels()
            return

        people = self.controller.search_people_unified(keyword)

        if people:
            self.main_page.update_household_table(people)
            # 自動載入搜尋結果的第一個人
            first = people[0]
            self.main_page._load_household(first['household_id'], first['id'])
        else:
            QMessageBox.information(self, "查無結果", f"找不到關鍵字：{keyword}")

    def open_new_household_dialog(self):
        dialog = NewHouseholdDialog(self.controller, self)

        if dialog.exec_() == QDialog.Accepted:
            
            person_id = getattr(dialog, "created_person_id", None)
            household_id = getattr(dialog, "created_household_id", None)

            if not person_id or not household_id:
                QMessageBox.warning(self, "錯誤", "建立成功但未取得 person_id / household_id，請檢查 Dialog 流程")
                return

            QMessageBox.information(
                self,
                "成功",
                f"已新增戶籍\n戶號：{household_id}\n戶長ID：{person_id}"
            )

            if self.main_page:
                self.main_page.refresh_all_panels(
                    select_household_id=household_id,
                    select_head_person_id=person_id
                )


    # -------------------------
    # Activity pages
    # -------------------------
    def open_activity_manage(self):
        if self.activity_manage_page is None:
            self.activity_manage_page = ActivityManagePage(self.controller)

            # 返回/關閉 → 回主頁（信眾資料建檔）
            self.activity_manage_page.request_close.connect(self.open_household_entry)

            # 從管理頁跳到報名頁（ActivityManagePage 要有 request_open_signup signal）
            if hasattr(self.activity_manage_page, "request_open_signup"):
                self.activity_manage_page.request_open_signup.connect(self.open_activity_signup)

        self._show_page(self.activity_manage_page)

    def open_activity_signup(self, activity_data=None):
        if self.activity_signup_page is None:
            self.activity_signup_page = ActivitySignupPage(self.controller)
            self.activity_signup_page.request_back_to_manage.connect(self.open_activity_manage)
            self.activity_signup_page.request_close.connect(self.open_household_entry)

        if activity_data:
            self.activity_signup_page.set_activity(activity_data)

        self._show_page(self.activity_signup_page)

    def open_income_expense_dialog(self, initial_tab=0):
        # 0=Income, 1=Expense
        dialog = IncomeExpenseDialog(self.controller, self, initial_tab)
        dialog.exec_()

    # -------------------------
    # Logout / Close
    # -------------------------
    def _on_logout(self):
        """登出：關閉主視窗，回到登入畫面"""
        reply = QMessageBox.question(
            self, "登出確認", "確定要登出嗎？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._is_logout = True
            self.close()

    def _on_close(self):
        """關閉程式：彈出確認框避免誤觸"""
        reply = QMessageBox.question(
            self, "關閉程式", "確定要關閉整個程式嗎？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._is_logout = False
            self.close()
