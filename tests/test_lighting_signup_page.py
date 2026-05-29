from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QTextEdit

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

    def mark_lighting_signups_paid(self, signup_year, signup_ids, handler="", payment_method="cash", transfer_last5=""):
        self.last_payment_call = {
            "signup_year": signup_year,
            "signup_ids": signup_ids,
            "handler": handler,
            "payment_method": payment_method,
            "transfer_last5": transfer_last5,
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
    check_item.setCheckState(Qt.Checked)
    check_item.setData(Qt.UserRole, "LS1")
    page.tbl_signups.setItem(0, 0, check_item)
    page.tbl_signups.setItem(0, 6, QTableWidgetItem("500"))
    page.tbl_signups.setItem(0, 7, QTableWidgetItem("未繳費"))

    monkeypatch.setattr("app.widgets.lighting_signup_page.QMessageBox.information", lambda *args, **kwargs: None)

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
    }
