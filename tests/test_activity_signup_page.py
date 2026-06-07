from unittest.mock import MagicMock, patch

from PyQt5.QtCore import Qt, pyqtSignal, QItemSelectionModel
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView

import app.widgets.activity_signup_page as activity_signup_page_module
from app.widgets.activity_signup_page import ActivitySignupPage


class _FakePaymentDialog:
    last_kwargs = None

    def __init__(self, parent=None, **kwargs):
        _FakePaymentDialog.last_kwargs = kwargs

    def exec_(self):
        return QDialog.Accepted

    def get_payload(self):
        return {"handler": "王小明(admin)", "payment_method": "cash", "transfer_last5": ""}


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

    header = page.tbl_signup_detail.horizontalHeader()
    margins = page.tbl_signup_detail.viewportMargins()

    assert header.isHidden() is False
    assert header.minimumHeight() >= 30
    assert margins.top() >= header.minimumHeight()
    assert margins.bottom() > 0
    assert [page.tbl_signup_detail.horizontalHeaderItem(i).text() for i in range(page.tbl_signup_detail.columnCount())] == [
        "已繳費", "類型", "姓名", "電話", "報名摘要", "金額", "收據號"
    ]
    assert page.tbl_signup_detail.columnWidth(3) == 180
    assert page.tbl_signup_detail.columnWidth(4) == 260
    assert page.tbl_signup_detail.columnWidth(5) == 110
    assert page.tbl_signup_detail.columnWidth(6) == 150


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


def test_activity_payment_success_message_includes_selected_name(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)
    monkeypatch.setattr(activity_signup_page_module, "PaymentMethodDialog", _FakePaymentDialog)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []
    mock_controller.mark_activity_signups_paid.return_value = {"paid_count": 1, "skipped_count": 0}

    page = ActivitySignupPage(controller=mock_controller, operator_name="王小明(admin)")
    qtbot.addWidget(page)
    page.signup_group.setEnabled(True)
    page.activity_data = {"id": "A001"}
    page._signup_rows_all = [{
        "signup_id": "S1",
        "person_id": "P1",
        "is_paid": 0,
        "signup_kind": "INITIAL",
        "person_name": "王小明",
        "person_phone": "0912",
        "plan_summary": "方案A",
        "total_amount": 100,
    }]
    page._apply_signup_detail_filter()
    page.tbl_signup_detail.selectRow(0)

    with patch("app.widgets.activity_signup_page.QMessageBox.information") as mock_info:
        page._on_mark_signup_paid()

    mock_info.assert_called_with(page, "繳費完成", "姓名 王小明 繳費成功。")


def test_signup_page_removes_payment_clear_button(qtbot, monkeypatch):
    monkeypatch.setattr(activity_signup_page_module, "ActivityPersonPanel", FakePersonPanel)
    monkeypatch.setattr(activity_signup_page_module, "ActivityPlanPanel", FakePlanPanel)

    mock_controller = MagicMock()
    mock_controller.list_activities_for_signup.return_value = []

    page = ActivitySignupPage(controller=mock_controller)
    qtbot.addWidget(page)

    assert not hasattr(page, "btn_signup_pay_clear")
    assert all(b.text() != "清除" for b in page.signup_group.findChildren(QPushButton))
