# tests/test_main_window.py
import pytest
from unittest.mock import MagicMock

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QMessageBox
from PyQt5.QtTest import QTest

import app.main_window as main_window_module
from app.main_window import MainWindow


# -------------------------
# Test doubles (Fake UI parts)
# -------------------------
class FakeSearchBar(QObject):
    search_triggered = pyqtSignal(str)
    show_all_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()


class FakeMainPageWidget(QWidget):
    new_household_triggered = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.search_bar = FakeSearchBar()

        self.update_household_table = MagicMock()
        self.fill_person_detail = MagicMock()
        self.update_member_table = MagicMock()
        self.refresh_all_panels = MagicMock()
        self._load_household = MagicMock()

        self.stats_label = QLabel("")


class FakeActivityManagePage(QWidget):
    request_close = pyqtSignal()
    request_open_signup = pyqtSignal(dict)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller


class FakeActivitySignupPage(QWidget):
    request_back_to_manage = pyqtSignal()
    request_close = pyqtSignal()

    def __init__(self, controller, parent=None, *args, **kwargs):
        super().__init__()
        self.controller = controller


class FakeIncomeExpensePage(QWidget):
    last_instance = None
    request_close = pyqtSignal()

    def __init__(self, controller, parent=None, initial_tab=0, user_role=None, current_operator_name=""):
        super().__init__(parent)
        self.controller = controller
        self.parent = parent
        self.initial_tab = initial_tab
        self.user_role = user_role
        self.current_operator_name = current_operator_name
        FakeIncomeExpensePage.last_instance = self


class FakeFinanceReportPage(QWidget):
    last_instance = None
    request_close = pyqtSignal()

    def __init__(self, controller, parent):
        super().__init__(parent)
        self.controller = controller
        self.parent = parent
        self.run_query_called = 0
        FakeFinanceReportPage.last_instance = self

    def run_query(self):
        self.run_query_called += 1


class FakeAccountManagementDialog:
    last_instance = None

    def __init__(self, controller, actor_username, parent):
        self.controller = controller
        self.actor_username = actor_username
        self.parent = parent
        self.exec_called = False
        FakeAccountManagementDialog.last_instance = self

    def exec_(self):
        self.exec_called = True


class FakeCoverSettingsDialog:
    last_instance = None

    def __init__(self, controller, parent):
        self.controller = controller
        self.parent = parent
        self.exec_called = False
        FakeCoverSettingsDialog.last_instance = self

    def exec_(self):
        self.exec_called = True


class FakeBackupSettingsDialog:
    last_instance = None

    def __init__(self, controller, parent):
        self.controller = controller
        self.parent = parent
        self.exec_called = False
        FakeBackupSettingsDialog.last_instance = self

    def exec_(self):
        self.exec_called = True


class FakeReportScheduleSettingsDialog:
    last_instance = None

    def __init__(self, controller, parent):
        self.controller = controller
        self.parent = parent
        self.exec_called = False
        FakeReportScheduleSettingsDialog.last_instance = self

    def exec_(self):
        self.exec_called = True


class FakeSystemLogViewerDialog:
    last_instance = None

    def __init__(self, parent=None):
        self.parent = parent
        self.exec_called = False
        FakeSystemLogViewerDialog.last_instance = self

    def exec_(self):
        self.exec_called = True


# -------------------------
# Tests
# -------------------------
@pytest.fixture(autouse=True)
def _mock_system_log(monkeypatch):
    calls = []
    def fake_log(message: str, level: str = "INFO"):
        calls.append({"message": message, "level": level})
    monkeypatch.setattr(main_window_module, "log_system", fake_log)
    return calls


