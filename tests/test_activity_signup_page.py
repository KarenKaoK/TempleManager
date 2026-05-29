from unittest.mock import MagicMock

from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel
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


def test_signup_detail_first_header_is_paid_text(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)

    assert page.tbl_signup_detail.horizontalHeaderItem(0).text() == "已繳費"


def test_mark_paid_enabled_by_selected_unpaid_rows(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)
    page.signup_group.setEnabled(True)

    page.activity_data = {"id": "A001"}
    page._signup_rows_all = [
        {
            "signup_id": "S1", "person_id": "P1", "is_paid": 0, "signup_kind": "INITIAL",
            "person_name": "王小明", "person_phone": "0912", "plan_summary": "方案A", "total_amount": 100
        },
        {
            "signup_id": "S2", "person_id": "P2", "is_paid": 1, "signup_kind": "INITIAL",
            "person_name": "王小華", "person_phone": "0922", "plan_summary": "方案B", "total_amount": 200
        },
    ]
    page._apply_signup_detail_filter()
    sel = page.tbl_signup_detail.selectionModel()
    idx_paid = page.tbl_signup_detail.model().index(1, 0)
    idx_unpaid = page.tbl_signup_detail.model().index(0, 0)

    # 先選未繳費列 -> 可繳費
    sel.select(idx_unpaid, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
    page._sync_mark_paid_enabled()
    assert "S1" in page._get_selected_unpaid_signup_ids()
    assert bool(page._get_selected_unpaid_signup_ids()) is True
    assert page.btn_signup_mark_paid.isEnabled()

    # 模擬 Ctrl 多選再加選已繳費列 -> 仍可繳費（已繳費列會被過濾）
    sel.select(idx_paid, QItemSelectionModel.Select | QItemSelectionModel.Rows)
    page._sync_mark_paid_enabled()
    selected_unpaid = page._get_selected_unpaid_signup_ids()
    assert "S1" in selected_unpaid
    assert "S2" not in selected_unpaid
    assert bool(selected_unpaid) is True


def test_signup_page_removes_payment_clear_button(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)

    assert not hasattr(page, "btn_signup_pay_clear")
    assert all(b.text() != "清除" for b in page.signup_group.findChildren(QPushButton))
