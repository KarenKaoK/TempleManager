from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMessageBox, QWidget, QStackedWidget, QDialog,
    QHBoxLayout, QPushButton, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QEvent, QTimer, QObject, QThread, pyqtSignal
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
from app.dialogs.finance_report_dialog import FinanceReportDialog
from app.dialogs.lighting_setup_dialog import LightingSetupDialog
from app.dialogs.account_management_dialog import AccountManagementDialog
from app.dialogs.cover_settings_dialog import CoverSettingsDialog
from app.dialogs.backup_settings_dialog import BackupSettingsDialog
from app.controller.app_controller import AppController


class ScheduledBackupWorker(QObject):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        worker_controller = None
        error_text = None
        try:
            # 背景 thread 不可共用主執行緒的 sqlite connection，需建立獨立 controller
            db_path = getattr(self.controller, "db_path", None)
            worker_controller = AppController(db_path=db_path) if db_path else AppController()
            worker_controller.create_local_backup(manual=False)
        except Exception as e:
            error_text = str(e)
        finally:
            # 先釋放 worker thread 內的 sqlite connection，避免主執行緒 callback 卡在 DB lock
            try:
                conn = getattr(worker_controller, "conn", None)
                if conn is not None:
                    conn.close()
            except Exception:
                pass

        if error_text is not None:
            self.failed.emit(error_text)
            return
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, username, role, controller):
        super().__init__()
        self.username = username
        self.role = role
        self.operator_name = username
        self.controller = controller
        self.font_manager = getattr(QApplication.instance(), "font_manager", None)
        self._last_activity_ts = time.monotonic()
        self._idle_filter_installed = False
        self._backup_retry_cooldown_seconds = 300  # 排程失敗後 5 分鐘內不重試
        self._backup_retry_cooldown_until = 0.0
        self._scheduled_backup_running = False
        self._scheduled_backup_thread = None
        self._scheduled_backup_worker = None

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
        self.finance_report_action = None

        # ✅ 空白頁
        self._blank_page = QWidget()
        self.stack.addWidget(self._blank_page)
        self.stack.setCurrentWidget(self._blank_page)

        self.setup_menu()
        self._setup_idle_logout()
        self._setup_backup_scheduler()
        
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
        income_entry_action = QAction("收入資料登錄作業", self)
        expense_entry_action = QAction("支出資料登錄作業", self)
        
        income_entry_action.triggered.connect(lambda: self.open_income_expense_page(0))
        expense_entry_action.triggered.connect(lambda: self.open_income_expense_page(1))
        
        finance_menu.addAction(income_entry_action)
        finance_menu.addAction(expense_entry_action)

        if self._can_access_finance_report():
            finance_report_menu = menu_bar.addMenu("財務會計")
            self.finance_report_action = QAction("會計彙整報表", self)
            self.finance_report_action.triggered.connect(self.open_finance_report_dialog)
            finance_report_menu.addAction(self.finance_report_action)

        if self._can_manage_accounts():
            system_menu = menu_bar.addMenu("系統管理")
            account_action = QAction("帳號管理", self)
            cover_action = QAction("封面設定", self)
            backup_action = QAction("資料備份", self)
            account_action.triggered.connect(self.open_account_management_dialog)
            cover_action.triggered.connect(self.open_cover_settings_dialog)
            backup_action.triggered.connect(self.open_backup_settings_dialog)
            system_menu.addAction(account_action)
            system_menu.addAction(cover_action)
            system_menu.addAction(backup_action)

    # -------------------------
    # Dialogs
    # -------------------------
    def open_income_setup(self):
        dlg = IncomeSetupDialog(user_role=self.role)
        dlg.exec_()

    def open_expense_setup(self):
        dlg = ExpenseSetupDialog(user_role=self.role)
        dlg.exec_()

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
        role = (self.role or "").strip()
        return role in {"管理員", "會計", "會計人員", "管理者"}

    def _can_manage_accounts(self):
        return (self.role or "").strip() in {"管理員", "管理者"}

    def open_finance_report_dialog(self):
        if not self._can_access_finance_report():
            QMessageBox.warning(self, "權限不足", "此功能僅限管理員與會計人員。")
            return
        dialog = FinanceReportDialog(self.controller, self)
        dialog.exec_()

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

    def _setup_idle_logout(self):
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
            self._idle_filter_installed = True
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(30 * 1000)
        self._idle_timer.timeout.connect(self._check_idle_timeout)
        self._idle_timer.start()

    def _setup_backup_scheduler(self):
        get_backup_settings = getattr(self.controller, "get_backup_settings", None)
        if callable(get_backup_settings):
            try:
                if bool(get_backup_settings().get("use_cli_scheduler")):
                    return
            except Exception:
                pass
        self._backup_timer = QTimer(self)
        self._backup_timer.setInterval(60 * 1000)  # 每分鐘檢查一次
        self._backup_timer.timeout.connect(self._check_backup_schedule)
        self._backup_timer.start()

    def _check_backup_schedule(self):
        get_backup_settings = getattr(self.controller, "get_backup_settings", None)
        if callable(get_backup_settings):
            try:
                if bool(get_backup_settings().get("use_cli_scheduler")):
                    return
            except Exception:
                pass
        should_run = getattr(self.controller, "should_run_scheduled_backup", None)
        try:
            if time.monotonic() < float(self._backup_retry_cooldown_until or 0):
                return
        except Exception:
            pass
        do_backup = getattr(self.controller, "create_local_backup", None)
        mark_run = getattr(self.controller, "mark_backup_run", None)
        if not callable(should_run) or not callable(do_backup) or not callable(mark_run):
            return
        if self._scheduled_backup_running:
            return
        try:
            if not should_run():
                return
            self._scheduled_backup_running = True
            self._start_scheduled_backup_worker()
        except Exception:
            # 備份失敗不阻斷主流程，失敗細節由 backup_logs 紀錄
            self._scheduled_backup_running = False
            self._backup_retry_cooldown_until = time.monotonic() + float(self._backup_retry_cooldown_seconds)
            return

    def _start_scheduled_backup_worker(self):
        self._scheduled_backup_thread = QThread(self)
        self._scheduled_backup_worker = ScheduledBackupWorker(self.controller)
        self._scheduled_backup_worker.moveToThread(self._scheduled_backup_thread)

        self._scheduled_backup_thread.started.connect(self._scheduled_backup_worker.run)
        self._scheduled_backup_worker.finished.connect(self._on_scheduled_backup_finished)
        self._scheduled_backup_worker.failed.connect(self._on_scheduled_backup_failed)

        self._scheduled_backup_worker.finished.connect(self._scheduled_backup_thread.quit)
        self._scheduled_backup_worker.failed.connect(self._scheduled_backup_thread.quit)
        self._scheduled_backup_thread.finished.connect(self._cleanup_scheduled_backup_thread)

        self._scheduled_backup_thread.start()

    def _on_scheduled_backup_finished(self):
        try:
            mark_run = getattr(self.controller, "mark_backup_run", None)
            if callable(mark_run):
                mark_run()
        except Exception:
            pass
        self._backup_retry_cooldown_until = 0.0
        self._scheduled_backup_running = False

    def _on_scheduled_backup_failed(self, _error_text: str):
        self._scheduled_backup_running = False
        self._backup_retry_cooldown_until = time.monotonic() + float(self._backup_retry_cooldown_seconds)

    def _cleanup_scheduled_backup_thread(self):
        if self._scheduled_backup_worker is not None:
            try:
                self._scheduled_backup_worker.deleteLater()
            except Exception:
                pass
        if self._scheduled_backup_thread is not None:
            try:
                self._scheduled_backup_thread.deleteLater()
            except Exception:
                pass
        self._scheduled_backup_worker = None
        self._scheduled_backup_thread = None

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
            self.close()

    def closeEvent(self, event):
        # 避免 QApp 持有已銷毀視窗的 event filter，造成關閉時 crash / segmentation fault
        try:
            if hasattr(self, "_idle_timer") and self._idle_timer is not None:
                self._idle_timer.stop()
            if hasattr(self, "_backup_timer") and self._backup_timer is not None:
                self._backup_timer.stop()
        except Exception:
            pass
        try:
            app = QApplication.instance()
            if app and self._idle_filter_installed:
                app.removeEventFilter(self)
                self._idle_filter_installed = False
        except Exception:
            pass
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
