from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout
from .base_person_dialog import BasePersonDialog

class NewMemberDialog(BasePersonDialog):
    def __init__(self, controller, household_id, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("戶籍家庭成員資料新增作業")
        self.household_id = household_id

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("✅ 存入")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))

    def get_member_data(self):
        data = super().get_data()
        data["household_id"] = self.household_id
        return data
