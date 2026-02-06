# base_person_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QCheckBox
)

class BasePersonDialog(QDialog):
    """
    required:
      name, gender, phone_mobile, birthday_ad, birthday_lunar, birth_time, address
    optional:
      phone_home, zip_code, note, lunar_is_leap
    """

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setFixedSize(600, 420)

        layout = QVBoxLayout()
        form = QGridLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.gender_input = QComboBox()
        self.gender_input.addItems(["男", "女", "其他"])

        self.birthday_ad_input = QLineEdit()
        self.birthday_lunar_input = QLineEdit()
        self.lunar_leap_checkbox = QCheckBox("農曆生日為閏月")

        self.birth_time_input = QComboBox()
        self.birth_time_input.addItems(["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "吉時"])

        self.phone_home_input = QLineEdit()
        self.phone_mobile_input = QLineEdit()
        self.address_input = QLineEdit()
        self.zip_code_input = QLineEdit()
        self.note_input = QLineEdit()

        # row 0
        form.addWidget(QLabel("姓名："), 0, 0)
        form.addWidget(self.name_input, 0, 1)
        form.addWidget(QLabel("性別："), 0, 2)
        form.addWidget(self.gender_input, 0, 3)

        # row 1
        form.addWidget(QLabel("國曆生日："), 1, 0)
        form.addWidget(self.birthday_ad_input, 1, 1)
        form.addWidget(QLabel("出生時辰："), 1, 2)
        form.addWidget(self.birth_time_input, 1, 3)

        # row 2
        form.addWidget(QLabel("農曆生日："), 2, 0)
        form.addWidget(self.birthday_lunar_input, 2, 1)
        form.addWidget(self.lunar_leap_checkbox, 2, 2, 1, 2)

        # row 3
        form.addWidget(QLabel("聯絡電話："), 3, 0)
        form.addWidget(self.phone_home_input, 3, 1)
        form.addWidget(QLabel("手機號碼："), 3, 2)
        form.addWidget(self.phone_mobile_input, 3, 3)

        # row 4
        form.addWidget(QLabel("地址："), 4, 0)
        form.addWidget(self.address_input, 4, 1, 1, 3)

        # row 5
        form.addWidget(QLabel("郵遞區號："), 5, 0)
        form.addWidget(self.zip_code_input, 5, 1)
        form.addWidget(QLabel("備註："), 5, 2)
        form.addWidget(self.note_input, 5, 3)

        layout.addLayout(form)
        self.setLayout(layout)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "gender": self.gender_input.currentText(),
            "birthday_ad": self.birthday_ad_input.text().strip(),
            "birthday_lunar": self.birthday_lunar_input.text().strip(),
            "lunar_is_leap": 1 if self.lunar_leap_checkbox.isChecked() else 0,
            "birth_time": self.birth_time_input.currentText(),
            "phone_home": self.phone_home_input.text().strip(),
            "phone_mobile": self.phone_mobile_input.text().strip(),
            "address": self.address_input.text().strip(),
            "zip_code": self.zip_code_input.text().strip(),
            "note": self.note_input.text().strip(),
        }
