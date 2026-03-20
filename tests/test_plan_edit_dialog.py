from app.dialogs.plan_edit_dialog import PlanEditDialog


class DummyController:
    pass


def test_plan_edit_dialog_collect_payload_commits_typed_fixed_amount(qtbot):
    dialog = PlanEditDialog(DummyController(), mode="new", activity_id="A1")
    qtbot.addWidget(dialog)

    dialog.f_name.setText("方案A")
    dialog.tbl_items.item(0, 0).setText("項目1")
    dialog.tbl_items.item(0, 1).setText("1")
    dialog.f_amount.lineEdit().setText("1234")

    payload = dialog._collect_payload()

    assert payload is not None
    assert payload["fee_type"] == "fixed"
    assert payload["amount"] == 1234
