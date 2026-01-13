# tests/test_main_window.py
import pytest
from unittest.mock import MagicMock

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel

import app.main_window as main_window_module
from app.main_window import MainWindow


# -------------------------
# Test doubles (Fake UI parts)
# -------------------------
class FakeSearchBar(QObject):
    search_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()


class FakeMainPageWidget(QWidget):
    """
    測試用 MainPageWidget（一定要是 QWidget，才能 setCentralWidget）
    - 提供 search_bar.search_triggered / new_household_triggered signal
    - 提供 perform_search 會呼叫到的 UI 更新方法
    - 提供 stats_label.setText
    """
    new_household_triggered = pyqtSignal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.search_bar = FakeSearchBar()

        # 下面三個方法會在 perform_search success 情境被呼叫
        self.update_household_table = MagicMock()
        self.fill_head_detail = MagicMock()
        self.update_member_table = MagicMock()

        self.stats_label = QLabel("")  # 用真正 QLabel，行為最接近


# -------------------------
# Tests
# -------------------------
def test_main_window_init(qtbot):
    mock_controller = MagicMock()

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    assert window.username == "test_user"
    assert window.role == "管理者"
    assert "宮廟管理系統" in window.windowTitle()
    assert window.controller is mock_controller
    assert window.menuBar() is not None


def test_open_household_entry_sets_central_widget_and_wires_signals(qtbot, monkeypatch):
    """
    測試 open_household_entry 是否：
    1) setCentralWidget(MainPageWidget)
    2) 把 search_triggered 連到 perform_search
    3) 把 new_household_triggered 連到 open_new_household_dialog
    """
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.perform_search = MagicMock()
    window.open_new_household_dialog = MagicMock()

    window.open_household_entry()

    assert window.centralWidget() is window.main_page
    assert isinstance(window.main_page, FakeMainPageWidget)

    window.main_page.search_bar.search_triggered.emit("abc")
    window.perform_search.assert_called_once_with("abc")

    window.main_page.new_household_triggered.emit()
    window.open_new_household_dialog.assert_called_once()


def test_perform_search_success_updates_ui(qtbot, monkeypatch):
    """
    測試 perform_search 成功情境：
    - controller.search_by_any_name 回傳 head_result & members
    - controller.format_head_data 轉換 head_data
    - 更新 main_page 的 table/detail/member/stats_label
    """
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    mock_controller = MagicMock()
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.open_household_entry()

    head_result = {"id": 1, "head_name": "王小明"}
    members = [
        {"name": "王小華", "identity": "丁"},
        {"name": "王小美", "identity": "口"},
    ]
    head_data = {"id": 1, "head_name": "王小明"}

    mock_controller.search_by_any_name.return_value = (head_result, members)
    mock_controller.format_head_data.return_value = head_data

    window.perform_search("王")

    mock_controller.search_by_any_name.assert_called_once_with("王")
    mock_controller.format_head_data.assert_called_once_with(head_result)

    window.main_page.update_household_table.assert_called_once_with([head_data])
    window.main_page.fill_head_detail.assert_called_once_with(head_data)
    window.main_page.update_member_table.assert_called_once_with(members)

    text = window.main_page.stats_label.text()
    assert "戶號" in text
    assert "戶長" in text
    assert "王小明" in text


def test_perform_search_no_result_shows_messagebox_and_no_updates(qtbot, monkeypatch):
    """
    測試 perform_search 失敗情境：
    - controller.search_by_any_name 回傳 None
    - QMessageBox.information 被呼叫
    - UI 更新方法不應被呼叫（避免殘留舊資料）
    """
    monkeypatch.setattr(main_window_module, "MainPageWidget", FakeMainPageWidget)

    info_mock = MagicMock()
    monkeypatch.setattr(main_window_module.QMessageBox, "information", info_mock)

    mock_controller = MagicMock()
    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    window.open_household_entry()

    mock_controller.search_by_any_name.return_value = (None, [])

    window.perform_search("不存在")

    info_mock.assert_called_once()

    window.main_page.update_household_table.assert_not_called()
    window.main_page.fill_head_detail.assert_not_called()
    window.main_page.update_member_table.assert_not_called()
