from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, QTabWidget, QTableWidgetItem,
    QDialog, QMessageBox, QComboBox, QDateEdit, QCheckBox
)
from PyQt5.QtCore import QDate

class NewHouseholdDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller 
        self.setWindowTitle("戶籍戶長新增表單")
        self.setFixedSize(600, 500)

        layout = QVBoxLayout()
        form = QGridLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.gender_input = QComboBox()
        self.gender_input.addItems(["男", "女"])

        self.joined_at_input = QDateEdit()
        self.joined_at_input.setDate(QDate.currentDate())
        self.joined_at_input.setCalendarPopup(True)

        self.birthday_ad_input = QLineEdit()
        self.birthday_lunar_input = QLineEdit()
        self.lunar_leap_checkbox = QCheckBox("農曆生日為閏月")

        self.identity_input = QComboBox()
        self.load_identities()

        self.age_input = QLineEdit()
        self.zodiac_input = QLineEdit()
        self.birth_time_input = QComboBox()
        self.birth_time_input.addItems(["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"])

        self.phone_home_input = QLineEdit()
        self.phone_mobile_input = QLineEdit()

        self.address_input = QLineEdit()
        self.zip_code_input = QLineEdit()
        self.id_input = QLineEdit()

        self.note_input = QLineEdit()
        self.email_input = QLineEdit()

        form.addWidget(QLabel("姓名："), 0, 0)
        form.addWidget(self.name_input, 0, 1)
        form.addWidget(QLabel("加入日期："), 0, 2)
        form.addWidget(self.joined_at_input, 0, 3)

        form.addWidget(QLabel("國曆生日："), 1, 0)
        form.addWidget(self.birthday_ad_input, 1, 1)
        form.addWidget(QLabel("性別："), 1, 2)
        form.addWidget(self.gender_input, 1, 3)

        form.addWidget(QLabel("農曆生日："), 2, 0)
        form.addWidget(self.birthday_lunar_input, 2, 1)
        form.addWidget(self.lunar_leap_checkbox, 2, 2)

        form.addWidget(QLabel("身份："), 3, 0)
        form.addWidget(self.identity_input, 3, 1)
        form.addWidget(QLabel("生肖："), 3, 2)
        form.addWidget(self.zodiac_input, 3, 3)

        form.addWidget(QLabel("年齡："), 4, 0)
        form.addWidget(self.age_input, 4, 1)
        form.addWidget(QLabel("出生時辰："), 4, 2)
        form.addWidget(self.birth_time_input, 4, 3)

        form.addWidget(QLabel("聯絡電話："), 5, 0)
        form.addWidget(self.phone_home_input, 5, 1)
        form.addWidget(QLabel("手機號碼："), 5, 2)
        form.addWidget(self.phone_mobile_input, 5, 3)

        form.addWidget(QLabel("信眾地址："), 6, 0)
        form.addWidget(self.address_input, 6, 1, 1, 3)

        form.addWidget(QLabel("郵遞區號："), 7, 0)
        form.addWidget(self.zip_code_input, 7, 1)
        form.addWidget(QLabel("身分證號："), 7, 2)
        form.addWidget(self.id_input, 7, 3)

        form.addWidget(QLabel("備註說明："), 8, 0)
        form.addWidget(self.note_input, 8, 1, 1, 3)

        form.addWidget(QLabel("電子郵件："), 9, 0)
        form.addWidget(self.email_input, 9, 1, 1, 3)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("✅ 存入")
        self.cancel_btn = QPushButton("❌ 關閉")
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(lambda: self.done(QDialog.Rejected))

    def get_data(self):
        return {
            "head_name": self.name_input.text(),
            "head_gender": self.gender_input.currentText(),
            "head_joined_at": self.joined_at_input.date().toString("yyyy-MM-dd"),
            "head_birthday_ad": self.birthday_ad_input.text(),
            "head_birthday_lunar": self.birthday_lunar_input.text(),
            "head_lunar_is_leap": self.lunar_leap_checkbox.isChecked(),
            "head_identity": self.identity_input.currentText(),
            "head_zodiac": self.zodiac_input.text(),
            "head_age": self.age_input.text(),
            "head_birth_time": self.birth_time_input.currentText(),
            "head_phone_home": self.phone_home_input.text(),
            "head_phone_mobile": self.phone_mobile_input.text(),
            "head_address": self.address_input.text(),
            "head_zip_code": self.zip_code_input.text(),
            "head_id_number": self.id_input.text(),
            "head_note": self.note_input.text(),
            "head_email": self.email_input.text()
        }
    def load_identities(self):
        self.identity_input.clear()
        identities = self.controller.get_all_member_identities()
        for item in identities:
            self.identity_input.addItem(item["name"], item["id"])
