from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout
from .base_person_dialog import BasePersonDialog
from PyQt5.QtCore import QDate

class EditMemberDialog(BasePersonDialog):
    def __init__(self, controller, person_id, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("戶籍家庭成員資料修改作業")
        self.person_id = person_id
        self.fill_data()

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("💾 儲存修改")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout().addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))

    def fill_data(self):
        person = self.controller.get_member_by_id(self.person_id)
        if not person:
            return
        date_obj = QDate.fromString(person["joined_at"], "yyyy-MM-dd")
        self.name_input.setText(person["name"])
        self.gender_input.setCurrentText(person["gender"])
        self.joined_at_input.setDate(date_obj)
        self.birthday_ad_input.setText(person["birthday_ad"])
        self.birthday_lunar_input.setText(person["birthday_lunar"])
        self.lunar_leap_checkbox.setChecked(person["lunar_is_leap"])
        self.identity_input.setCurrentText(person["identity"])
        self.zodiac_input.setText(person["zodiac"])
        self.age_input.setText(str(person["age"]))
        self.birth_time_input.setCurrentText(person["birth_time"])
        self.phone_home_input.setText(person["phone_home"])
        self.phone_mobile_input.setText(person["phone_mobile"])
        self.address_input.setText(person["address"])
        self.zip_code_input.setText(person["zip_code"])
        self.id_input.setText(person["id_number"])
        self.note_input.setText(person["note"])
        self.email_input.setText(person["email"])

    def get_member_data(self):
        data = super().get_data()
        data["id"] = self.person_id
        return data