def test_main_window_init(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    assert window.username == "test_user"
    assert window.role == "管理者"
    assert "宮廟管理系統" in window.windowTitle()
    assert window.controller is mock_controller
    assert window.main_page is not None
    assert window.stack.currentWidget() is window.main_page


def test_open_household_entry_sets_central_widget_and_wires_signals(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    
    # 在 class 層級 mock，這樣 __init__ 連接時就會連到 mock
    mock_perform_search = MagicMock()
    mock_open_dialog = MagicMock()
    monkeypatch.setattr(MainWindow, "perform_search", mock_perform_search)
    monkeypatch.setattr(MainWindow, "open_new_household_dialog", mock_open_dialog)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    assert window.stack.currentWidget() is window.main_page
    
    window.main_page.search_bar.search_triggered.emit("abc")
    mock_perform_search.assert_called()

    window.main_page.new_household_triggered.emit()
    mock_open_dialog.assert_called()


def test_perform_search_success_updates_ui(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.main_page.update_household_table.reset_mock()

    people = [
        {"id": "P1", "name": "王小明", "household_id": "H1"},
    ]
    mock_controller.search_people_unified.return_value = people

    window.perform_search("王")

    mock_controller.search_people_unified.assert_called_once_with("王")
    window.main_page.update_household_table.assert_called_once_with(people)
    window.main_page._load_household.assert_called_once_with("H1", "P1")


def test_show_all_calls_refresh(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)
    
    window.main_page.refresh_all_panels.reset_mock()
    window.main_page.search_bar.show_all_triggered.emit()
    window.main_page.refresh_all_panels.assert_called_once()


def test_perform_search_no_result(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    info_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "information", info_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.main_page.update_household_table.reset_mock()
    mock_controller.search_people_unified.return_value = []

    window.perform_search("不存在")

    info_mock.assert_called_once()
    window.main_page.update_household_table.assert_not_called()


def test_activity_manage_close_returns_to_main_page(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "ActivityManagePage", FakeActivityManagePage)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.open_activity_manage()
    assert window.stack.currentWidget() is window.activity_manage_page

    window.activity_manage_page.request_close.emit()
    assert window.stack.currentWidget() is window.main_page


def test_activity_signup_close_returns_to_main_page(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "ActivitySignupPage", FakeActivitySignupPage)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.open_activity_signup()
    assert window.stack.currentWidget() is window.activity_signup_page

    window.activity_signup_page.request_close.emit()
    assert window.stack.currentWidget() is window.main_page


def test_bottom_bar_hidden_on_activity_pages_and_shown_on_main(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "ActivityManagePage", FakeActivityManagePage)
    monkeypatch.setattr(main_window_module, "ActivitySignupPage", FakeActivitySignupPage)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    assert window.bottom_bar.isHidden() is False

    window.open_activity_manage()
    assert window.bottom_bar.isHidden() is True

    window.open_activity_signup()
    assert window.bottom_bar.isHidden() is True

    window.open_household_entry()
    assert window.bottom_bar.isHidden() is False


def test_open_income_expense_dialog_passes_role(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "IncomeExpensePage", FakeIncomeExpensePage)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []

    window = MainWindow("test_user", "會計", mock_controller)
    qtbot.addWidget(window)

    window.open_income_expense_dialog(initial_tab=1)
    instance = FakeIncomeExpensePage.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.parent is window
    assert instance.initial_tab == 1
    assert instance.user_role == "會計"
    assert window.stack.currentWidget() is window.income_expense_page


def test_finance_report_action_visible_for_accountant(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "FinanceReportPage", FakeFinanceReportPage)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    window = MainWindow("test_user", "會計", mock_controller)
    qtbot.addWidget(window)

    assert window.finance_report_action is not None
    window.open_finance_report_dialog()
    instance = FakeFinanceReportPage.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.parent is window
    assert window.stack.currentWidget() is window.finance_report_page


def test_finance_report_action_hidden_for_staff(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    window = MainWindow("test_user", "工作人員", mock_controller)
    qtbot.addWidget(window)

    assert window.finance_report_action is None


def test_open_finance_report_dialog_blocks_staff(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    warn_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warn_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    window = MainWindow("test_user", "工作人員", mock_controller)
    qtbot.addWidget(window)

    window.open_finance_report_dialog()
    warn_mock.assert_called_once()


def test_admin_can_open_account_management_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "AccountManagementDialog", FakeAccountManagementDialog)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    window.open_account_management_dialog()
    instance = FakeAccountManagementDialog.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.actor_username == "admin"
    assert instance.parent is window
    assert instance.exec_called is True


def test_staff_open_account_management_dialog_is_blocked(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    warn_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warn_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("staff", "工作人員", mock_controller)
    qtbot.addWidget(window)

    window.open_account_management_dialog()
    warn_mock.assert_called_once()


def test_admin_can_open_cover_settings_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "CoverSettingsDialog", FakeCoverSettingsDialog)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    window.open_cover_settings_dialog()
    instance = FakeCoverSettingsDialog.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.parent is window
    assert instance.exec_called is True


def test_staff_open_cover_settings_dialog_is_blocked(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    warn_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warn_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("staff", "工作人員", mock_controller)
    qtbot.addWidget(window)

    window.open_cover_settings_dialog()
    warn_mock.assert_called_once()


def test_admin_can_open_backup_settings_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "BackupSettingsDialog", FakeBackupSettingsDialog)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    mock_controller.should_run_scheduled_backup.return_value = False
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    window.open_backup_settings_dialog()
    instance = FakeBackupSettingsDialog.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.parent is window
    assert instance.exec_called is True


def test_staff_open_backup_settings_dialog_is_blocked(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    warn_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warn_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    mock_controller.should_run_scheduled_backup.return_value = False
    window = MainWindow("staff", "工作人員", mock_controller)
    qtbot.addWidget(window)

    window.open_backup_settings_dialog()
    warn_mock.assert_called_once()


def test_admin_can_open_report_schedule_settings_dialog(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "ReportScheduleSettingsDialog", FakeReportScheduleSettingsDialog)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    window.open_report_schedule_settings_dialog()
    instance = FakeReportScheduleSettingsDialog.last_instance
    assert instance is not None
    assert instance.controller is mock_controller
    assert instance.parent is window
    assert instance.exec_called is True


def test_staff_open_report_schedule_settings_dialog_is_blocked(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    warn_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "warning", warn_mock)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("staff", "工作人員", mock_controller)
    qtbot.addWidget(window)

    window.open_report_schedule_settings_dialog()
    warn_mock.assert_called_once()


def test_admin_open_system_log_dialog_requires_reauth_success(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "SystemLogViewerDialog", FakeSystemLogViewerDialog)
    FakeSystemLogViewerDialog.last_instance = None

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    monkeypatch.setattr(window, "_reauth_admin_for_sensitive_action", MagicMock(return_value=True))
    window.open_system_log_dialog()

    instance = FakeSystemLogViewerDialog.last_instance
    assert instance is not None
    assert instance.parent is window
    assert instance.exec_called is True


def test_admin_open_system_log_dialog_blocked_when_reauth_failed(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module, "SystemLogViewerDialog", FakeSystemLogViewerDialog)
    FakeSystemLogViewerDialog.last_instance = None

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    monkeypatch.setattr(window, "_reauth_admin_for_sensitive_action", MagicMock(return_value=False))
    window.open_system_log_dialog()

    assert FakeSystemLogViewerDialog.last_instance is None


def test_main_window_no_builtin_backup_timer(qtbot, monkeypatch):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0

    window = MainWindow("admin", "管理員", mock_controller)
    qtbot.addWidget(window)

    assert hasattr(window, "_backup_timer") is False


def test_manual_logout_writes_system_log(qtbot, monkeypatch, _mock_system_log):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)
    monkeypatch.setattr(main_window_module.QMessageBox, "question", MagicMock(return_value=QMessageBox.Yes))

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 0
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    close_mock = MagicMock()
    monkeypatch.setattr(window, "close", close_mock)

    window._on_logout()

    assert getattr(window, "_is_logout", False) is True
    close_mock.assert_called_once()
    assert any(c["level"] == "INFO" and "手動登出" in c["message"] for c in _mock_system_log)


def test_idle_logout_writes_system_log(qtbot, monkeypatch, _mock_system_log):
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    mock_controller.get_all_people.return_value = []
    mock_controller.get_idle_logout_minutes.return_value = 1
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    close_mock = MagicMock()
    monkeypatch.setattr(window, "close", close_mock)
    window._last_activity_ts = main_window_module.time.monotonic() - 61

    window._check_idle_timeout()

    assert getattr(window, "_is_logout", False) is True
    close_mock.assert_called_once()
    assert any(c["level"] == "WARN" and "自動登出" in c["message"] for c in _mock_system_log)
