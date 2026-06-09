from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class PaymentMethodDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        title="確認繳費",
        selected_count=0,
        total_amount=0,
        handler="",
        can_edit_handler=True,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self._payload = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.summary_label = QLabel(f"{int(selected_count or 0)} 筆 / {int(total_amount or 0)} 元")
        self.handler_input = QLineEdit()
        self.handler_input.setText((handler or "").strip())
        self.handler_input.setPlaceholderText("經手人（必填）")
        self.handler_input.setReadOnly(not can_edit_handler)
        if not can_edit_handler:
            self.handler_input.setToolTip("經手人固定為目前登入者")

        self.method_combo = QComboBox()
        self.method_combo.addItem("現金", "cash")
        self.method_combo.addItem("轉帳", "transfer")
        self.method_combo.setMinimumWidth(180)

        self.transfer_last5_input = QLineEdit()
        self.transfer_last5_input.setPlaceholderText("轉帳末5碼")
        self.transfer_last5_input.setVisible(False)
        self.method_combo.currentIndexChanged.connect(self._sync_transfer_field)

        self.receipt_method_combo = QComboBox()
        self.receipt_method_combo.addItem("電子收據", "ELECTRONIC")
        self.receipt_method_combo.addItem("紙本收據", "PAPER")
        self.paper_receipt_number_input = QLineEdit()
        self.paper_receipt_number_input.setPlaceholderText("紙本收據號")
        self.paper_receipt_number_input.setVisible(False)
        self.receipt_method_combo.currentIndexChanged.connect(self._sync_paper_receipt_field)

        form.addRow("本次繳費", self.summary_label)
        form.addRow("經手人", self.handler_input)
        form.addRow("付款方式", self.method_combo)
        form.addRow("轉帳末5碼", self.transfer_last5_input)
        form.addRow("收據型態", self.receipt_method_combo)
        form.addRow("紙本收據號", self.paper_receipt_number_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if ok_button is not None:
            ok_button.setText("確認")
        if cancel_button is not None:
            cancel_button.setText("取消")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _sync_transfer_field(self):
        is_transfer = self.method_combo.currentData() == "transfer"
        self.transfer_last5_input.setVisible(is_transfer)
        if not is_transfer:
            self.transfer_last5_input.clear()

    def _sync_paper_receipt_field(self):
        is_paper = self.receipt_method_combo.currentData() == "PAPER"
        self.paper_receipt_number_input.setVisible(is_paper)
        if not is_paper:
            self.paper_receipt_number_input.clear()

    def _accept_if_valid(self):
        handler = (self.handler_input.text() or "").strip()
        if not handler:
            QMessageBox.information(self, "欄位不足", "請先輸入經手人。")
            return

        method = self.method_combo.currentData() or "cash"
        transfer_last5 = (self.transfer_last5_input.text() or "").strip()
        if method == "transfer" and not transfer_last5:
            QMessageBox.information(self, "欄位不足", "轉帳付款必須填寫末5碼。")
            return

        receipt_method = self.receipt_method_combo.currentData() or "ELECTRONIC"
        paper_receipt_number = (self.paper_receipt_number_input.text() or "").strip()
        if receipt_method == "PAPER" and not paper_receipt_number:
            QMessageBox.information(self, "欄位不足", "紙本收據必須填寫紙本收據號。")
            return

        self._payload = {
            "handler": handler,
            "payment_method": method,
            "transfer_last5": transfer_last5 if method == "transfer" else "",
            "receipt_method": receipt_method,
            "paper_receipt_number": paper_receipt_number if receipt_method == "PAPER" else "",
        }
        self.accept()

    def get_payload(self):
        return dict(self._payload or {})
