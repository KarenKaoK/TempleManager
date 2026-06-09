from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QTableWidgetItem, QTextEdit

from app.widgets.lighting_signup_page import LightingSignupPage


class _FakePaymentDialog:
    last_kwargs = None

    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        _FakePaymentDialog.last_kwargs = kwargs

    def exec_(self):
        return QDialog.Accepted

    def get_payload(self):
        return {
            "handler": "王小明(admin)",
            "payment_method": "transfer",
            "transfer_last5": "T1234",
            "receipt_method": "ELECTRONIC",
            "paper_receipt_number": "",
        }


class _FakeLightingController:
    def get_lighting_hint_settings(self):
        return {
            "year": "2026",
            "tai_sui_text": "犯太歲：馬（太歲）\n鼠（歲破）",
            "ji_gai_text": "祭改：龍（喪門）\n兔（男制太陰女制桃花）",
            "peaceful_text": "平安無沖：蛇（太陽）\n雞（吉星臨照）",
        }

    def _default_lighting_hint_texts(self, year):
        return self.get_lighting_hint_settings()

    def list_lighting_items(self, include_inactive=False):
        return []

    def list_lighting_signups(self, signup_year, keyword="", unpaid_only=False):
        return []

    def get_lighting_signup_item_totals(self, signup_year, keyword=""):
        return []

    def mark_lighting_signups_paid(
        self,
        signup_year,
        signup_ids,
        handler="",
        payment_method="cash",
        transfer_last5="",
        receipt_method="ELECTRONIC",
        paper_receipt_number="",
    ):
        self.last_payment_call = {
            "signup_year": signup_year,
            "signup_ids": signup_ids,
            "handler": handler,
            "payment_method": payment_method,
            "transfer_last5": transfer_last5,
            "receipt_method": receipt_method,
            "paper_receipt_number": paper_receipt_number,
        }
        return {"paid_count": 1, "skipped_count": 0}


def test_lighting_hint_boxes_stay_single_line_and_scrollable(qtbot):
    page = LightingSignupPage(controller=_FakeLightingController())
    qtbot.addWidget(page)

    for widget in (page.txt_tai_sui_hint, page.txt_ji_gai_hint, page.txt_peaceful_hint):
        assert isinstance(widget, QTextEdit)
        assert widget.height() == 56
        assert widget.lineWrapMode() == QTextEdit.NoWrap
        assert widget.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
        assert widget.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        assert "\n" not in widget.toPlainText()


def test_lighting_payment_uses_dialog_and_fixed_handler(qtbot, monkeypatch):
    monkeypatch.setattr("app.widgets.lighting_signup_page.PaymentMethodDialog", _FakePaymentDialog)
    controller = _FakeLightingController()
    page = LightingSignupPage(controller=controller, operator_name="王小明(admin)")
    qtbot.addWidget(page)

    assert not hasattr(page, "edt_payment_handler")
    assert not hasattr(page, "cmb_payment_method")
    assert not hasattr(page, "edt_transfer_last5")

    page.tbl_signups.setRowCount(1)
    check_item = QTableWidgetItem("")
    check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    check_item.setCheckState(Qt.Unchecked)
    check_item.setData(Qt.UserRole, "LS1")
    check_item.setData(Qt.UserRole + 1, 0)
    page.tbl_signups.setItem(0, 0, check_item)
    page.tbl_signups.setItem(0, 2, QTableWidgetItem("王小明"))
    page.tbl_signups.setItem(0, 5, QTableWidgetItem("500"))
    page.tbl_signups.setItem(0, 6, QTableWidgetItem(""))
    page.tbl_signups.selectRow(0)

    messages = []
    def capture_information(parent, title, text):
        messages.append((title, text))

    monkeypatch.setattr("app.widgets.lighting_signup_page.QMessageBox.information", capture_information)

    page._on_mark_paid()

    assert _FakePaymentDialog.last_kwargs["title"] == "安燈繳費"
    assert _FakePaymentDialog.last_kwargs["handler"] == "王小明(admin)"
    assert _FakePaymentDialog.last_kwargs["can_edit_handler"] is False
    assert _FakePaymentDialog.last_kwargs["total_amount"] == 500
    assert controller.last_payment_call == {
        "signup_year": page.year_spin.value(),
        "signup_ids": ["LS1"],
        "handler": "王小明(admin)",
        "payment_method": "transfer",
        "transfer_last5": "T1234",
        "receipt_method": "ELECTRONIC",
        "paper_receipt_number": "",
    }
    assert messages[-1] == ("繳費完成", "姓名 王小明 繳費完成。")


