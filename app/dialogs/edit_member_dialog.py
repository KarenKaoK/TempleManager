# edit_member_dialog.py
from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout, QMessageBox
from .base_person_dialog import BasePersonDialog

class EditMemberDialog(BasePersonDialog):
    def __init__(self, controller, person: dict, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("修改成員資料")
        self.person = person
        self.person_id = person["id"]

        self._fill(person)

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("💾 儲存修改")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.on_save_clicked)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))

    def _fill(self, p: dict):
        self.name_input.setText(p.get("name", ""))
        self.gender_input.setCurrentText(p.get("gender", "男"))
        self.birthday_ad_input.setText(p.get("birthday_ad", ""))
        self.birthday_lunar_input.setText(p.get("birthday_lunar", ""))
        self.lunar_leap_checkbox.setChecked(bool(p.get("lunar_is_leap", 0)))
        self.birth_time_input.setCurrentText(p.get("birth_time", "子"))
        self.phone_home_input.setText(p.get("phone_home", ""))
        self.phone_mobile_input.setText(p.get("phone_mobile", ""))
        self.address_input.setText(p.get("address", ""))
        self.zip_code_input.setText(p.get("zip_code", ""))
        self.note_input.setText(p.get("note", ""))

    def on_save_clicked(self):
        payload = self.get_data()
        try:
            self.controller.update_person(self.person_id, payload)
            QMessageBox.information(self, "成功", "資料已更新")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"更新失敗：{e}")
