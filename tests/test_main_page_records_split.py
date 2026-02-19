from app.widgets.main_page import MainPageWidget


class _FakeController:
    def __init__(self):
        self.rows = []

    def get_all_people(self):
        return []

    def get_income_transactions_by_person(self, person_id: str):
        return list(self.rows)


def test_income_records_split_into_donation_activity_light_tabs(qtbot):
    controller = _FakeController()
    controller.rows = [
        {
            "id": 1,
            "date": "2026-02-20",
            "category_id": "01",
            "category_name": "香油錢",
            "amount": 100,
            "handler": "A",
            "receipt_number": "R001",
            "note": "",
        },
        {
            "id": 2,
            "date": "2026-02-21",
            "category_id": "90",
            "category_name": "活動收入",
            "amount": 200,
            "handler": "B",
            "receipt_number": "R002",
            "note": "",
        },
        {
            "id": 3,
            "date": "2026-02-22",
            "category_id": "91",
            "category_name": "點燈收入",
            "amount": 300,
            "handler": "C",
            "receipt_number": "R003",
            "note": "",
        },
    ]

    page = MainPageWidget(controller)
    qtbot.addWidget(page)
    page._refresh_donation_records({"id": "P001", "name": "王小明"})

    assert page.donation_table.rowCount() == 1
    assert page.activity_table.rowCount() == 1
    assert page.light_table.rowCount() == 1
    assert "共 1 筆" in page.donation_summary_label.text()
    assert "共 1 筆" in page.activity_summary_label.text()
    assert "共 1 筆" in page.light_summary_label.text()
