from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton

from app.widgets.activity_detail_panel import ActivityDetailPanel


class FakeController:
    def get_activity_signups(self, activity_id):
        assert activity_id == "A1"
        return [
            {"signup_id": "S1", "person_name": "甲", "person_phone": "0911", "plan_summary": "方案A×1", "total_amount": 100, "donation_amount": 20, "is_paid": 1, "payment_receipt_number": "R001"},
            {"signup_id": "S2", "person_name": "乙", "person_phone": "0922", "plan_summary": "方案B×1", "total_amount": 200, "donation_amount": 0, "is_paid": 0, "payment_receipt_number": ""},
            {"signup_id": "S3", "person_name": "丙", "person_phone": "0933", "plan_summary": "方案C×1", "total_amount": 300, "donation_amount": 30, "is_paid": 1, "payment_receipt_number": "R002"},
        ]


def test_signup_stats_include_paid_and_unpaid_amounts(qtbot):
    panel = ActivityDetailPanel(controller=FakeController())
    qtbot.addWidget(panel)

    panel._current_activity_id = "A1"
    panel._reload_signup_tab()

    assert panel.stat_signup_cnt._value_label.text() == "3"
    assert panel.stat_total._value_label.text() == "600"
    assert panel.stat_donation._value_label.text() == "50"
    assert panel.stat_paid_amount._value_label.text() == "400"
    assert panel.stat_unpaid_amount._value_label.text() == "200"


def test_signup_detail_table_header_is_visible_and_labeled(qtbot):
    panel = ActivityDetailPanel(controller=FakeController())
    qtbot.addWidget(panel)

    header = panel.tbl_signups.horizontalHeader()

    assert header.isHidden() is False
    assert header.height() >= 34 or header.minimumHeight() >= 34
    assert panel.tbl_signups.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert [panel.tbl_signups.horizontalHeaderItem(i).text() for i in range(panel.tbl_signups.columnCount())] == [
        "勾選", "收據號", "姓名", "電話", "報名項目", "金額"
    ]


def test_activity_management_signup_stats_has_no_mark_paid_button(qtbot):
    panel = ActivityDetailPanel(controller=FakeController())
    qtbot.addWidget(panel)

    button_texts = [button.text() for button in panel.tab_signup.findChildren(QPushButton)]

    assert "按此繳費" not in button_texts
    assert not hasattr(panel, "btn_mark_paid")


def test_clear_signup_tab_resets_paid_and_unpaid_amounts(qtbot):
    panel = ActivityDetailPanel(controller=FakeController())
    qtbot.addWidget(panel)

    panel._clear_signup_tab()

    assert panel.stat_signup_cnt._value_label.text() == "0"
    assert panel.stat_total._value_label.text() == "0"
    assert panel.stat_donation._value_label.text() == "0"
    assert panel.stat_paid_amount._value_label.text() == "0"
    assert panel.stat_unpaid_amount._value_label.text() == "0"
