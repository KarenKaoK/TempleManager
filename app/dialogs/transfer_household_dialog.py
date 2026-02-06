# app/dialogs/transfer_household_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QHBoxLayout, QPushButton, QMessageBox
)

class TransferHouseholdDialog(QDialog):
    def __init__(self, controller, member: dict, current_head: dict, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.member = member
        self.current_head = current_head
        self.selected_head_person_id = None

        self.setWindowTitle("戶籍變更")
        self.resize(520, 200)

        layout = QVBoxLayout()

        form = QFormLayout()
        self.lbl_member = QLabel(f"{member.get('name','')}（{member.get('phone_mobile','')}）")
        self.lbl_current_head = QLabel(f"{current_head.get('name','')}（{current_head.get('phone_mobile','')}）")

        self.cmb_heads = QComboBox()

        # 排除同戶的戶長，避免選到同一戶
        exclude_household_id = member.get("household_id")
        heads = self.controller.list_active_heads(exclude_household_id=exclude_household_id)

        if not heads:
            self.cmb_heads.addItem("（無可選戶長）", None)
            self.cmb_heads.setEnabled(False)
        else:
            for h in heads:
                text = f"{h.get('name','')}（{h.get('phone_mobile','')}）"
                self.cmb_heads.addItem(text, h.get("head_person_id"))

        form.addRow("搬移對象：", self.lbl_member)
        form.addRow("目前戶長：", self.lbl_current_head)
        form.addRow("目標戶長：", self.cmb_heads)

        layout.addLayout(form)

        # buttons
        btns = QHBoxLayout()
        btns.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_ok = QPushButton("確認變更")

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_ok)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)

        layout.addLayout(btns)
        self.setLayout(layout)

    def _on_ok(self):
        head_person_id = self.cmb_heads.currentData()
        if not head_person_id:
            QMessageBox.warning(self, "無法變更", "請選擇目標戶長")
            return
        self.selected_head_person_id = head_person_id
        self.accept()

    def get_target_head_person_id(self):
        return self.selected_head_person_id
