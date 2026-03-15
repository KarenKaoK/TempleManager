from unittest.mock import MagicMock
from PyQt5.QtWidgets import QDialog
from app.widgets.main_page import MainPageWidget


class _FakeController:
    def get_all_people(self):
        return []

    def get_income_transactions_by_person(self, person_id: str):
        return []


class _EditableFakeController:
    def __init__(self):
        self.people = [
            {
                "id": "H1-HEAD",
                "household_id": "H1",
                "role_in_household": "HEAD",
                "name": "戶長甲",
                "gender": "男",
                "birthday_ad": "1980/01/01",
                "birthday_lunar": "1979/11/15",
                "lunar_is_leap": 0,
                "birth_time": "子",
                "age": 46,
                "zodiac": "猴",
                "phone_home": "",
                "phone_mobile": "0911000000",
                "address": "台北",
                "zip_code": "",
                "note": "",
                "joined_at": "2026-01-01",
                "status": "ACTIVE",
            },
            {
                "id": "H1-M1",
                "household_id": "H1",
                "role_in_household": "MEMBER",
                "name": "成員甲",
                "gender": "女",
                "birthday_ad": "1990/02/02",
                "birthday_lunar": "1990/01/07",
                "lunar_is_leap": 0,
                "birth_time": "午",
                "age": 37,
                "zodiac": "馬",
                "phone_home": "",
                "phone_mobile": "0922000000",
                "address": "台北",
                "zip_code": "",
                "note": "",
                "joined_at": "2026-01-02",
                "status": "ACTIVE",
            },
        ]

    def get_all_people(self):
        return sorted(self.people, key=lambda p: p["joined_at"], reverse=True)

    def list_people_by_household(self, household_id: str, status: str = "ACTIVE"):
        rows = [p for p in self.people if p["household_id"] == household_id]
        if status != "ALL":
            rows = [p for p in rows if p["status"] == status]
        rows.sort(key=lambda p: (0 if p["role_in_household"] == "HEAD" else 1, p["joined_at"]))
        return [dict(p) for p in rows]

    def get_income_transactions_by_person(self, person_id: str):
        return []


def test_staff_cannot_edit_member_or_delete_head_buttons(qtbot):
    page = MainPageWidget(_FakeController(), user_role="工作人員")
    qtbot.addWidget(page)

    assert page.delete_btn.isEnabled() is False
    assert page.restore_btn.isEnabled() is False
    assert page.delete_btn.toolTip() == "目前角色無權限刪除戶長。"
    assert page.restore_btn.toolTip() == "僅管理員可恢復停用資料。"
    for label in [
        "🖊 修改成員",
        "❌ 刪除成員",
        "🧾 分戶成新戶長",
        "🔄 變更戶長",
        "⬆ 上移",
        "⬇ 下移",
    ]:
        assert page.member_buttons[label].isEnabled() is False
        assert page.member_buttons[label].toolTip() == "目前角色無權限執行此操作。"


def test_accountant_can_edit_member_or_delete_head_buttons(qtbot):
    page = MainPageWidget(_FakeController(), user_role="會計")
    qtbot.addWidget(page)

    assert page.delete_btn.isEnabled() is True
    # 恢復停用資料維持僅管理員可操作
    assert page.restore_btn.isEnabled() is False
    for label in [
        "🖊 修改成員",
        "❌ 刪除成員",
        "🧾 分戶成新戶長",
        "🔄 變更戶長",
        "⬆ 上移",
        "⬇ 下移",
    ]:
        assert page.member_buttons[label].isEnabled() is True


def test_edit_member_refreshes_current_household_only(qtbot, monkeypatch):
    controller = _EditableFakeController()
    page = MainPageWidget(controller, user_role="會計")
    qtbot.addWidget(page)

    class _AcceptedEditDialog:
        def __init__(self, controller, person, parent=None):
            self.controller = controller
            self.person = person

        def exec_(self):
            for row in self.controller.people:
                if row["id"] == self.person["id"]:
                    row["name"] = "成員甲-已修改"
                    break
            return QDialog.Accepted

    monkeypatch.setattr("app.widgets.main_page.EditMemberDialog", _AcceptedEditDialog)
    page.refresh_all_panels = MagicMock()

    page.member_table.selectRow(1)
    page.on_edit_member_clicked()

    assert page.refresh_all_panels.called is False
    assert page.member_table.item(1, 0).text() == "成員甲-已修改"

    household_names = [
        page.household_table.item(r, 1).text()
        for r in range(page.household_table.rowCount())
        if page.household_table.item(r, 1) is not None
    ]
    assert "成員甲-已修改" in household_names
