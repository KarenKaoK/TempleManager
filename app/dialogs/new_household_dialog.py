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

        self.confirm_btn.clicked.connect(self.save_data)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))

    def save_data(self):
        data = self.get_data()
        
        # 簡易檢查
        if not data.get("name"):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "錯誤", "姓名為必填欄位")
            return

        try:
            # 呼叫 Controller 建立新戶籍 (回傳 person_id, household_id)
            person_id, household_id = self.controller.create_household(data)
            
            # 存起來供外部存取
            self.created_person_id = person_id
            self.created_household_id = household_id
            self.created_name = data.get("name", "")
            self.created_phone_mobile = data.get("phone_mobile", "")
            
            # QMessageBox.information(self, "成功", "建立成功！")
            self.accept()
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "錯誤", f"建立失敗: {str(e)}")