def test_lighting_signup_table_is_read_only_and_status_checkbox_is_not_user_checkable(qtbot):
    controller = _FakeLightingController()
    page = LightingSignupPage(controller=controller)
    qtbot.addWidget(page)

    assert page.tbl_signups.editTriggers() == QAbstractItemView.NoEditTriggers
    assert page.tbl_signups.selectionBehavior() == QAbstractItemView.SelectRows
    assert page.tbl_signups.selectionMode() == QAbstractItemView.ExtendedSelection
    assert page.tbl_signups.columnCount() == 7
    assert [page.tbl_signups.horizontalHeaderItem(i).text() for i in range(page.tbl_signups.columnCount())] == [
        "已繳費", "類型", "姓名", "電話", "報名摘要", "金額", "收據號"
    ]
    assert page.tbl_signups.columnWidth(0) == 58
    assert page.tbl_signups.columnWidth(1) == 78
    assert page.tbl_signups.columnWidth(2) == 140
    assert page.tbl_signups.columnWidth(3) == 150
    assert page.tbl_signups.columnWidth(4) == 280
    assert page.tbl_signups.columnWidth(5) == 90
    assert page.tbl_signups.columnWidth(6) == 120
    assert page.tbl_signups.textElideMode() == Qt.ElideRight
    assert page.tbl_signups.viewportMargins().bottom() > 0
    assert not hasattr(page, "btn_clear_selection_rows")

    page.tbl_signups.setRowCount(1)
    check_item = QTableWidgetItem("")
    check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    check_item.setCheckState(Qt.Checked)
    check_item.setData(Qt.UserRole, "LS1")
    check_item.setData(Qt.UserRole + 1, 1)
    page.tbl_signups.setItem(0, 0, check_item)

    assert not bool(page.tbl_signups.item(0, 0).flags() & Qt.ItemIsUserCheckable)


def test_lighting_summary_cell_uses_tooltip_for_full_text(qtbot):
    class ControllerWithLongSummary(_FakeLightingController):
        def list_lighting_signups(self, signup_year, keyword="", unpaid_only=False):
            return [{
                "signup_id": "LS1",
                "person_id": "P1",
                "signup_kind": "INITIAL",
                "group_id": "LS1",
                "person_name": "王小明",
                "person_phone": "0911",
                "lighting_summary": "光明燈、太歲燈、財神燈、文昌燈、平安燈",
                "total_amount": 2500,
                "is_paid": 0,
                "payment_receipt_number": "",
            }]

    page = LightingSignupPage(controller=ControllerWithLongSummary())
    qtbot.addWidget(page)

    item = page.tbl_signups.item(0, 4)

    assert item.text() == "光明燈、太歲燈、財神燈、文昌燈、平安燈"
    assert item.toolTip() == item.text()


def test_lighting_signup_reload_restores_table_updates_and_signals(qtbot):
    class ControllerWithPaidRow(_FakeLightingController):
        def list_lighting_signups(self, signup_year, keyword="", unpaid_only=False):
            return [{
                "signup_id": "LS1",
                "person_id": "P1",
                "signup_kind": "INITIAL",
                "group_id": "LS1",
                "person_name": "王小明",
                "person_phone": "0911",
                "lighting_summary": "光明燈",
                "total_amount": 500,
                "is_paid": 1,
                "payment_receipt_number": "R001",
            }]

    page = LightingSignupPage(controller=ControllerWithPaidRow())
    qtbot.addWidget(page)

    page._reload_signup_list()

    assert page.tbl_signups.updatesEnabled()
    assert not page.tbl_signups.signalsBlocked()
    assert page.tbl_signups.item(0, 0).checkState() == Qt.Checked


def test_lighting_payment_selection_uses_selected_unpaid_rows_only(qtbot):
    controller = _FakeLightingController()
    page = LightingSignupPage(controller=controller)
    qtbot.addWidget(page)

    page.tbl_signups.setRowCount(2)
    unpaid_item = QTableWidgetItem("")
    unpaid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    unpaid_item.setCheckState(Qt.Unchecked)
    unpaid_item.setData(Qt.UserRole, "LS1")
    unpaid_item.setData(Qt.UserRole + 1, 0)
    page.tbl_signups.setItem(0, 0, unpaid_item)

    paid_item = QTableWidgetItem("")
    paid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    paid_item.setCheckState(Qt.Checked)
    paid_item.setData(Qt.UserRole, "LS2")
    paid_item.setData(Qt.UserRole + 1, 1)
    page.tbl_signups.setItem(1, 0, paid_item)

    selection_model = page.tbl_signups.selectionModel()
    selection_model.select(page.tbl_signups.model().index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
    selection_model.select(page.tbl_signups.model().index(1, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)

    assert page._selected_signup_ids() == ["LS1"]
