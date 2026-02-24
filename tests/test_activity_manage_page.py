from unittest.mock import MagicMock

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QPushButton

import app.widgets.activity_manage_page as activity_manage_page_module
from app.widgets.activity_manage_page import ActivityManagePage


class FakeActivityListPanel(QWidget):
    activity_selected = pyqtSignal(str)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

    def refresh(self, keyword=""):
        return None

    def set_selected(self, activity_id):
        return None


class FakeActivityDetailPanel(QWidget):
    request_back = pyqtSignal()
    activity_saved = pyqtSignal(str)
    activity_deleted = pyqtSignal(str)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.default_handler = None
        self.current_role = None

    def load_activity(self, activity_id):
        return None

    def set_default_payment_handler(self, username):
        self.default_handler = username

    def set_current_user_role(self, role):
        self.current_role = role


def test_manage_page_has_close_back_button_and_emits_request_close(qtbot, monkeypatch):
    monkeypatch.setattr(activity_manage_page_module, "ActivityListPanel", FakeActivityListPanel)
    monkeypatch.setattr(activity_manage_page_module, "ActivityDetailPanel", FakeActivityDetailPanel)

    page = ActivityManagePage(controller=MagicMock())
    qtbot.addWidget(page)

    btn = next(
        b for b in page.findChildren(QPushButton)
        if b.text() == "關閉返回"
    )
    assert btn is not None

    with qtbot.waitSignal(page.request_close, timeout=1000):
        qtbot.mouseClick(btn, Qt.LeftButton)


def test_manage_page_propagates_login_name_account_to_detail_panel(qtbot, monkeypatch):
    monkeypatch.setattr(activity_manage_page_module, "ActivityListPanel", FakeActivityListPanel)
    monkeypatch.setattr(activity_manage_page_module, "ActivityDetailPanel", FakeActivityDetailPanel)

    page = ActivityManagePage(controller=MagicMock())
    qtbot.addWidget(page)

    page.set_current_username("王小明(admin01)")

    assert hasattr(page, "activity_detail_panel")
    assert page.activity_detail_panel.default_handler == "王小明(admin01)"


def test_manage_page_propagates_user_role_to_detail_panel(qtbot, monkeypatch):
    monkeypatch.setattr(activity_manage_page_module, "ActivityListPanel", FakeActivityListPanel)
    monkeypatch.setattr(activity_manage_page_module, "ActivityDetailPanel", FakeActivityDetailPanel)

    page = ActivityManagePage(controller=MagicMock())
    qtbot.addWidget(page)

    page.set_current_user_role("會計")

    assert hasattr(page, "activity_detail_panel")
    assert page.activity_detail_panel.current_role == "會計"
