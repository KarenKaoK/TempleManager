# new_household_dialog.py
from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout

from .base_person_dialog import BasePersonDialog

class NewHouseholdDialog(BasePersonDialog):
    def __init__(self, controller, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("新增戶籍資料（戶長資料）")

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("✅ 存入")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))
