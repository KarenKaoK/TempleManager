# app/dialogs/member_dialog.py

from .base_person_dialog import BasePersonDialog

class MemberDialog(BasePersonDialog):
    def __init__(self, controller, parent=None, data=None):
        super().__init__(controller, parent)
        self.setWindowTitle("戶籍家庭成員資料新增作業" if data is None else "戶籍家庭成員資料修改作業")

        # 載入資料（for 編輯）
        if data:
            self.populate_data(data)

        # 按鈕行為
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(self.Rejected))

    def populate_data(self, data: dict):
        """編輯時填入既有資料"""
        self.name_input.setText(data.get("name", ""))
        self.gender_input.setCurrentText(data.get("gender", "男"))
        self.joined_at_input.setDate(QDate.fromString(data.get("joined_at", ""), "yyyy-MM-dd"))
        self.birthday_ad_input.setText(data.get("birthday_ad", ""))
        self.birthday_lunar_input.setText(data.get("birthday_lunar", ""))
        self.lunar_leap_checkbox.setChecked(data.get("lunar_is_leap", False))
        self.identity_input.setCurrentText(data.get("identity", ""))
        self.zodiac_input.setText(data.get("zodiac", ""))
        self.age_input.setText(str(data.get("age", "")))
        self.birth_time_input.setCurrentText(data.get("birth_time", "子"))
        self.phone_home_input.setText(data.get("phone_home", ""))
        self.phone_mobile_input.setText(data.get("phone_mobile", ""))
        self.address_input.setText(data.get("address", ""))
        self.zip_code_input.setText(data.get("zip_code", ""))
        self.id_input.setText(data.get("id_number", ""))
        self.note_input.setText(data.get("note", ""))
        self.email_input.setText(data.get("email", ""))
