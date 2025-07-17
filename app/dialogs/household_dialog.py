from PyQt5.QtWidgets import QPushButton, QHBoxLayout
from app.dialogs.base_person_dialog import BasePersonDialog
from app.utils.data_transformers import convert_member_to_head_format

class NewHouseholdDialog(BasePersonDialog):
    def __init__(self, controller, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("戶籍戶長新增表單")

        # 確認與關閉按鈕
        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("✅ 存入")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(self.Rejected))

    def get_data(self):
        """轉換為 head_ 開頭格式供 insert_household 使用"""
        base_data = super().get_data()
        return convert_member_to_head_format(base_data)
