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


def test_clear_signup_tab_resets_paid_and_unpaid_amounts(qtbot):
    panel = ActivityDetailPanel(controller=FakeController())
    qtbot.addWidget(panel)

    panel._clear_signup_tab()

    assert panel.stat_signup_cnt._value_label.text() == "0"
    assert panel.stat_total._value_label.text() == "0"
    assert panel.stat_donation._value_label.text() == "0"
    assert panel.stat_paid_amount._value_label.text() == "0"
    assert panel.stat_unpaid_amount._value_label.text() == "0"
