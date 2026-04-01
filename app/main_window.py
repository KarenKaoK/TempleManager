from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMessageBox, QWidget, QStackedWidget, QDialog,
    QHBoxLayout, QPushButton, QVBoxLayout, QFrame, QInputDialog, QLineEdit
)
from PyQt5.QtCore import QEvent, QTimer, Qt
import time

from app.dialogs.income_dialog import IncomeSetupDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog
from app.dialogs.member_identity_dialog import MemberIdentityDialog

from app.dialogs.new_household_dialog import NewHouseholdDialog
from app.widgets.main_page import MainPageWidget
from app.widgets.activity_manage_page import ActivityManagePage
from app.widgets.activity_signup_page import ActivitySignupPage
from app.widgets.lighting_signup_page import LightingSignupPage
from app.dialogs.income_expense_dialog import IncomeExpensePage
from app.dialogs.finance_report_dialog import FinanceReportPage
from app.dialogs.lighting_setup_dialog import LightingSetupDialog
from app.dialogs.account_management_dialog import AccountManagementDialog
from app.dialogs.cover_settings_dialog import CoverSettingsDialog
from app.dialogs.backup_settings_dialog import BackupSettingsDialog
from app.dialogs.report_schedule_settings_dialog import ReportScheduleSettingsDialog
from app.dialogs.system_log_viewer_dialog import SystemLogViewerDialog
from app.logging import log_system
from app.auth.permissions import (
    can_access_finance_report,
    can_manage_accounts,
    can_view_expense_entry,
)


