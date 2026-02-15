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

    def __init__(self, controller):
        super().__init__()
        self.controller = controller


# -------------------------
# Tests
# -------------------------
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
