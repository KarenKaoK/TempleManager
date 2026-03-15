from unittest.mock import MagicMock

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

import app.widgets.activity_signup_page as activity_signup_page_module
from app.widgets.activity_signup_page import ActivitySignupPage


class FakePersonPanel(QWidget):
    search_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def show_search_results(self, people):
        return None

    def get_person_payload(self):
        return {}


class FakePlanPanel(QWidget):
    save_clicked = pyqtSignal()

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

    def clear(self):
        return None

    def load_activity(self, activity_id):
        return None


def test_signup_page_has_close_back_button_and_emits_request_close(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)

    btn = next(
        b for b in page.findChildren(QPushButton)
        if b.text() == "關閉返回"
    )
    assert btn is not None

    with qtbot.waitSignal(page.request_close, timeout=1000):
        qtbot.mouseClick(btn, Qt.LeftButton)


def test_signup_detail_table_enables_horizontal_scroll(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)

    assert page.tbl_signup_detail.horizontalScrollMode() == QAbstractItemView.ScrollPerPixel
    assert page.tbl_signup_detail.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert page.tbl_signup_detail.horizontalHeader().sectionResizeMode(4) == QHeaderView.Interactive
