# edit_member_dialog.py
from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout, QMessageBox

from .base_person_dialog import BasePersonDialog
from app.utils.date_utils import normalize_ymd_text
from app.logging import get_logger, log_data_change, person_snapshot_for_log


_household_logger = get_logger("household")

class EditMemberDialog(BasePersonDialog):
    def __init__(self, controller, person: dict, parent=None):
        super().__init__(controller, parent)
        self.setWindowTitle("修改資料")
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
        self.birthday_ad_input.setText(normalize_ymd_text(p.get("birthday_ad", "")))
        self.birthday_lunar_input.setText(normalize_ymd_text(p.get("birthday_lunar", "")))
        self.lunar_leap_checkbox.setChecked(bool(p.get("lunar_is_leap", 0)))
        self.birth_time_input.setCurrentText(p.get("birth_time", "子"))
        self.age_input.setText("" if p.get("age") is None else str(p.get("age")))
        self.zodiac_input.setText(str(p.get("zodiac", "") or ""))
        self.phone_home_input.setText(p.get("phone_home", ""))
        self.phone_mobile_input.setText(p.get("phone_mobile", ""))
        self.address_input.setText(p.get("address", ""))
        self.zip_code_input.setText(p.get("zip_code", ""))
        self.note_input.setText(p.get("note", ""))

    def on_save_clicked(self):
        payload = self.get_data()
        before_dict = dict(self.person or {})
        try:
            self.controller.update_person(self.person_id, payload)
            actor = getattr(self, "operator_name", None)

            # 完整欄位 before/after（含國曆生日、農曆生日、時辰、年紀、生肖等）
            before = person_snapshot_for_log(before_dict)
            after = person_snapshot_for_log(payload)
            # payload 不含 role/household/status，從 before 補齊
            if "role_in_household" in before_dict:
                after["role_in_household"] = before_dict["role_in_household"]
            if "household_id" in before_dict:
                after["household_id"] = before_dict["household_id"]
            if "status" in before_dict:
                after["status"] = before_dict["status"]

            log_data_change(
                user_id=actor,
                action="修改信眾資料",
                entity="person",
                entity_id=self.person_id,
                before=before,
                after=after,
                extra={"source": "edit_member_dialog"},
            )

            QMessageBox.information(self, "成功", "資料已更新")
            self.accept()
        except Exception as e:
            _household_logger.warning(
                f"[SYSTEM] household - 修改信眾資料失敗 人員ID={self.person_id} 錯誤={e}"
            )
            QMessageBox.warning(self, "錯誤", f"更新失敗：{e}")