class MainWindow(QMainWindow):
    def __init__(self, username, role, controller):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.username = username
        self.role = role
        self.operator_name = username
        self.controller = controller
        self.font_manager = getattr(QApplication.instance(), "font_manager", None)
        self._last_activity_ts = time.monotonic()
        self._idle_filter_installed = False

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
        self.lighting_signup_page = None
        self.income_expense_page = None
        self.finance_report_page = None
        self.finance_report_action = None
        self.income_entry_action = None
        self.expense_entry_action = None

        # ✅ 空白頁
        self._blank_page = QWidget()
        self.stack.addWidget(self._blank_page)
        self.stack.setCurrentWidget(self._blank_page)

        self.setup_menu()
        self._setup_idle_logout()
        
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
        hide_for_activity_pages = page in (
            self.activity_manage_page,
            self.activity_signup_page,
            self.lighting_signup_page,
            self.income_expense_page,
            self.finance_report_page,
        )
        self.bottom_bar.setVisible(not hide_for_activity_pages)

    def _back_to_blank(self):
        self.stack.setCurrentWidget(self._blank_page)

    # -------------------------
    # Menu
    # -------------------------
    def setup_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

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
        # 安燈管理（插在活動頁面與收支管理之間）
        # -------------------------
        lighting_menu = menu_bar.addMenu("安燈管理")
        lighting_setup_action = QAction("安燈設定", self)
        lighting_signup_action = QAction("安燈報名", self)
        lighting_setup_action.triggered.connect(self.open_lighting_setup)
        lighting_signup_action.triggered.connect(self.open_lighting_signup)
        lighting_menu.addAction(lighting_setup_action)
        lighting_menu.addAction(lighting_signup_action)

        # -------------------------
        # 收支管理
        # -------------------------
        finance_menu = menu_bar.addMenu("收支管理")
        self.income_entry_action = QAction("收入資料登錄作業", self)
        self.expense_entry_action = None
        
        self.income_entry_action.triggered.connect(lambda: self.open_income_expense_page(0))
        finance_menu.addAction(self.income_entry_action)

        if can_view_expense_entry(self.role):
            self.expense_entry_action = QAction("支出資料登錄作業", self)
            self.expense_entry_action.triggered.connect(lambda: self.open_income_expense_page(1))
            finance_menu.addAction(self.expense_entry_action)

        if self._can_access_finance_report():
            finance_report_menu = menu_bar.addMenu("財務會計")
            self.finance_report_action = QAction("會計彙整報表", self)
            self.finance_report_action.triggered.connect(self.open_finance_report_page)
            finance_report_menu.addAction(self.finance_report_action)

        if self._can_manage_accounts():
            system_menu = menu_bar.addMenu("系統管理")
            account_action = QAction("帳號管理", self)
            cover_action = QAction("封面設定", self)
            backup_action = QAction("資料備份", self)
            report_schedule_action = QAction("報表排程設定", self)
            system_log_action = QAction("系統日誌", self)
            account_action.triggered.connect(self.open_account_management_dialog)
            cover_action.triggered.connect(self.open_cover_settings_dialog)
            backup_action.triggered.connect(self.open_backup_settings_dialog)
            report_schedule_action.triggered.connect(self.open_report_schedule_settings_dialog)
            system_log_action.triggered.connect(self.open_system_log_dialog)
            system_menu.addAction(account_action)
            system_menu.addAction(cover_action)
            system_menu.addAction(backup_action)
            system_menu.addAction(report_schedule_action)
            system_menu.addAction(system_log_action)

    # -------------------------
    # Dialogs
    # -------------------------
    def open_income_setup(self):
        dlg = IncomeSetupDialog(user_role=self.role)
        dlg.exec_()
        if self.income_expense_page is not None and hasattr(self.income_expense_page, "refresh_all_tabs"):
            self.income_expense_page.refresh_all_tabs()

    def open_expense_setup(self):
        dlg = ExpenseSetupDialog(user_role=self.role)
        dlg.exec_()
        if self.income_expense_page is not None and hasattr(self.income_expense_page, "refresh_all_tabs"):
            self.income_expense_page.refresh_all_tabs()

    def open_identity_setup(self):
        dlg = MemberIdentityDialog(user_role=self.role)
        dlg.exec_()

    # -------------------------
    # Household page
    # -------------------------
    def open_household_entry(self):
        if self.main_page is None:
            self.main_page = MainPageWidget(self.controller)
            if hasattr(self.main_page, "set_user_role"):
                self.main_page.set_user_role(self.role)
            if hasattr(self.main_page, "font_size_changed"):
                self.main_page.font_size_changed.connect(self.on_global_font_size_changed)
            if self.font_manager and hasattr(self.main_page, "set_font_size_label"):
                self.main_page.set_font_size_label(self.font_manager.get_label())
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

            name = getattr(dialog, "created_name", "")
            phone = getattr(dialog, "created_phone_mobile", "")

            QMessageBox.information(
                self,
                "成功",
                f"已新增戶籍\n姓名：{name}\n手機：{phone}"
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
        if hasattr(self.activity_manage_page, "set_current_username"):
            self.activity_manage_page.set_current_username(self.operator_name)
        if hasattr(self.activity_manage_page, "set_current_user_role"):
            self.activity_manage_page.set_current_user_role(self.role)
        if hasattr(self.activity_manage_page, "refresh_after_signup_changes"):
            self.activity_manage_page.refresh_after_signup_changes()

        self._show_page(self.activity_manage_page)

    def open_activity_signup(self, activity_data=None):
        if self.activity_signup_page is None:
            self.activity_signup_page = ActivitySignupPage(
                self.controller,
                operator_name=getattr(self, "operator_name", "") or self.username,
                user_role=self.role,
            )
            self.activity_signup_page.request_back_to_manage.connect(self.open_activity_manage)
            self.activity_signup_page.request_close.connect(self.open_household_entry)
        else:
            if hasattr(self.activity_signup_page, "set_default_payment_handler"):
                self.activity_signup_page.set_default_payment_handler(
                    getattr(self, "operator_name", "") or self.username
                )
            if hasattr(self.activity_signup_page, "set_current_user_role"):
                self.activity_signup_page.set_current_user_role(self.role)

        if activity_data:
            self.activity_signup_page.set_activity(activity_data)

        self._show_page(self.activity_signup_page)

    def open_income_expense_page(self, initial_tab=0):
        if int(initial_tab or 0) == 1 and not can_view_expense_entry(self.role):
            QMessageBox.warning(self, "權限不足", "目前角色無權限使用支出資料登錄作業。")
            initial_tab = 0

        if self.income_expense_page is None:
            self.income_expense_page = IncomeExpensePage(
                self.controller,
                self,
                initial_tab=initial_tab,
                user_role=self.role,
                current_operator_name=getattr(self, "operator_name", "") or self.username,
            )
            self.income_expense_page.request_close.connect(self.open_household_entry)
        else:
            if hasattr(self.income_expense_page, "tabs"):
                idx = 0 if int(initial_tab or 0) == 0 else 1
                self.income_expense_page.tabs.setCurrentIndex(idx)
            if hasattr(self.income_expense_page, "refresh_current_tab"):
                self.income_expense_page.refresh_current_tab()

        self._show_page(self.income_expense_page)

    def open_income_expense_dialog(self, initial_tab=0):
        # backward compatibility: 舊呼叫點導向 page
        self.open_income_expense_page(initial_tab)

    def open_lighting_setup(self):
        dialog = LightingSetupDialog(self.controller, self, user_role=self.role)
        dialog.exec_()

    def open_lighting_signup(self):
        if self.lighting_signup_page is None:
            self.lighting_signup_page = LightingSignupPage(
                self.controller,
                self,
                operator_name=getattr(self, "operator_name", "") or self.username,
                user_role=self.role,
            )
            self.lighting_signup_page.request_close.connect(self.open_household_entry)
        else:
            if hasattr(self.lighting_signup_page, "operator_name"):
                self.lighting_signup_page.operator_name = getattr(self, "operator_name", "") or self.username
            if hasattr(self.lighting_signup_page, "user_role"):
                self.lighting_signup_page.user_role = self.role
            if hasattr(self.lighting_signup_page, "edt_payment_handler"):
                self.lighting_signup_page.edt_payment_handler.setText(getattr(self, "operator_name", "") or self.username)
            if hasattr(self.lighting_signup_page, "_apply_payment_handler_permissions"):
                self.lighting_signup_page._apply_payment_handler_permissions()
            if hasattr(self.lighting_signup_page, "lbl_operator"):
                self.lighting_signup_page.lbl_operator.setText(
                    f"目前經手人預設：{(getattr(self, 'operator_name', '') or self.username) or '（未取得）'}"
                )
            if hasattr(self.lighting_signup_page, "_reload_all"):
                self.lighting_signup_page._reload_all()

        self._show_page(self.lighting_signup_page)

    def _can_access_finance_report(self):
        return can_access_finance_report(self.role)

    def _can_manage_accounts(self):
        return can_manage_accounts(self.role)

    def _reauth_admin_for_sensitive_action(self, action_name: str) -> bool:
        verifier = getattr(self.controller, "verify_user_password", None)
        if not callable(verifier):
            QMessageBox.warning(self, "功能不可用", "目前系統不支援二次驗證。")
            return False

        password, ok = QInputDialog.getText(
            self,
            "二次驗證",
            f"請輸入目前帳號密碼以繼續「{action_name}」",
            QLineEdit.Password,
        )
        if not ok:
            return False
        if not (password or "").strip():
            QMessageBox.warning(self, "驗證失敗", "密碼不可空白。")
            return False

        try:
            valid = bool(verifier(self.username, password, require_active=True))
        except Exception:
            QMessageBox.warning(self, "驗證失敗", "密碼驗證時發生錯誤，請稍後重試。")
            return False

        if not valid:
            QMessageBox.warning(self, "驗證失敗", "密碼錯誤或帳號已停用。")
            return False
        return True

    def open_finance_report_dialog(self):
        if not self._can_access_finance_report():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員與會計人員。")
            return
        # backward compatibility: 舊呼叫點導向 page
        self.open_finance_report_page()

    def open_finance_report_page(self):
        if not self._can_access_finance_report():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員與會計人員。")
            return
        if self.finance_report_page is None:
            self.finance_report_page = FinanceReportPage(self.controller, self)
            self.finance_report_page.request_close.connect(self.open_household_entry)
        else:
            # 每次進入維持最新查詢結果
            if hasattr(self.finance_report_page, "run_query"):
                self.finance_report_page.run_query()

        self._show_page(self.finance_report_page)

    def open_account_management_dialog(self):
        if not self._can_manage_accounts():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員。")
            return
        dialog = AccountManagementDialog(self.controller, self.username, self)
        dialog.exec_()

    def open_cover_settings_dialog(self):
        if not self._can_manage_accounts():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員。")
            return
        dialog = CoverSettingsDialog(self.controller, self)
        dialog.exec_()

    def open_backup_settings_dialog(self):
        if not self._can_manage_accounts():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員。")
            return
        dialog = BackupSettingsDialog(self.controller, self)
        dialog.exec_()

    def open_report_schedule_settings_dialog(self):
        if not self._can_manage_accounts():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員。")
            return
        dialog = ReportScheduleSettingsDialog(self.controller, self)
        dialog.exec_()

    def open_system_log_dialog(self):
        if not self._can_manage_accounts():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員。")
            return
        if not self._reauth_admin_for_sensitive_action("系統日誌"):
            return
        dialog = SystemLogViewerDialog(self)
        dialog.exec_()

    def _setup_idle_logout(self):
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
            self._idle_filter_installed = True
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(30 * 1000)
        self._idle_timer.timeout.connect(self._check_idle_timeout)
        self._idle_timer.start()

    def eventFilter(self, obj, event):
        if event.type() in {
            QEvent.MouseMove,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.KeyPress,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
        }:
            self._last_activity_ts = time.monotonic()
        return super().eventFilter(obj, event)

    def _check_idle_timeout(self):
        get_idle = getattr(self.controller, "get_idle_logout_minutes", None)
        if not callable(get_idle):
            return
        try:
            minutes = int(get_idle())
        except Exception:
            return
        if minutes <= 0:
            return
        elapsed = time.monotonic() - self._last_activity_ts
        if elapsed >= minutes * 60:
            # 不跳阻塞式彈窗，避免卡住流程與關閉時潛在 crash
            if hasattr(self, "_idle_timer") and self._idle_timer is not None:
                self._idle_timer.stop()
            self._is_logout = True
            try:
                log_system(f"使用者 {self.username} 因閒置 {minutes} 分鐘自動登出", level="WARN")
            except Exception:
                pass
            self.close()

    def closeEvent(self, event):
        # 避免 QApp 持有已銷毀視窗的 event filter，造成關閉時 crash / segmentation fault
        try:
            app = QApplication.instance()
            if app is not None:
                # macOS 上若輸入法仍綁定在 QLineEdit 等輸入元件，
                # 視窗關閉時可能在 IMK / Qt 清理階段觸發 crash。
                focus_widget = app.focusWidget()
                if focus_widget is not None:
                    try:
                        focus_widget.clearFocus()
                    except Exception as e:
                        log_system(f"主視窗關閉前清除焦點失敗：{e}", level="WARN")
                try:
                    self.setFocus()
                except Exception as e:
                    log_system(f"主視窗關閉前設定視窗焦點失敗：{e}", level="WARN")
                app.processEvents()
        except Exception as e:
            log_system(f"主視窗關閉前處理焦點/事件失敗：{e}", level="WARN")
        try:
            if hasattr(self, "_idle_timer") and self._idle_timer is not None:
                self._idle_timer.stop()
        except Exception as e:
            log_system(f"主視窗關閉前停止閒置計時器失敗：{e}", level="WARN")
        try:
            app = QApplication.instance()
            if app and self._idle_filter_installed:
                app.removeEventFilter(self)
                self._idle_filter_installed = False
        except Exception as e:
            log_system(f"主視窗關閉前移除 event filter 失敗：{e}", level="WARN")
        super().closeEvent(event)

    def on_global_font_size_changed(self, label):
        if self.font_manager:
            self.font_manager.apply(label)

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
            try:
                log_system(f"使用者 {self.username} 手動登出", level="INFO")
            except Exception:
                pass
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
