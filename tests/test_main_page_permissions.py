from app.widgets.main_page import MainPageWidget


class _FakeController:
    def get_all_people(self):
        return []

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
