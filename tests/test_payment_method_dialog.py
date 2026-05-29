from unittest.mock import patch

from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from app.dialogs.payment_method_dialog import PaymentMethodDialog


def test_payment_dialog_handler_is_readonly_when_not_editable(qtbot):
    dlg = PaymentMethodDialog(handler="王小明(admin)", can_edit_handler=False)
    qtbot.addWidget(dlg)

    assert dlg.handler_input.text() == "王小明(admin)"
    assert dlg.handler_input.isReadOnly() is True
    assert dlg.method_combo.minimumWidth() >= 180
    assert dlg.minimumWidth() >= 360
    assert dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).text() == "確認"
    assert dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.Cancel).text() == "取消"


def test_payment_dialog_accepts_cash_payload(qtbot):
    dlg = PaymentMethodDialog(handler="王小明(admin)", can_edit_handler=False)
    qtbot.addWidget(dlg)

    dlg._accept_if_valid()

    assert dlg.result() == QDialog.Accepted
    assert dlg.get_payload() == {
        "handler": "王小明(admin)",
        "payment_method": "cash",
        "transfer_last5": "",
    }


def test_payment_dialog_requires_transfer_tail(qtbot):
    dlg = PaymentMethodDialog(handler="王小明(admin)", can_edit_handler=False)
    qtbot.addWidget(dlg)
    dlg.method_combo.setCurrentIndex(dlg.method_combo.findData("transfer"))

    with patch("app.dialogs.payment_method_dialog.QMessageBox.information") as mock_info:
        dlg._accept_if_valid()

    mock_info.assert_called_once()
    assert dlg.result() == 0
    assert dlg.get_payload() == {}


def test_payment_dialog_accepts_transfer_payload(qtbot):
    dlg = PaymentMethodDialog(handler="王小明(admin)", can_edit_handler=False)
    qtbot.addWidget(dlg)
    dlg.method_combo.setCurrentIndex(dlg.method_combo.findData("transfer"))
    dlg.transfer_last5_input.setText("A1234")

    dlg._accept_if_valid()

    assert dlg.result() == QDialog.Accepted
    assert dlg.get_payload() == {
        "handler": "王小明(admin)",
        "payment_method": "transfer",
        "transfer_last5": "A1234",
    }
