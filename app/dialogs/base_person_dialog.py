# base_person_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QCheckBox, QMessageBox, QWidget
)

from app.utils.lunar_solar_converter import solar_to_lunar, lunar_to_solar


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

        # ✅ 新增兩顆按鈕
        self.btn_to_lunar = QPushButton("轉農曆")
        self.btn_to_ad = QPushButton("轉國曆")
        self.btn_to_lunar.setFixedWidth(80)
        self.btn_to_ad.setFixedWidth(80)

        self.birth_time_input = QComboBox()
        self.birth_time_input.addItems(["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "吉時"])

        self.phone_home_input = QLineEdit()
        self.phone_mobile_input = QLineEdit()
        self.address_input = QLineEdit()
        self.zip_code_input = QLineEdit()
        self.note_input = QLineEdit()

        # ✅ 把生日欄位變成「輸入框 + 按鈕」
        ad_wrap = QWidget()
        ad_h = QHBoxLayout(ad_wrap)
        ad_h.setContentsMargins(0, 0, 0, 0)
        ad_h.addWidget(self.birthday_ad_input, 1)
        ad_h.addWidget(self.btn_to_lunar)

        lunar_wrap = QWidget()
        lunar_h = QHBoxLayout(lunar_wrap)
        lunar_h.setContentsMargins(0, 0, 0, 0)
        lunar_h.addWidget(self.birthday_lunar_input, 1)
        lunar_h.addWidget(self.btn_to_ad)

        # row 0
        form.addWidget(QLabel("姓名："), 0, 0)
        form.addWidget(self.name_input, 0, 1)
        form.addWidget(QLabel("性別："), 0, 2)
        form.addWidget(self.gender_input, 0, 3)

        # row 1
        form.addWidget(QLabel("國曆生日："), 1, 0)
        form.addWidget(ad_wrap, 1, 1)
        form.addWidget(QLabel("出生時辰："), 1, 2)
        form.addWidget(self.birth_time_input, 1, 3)

        # row 2
        form.addWidget(QLabel("農曆生日："), 2, 0)
        form.addWidget(lunar_wrap, 2, 1)
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

        # ✅ 綁事件
        self.btn_to_lunar.clicked.connect(self.on_convert_to_lunar_clicked)
        self.btn_to_ad.clicked.connect(self.on_convert_to_ad_clicked)

    def _confirm_overwrite(self, field_name: str) -> bool:
        ret = QMessageBox.question(
            self,
            "覆寫確認",
            f"{field_name}已經有填寫內容，是否要用換算結果覆蓋？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return ret == QMessageBox.Yes

    def on_convert_to_lunar_clicked(self):
        solar = self.birthday_ad_input.text().strip()
        if not solar:
            QMessageBox.warning(self, "提示", "請先填寫國曆生日（YYYY-MM-DD）")
            return

        try:
            lunar_str, is_leap = solar_to_lunar(solar)
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"換算失敗：{e}")
            return

        if self.birthday_lunar_input.text().strip():
            if not self._confirm_overwrite("農曆生日"):
                return

        self.birthday_lunar_input.setText(lunar_str)
        self.lunar_leap_checkbox.setChecked(bool(is_leap))
        QMessageBox.information(self, "完成", "已換算並填入農曆生日")

    def on_convert_to_ad_clicked(self):
        lunar = self.birthday_lunar_input.text().strip()
        if not lunar:
            QMessageBox.warning(self, "提示", "請先填寫農曆生日（YYYY-MM-DD）")
            return

        is_leap = 1 if self.lunar_leap_checkbox.isChecked() else 0

        try:
            solar_str = lunar_to_solar(lunar, is_leap=is_leap)
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"換算失敗：{e}")
            return

        if self.birthday_ad_input.text().strip():
            if not self._confirm_overwrite("國曆生日"):
                return

        self.birthday_ad_input.setText(solar_str)
        QMessageBox.information(self, "完成", "已換算並填入國曆生日")

    def _warn_if_inconsistent(self) -> bool:
        """
        兩邊都有填時，若不一致：提醒但不阻擋（回傳 True 表示繼續）
        """
        solar = self.birthday_ad_input.text().strip()
        lunar = self.birthday_lunar_input.text().strip()
        if not solar or not lunar:
            return True

        try:
            calc_lunar, calc_is_leap = solar_to_lunar(solar)
        except Exception:
            # 算不出來就不要擋
            return True

        cur_is_leap = 1 if self.lunar_leap_checkbox.isChecked() else 0

        if calc_lunar != lunar or int(calc_is_leap) != int(cur_is_leap):
            QMessageBox.information(
                self,
                "提醒",
                "你填的國曆換算農曆，與目前農曆欄位不一致。\n"
                "若以當事人說的為準可直接存入；若要同步可按『轉農曆/轉國曆』。"
            )
        return True

    def get_data(self):
        # 存入前提醒（不阻擋）
        self._warn_if_inconsistent()

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
