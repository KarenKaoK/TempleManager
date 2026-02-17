import random
import string

from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)


class AccountManagementDialog(QDialog):
    def __init__(self, controller, actor_username: str, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.actor_username = actor_username
        self.setWindowTitle("帳號管理")
        self.resize(1160, 740)
        self._build_ui()
        self.reload_users()
        self.reload_settings()

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(QLabel("帳號列表"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["帳號", "角色", "狀態", "建立時間", "最近改密碼", "最近登入"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setMinimumHeight(360)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 220)
        self.table.setColumnWidth(4, 220)
        self.table.setColumnWidth(5, 220)
        root.addWidget(self.table, 3)

        action_row = QHBoxLayout()
        self.btn_create = QPushButton("新增帳號")
        self.btn_reset = QPushButton("重設密碼")
        self.btn_toggle = QPushButton("停用/啟用")
        self.btn_delete = QPushButton("刪除帳號")
        self.btn_refresh = QPushButton("重新整理")
        self.btn_create.clicked.connect(self.create_user)
        self.btn_reset.clicked.connect(self.reset_password)
        self.btn_toggle.clicked.connect(self.toggle_active)
        self.btn_delete.clicked.connect(self.delete_user)
        self.btn_refresh.clicked.connect(self.reload_users)
        action_row.addWidget(self.btn_create)
        action_row.addWidget(self.btn_reset)
        action_row.addWidget(self.btn_toggle)
        action_row.addWidget(self.btn_delete)
        action_row.addWidget(self.btn_refresh)
        action_row.addStretch()
        root.addLayout(action_row)

        root.addWidget(QLabel("安全設定"))
        settings_box = QWidget()
        form = QFormLayout(settings_box)
        self.reminder_days = QSpinBox()
        self.reminder_days.setRange(0, 365)
        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(0, 240)
        form.addRow("密碼提醒天數（0=關閉）", self.reminder_days)
        form.addRow("閒置自動登出分鐘", self.idle_minutes)
        root.addWidget(settings_box)

        footer = QHBoxLayout()
        self.btn_save_settings = QPushButton("儲存安全設定")
        self.btn_save_settings.clicked.connect(self.save_settings)
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        footer.addStretch()
        footer.addWidget(self.btn_save_settings)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def reload_users(self):
        users = self.controller.list_users()
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            status_text = "啟用" if int(u.get("is_active") or 0) == 1 else "停用"
            values = [
                str(u.get("username") or ""),
                str(u.get("role") or ""),
                status_text,
                str(u.get("created_at") or ""),
                str(u.get("password_changed_at") or ""),
                str(u.get("last_login_at") or ""),
            ]
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                self.table.setItem(i, j, item)

    def reload_settings(self):
        self.reminder_days.setValue(self.controller.get_password_reminder_days())
        self.idle_minutes.setValue(self.controller.get_idle_logout_minutes())

    def save_settings(self):
        self.controller.save_security_settings(self.reminder_days.value(), self.idle_minutes.value())
        QMessageBox.information(self, "成功", "安全設定已儲存")

    def _selected_username(self) -> str:
        r = self.table.currentRow()
        if r < 0:
            return ""
        item = self.table.item(r, 0)
        return item.text().strip() if item else ""

    def _selected_is_active(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 2)
        if not item:
            return None
        return item.text() == "啟用"

    def create_user(self):
        username, ok = QInputDialog.getText(self, "新增帳號", "帳號")
        if not ok:
            return
        username = (username or "").strip()
        if not username:
            QMessageBox.warning(self, "錯誤", "帳號不可空白")
            return
        role, ok = QInputDialog.getItem(self, "新增帳號", "角色", ["會計", "工作人員", "管理員"], 0, False)
        if not ok:
            return
        mode, ok = QInputDialog.getItem(
            self, "新增帳號", "密碼設定方式", ["管理員手動輸入", "系統產生臨時密碼"], 0, False
        )
        if not ok:
            return
        try:
            if mode == "系統產生臨時密碼":
                password = self._generate_temp_password()
                self.controller.create_user_account(self.actor_username, username, password, role)
                QMessageBox.information(
                    self,
                    "成功",
                    f"已建立帳號：{username}\n臨時密碼：{password}\n請妥善交付使用者。",
                )
            else:
                password, ok = QInputDialog.getText(self, "新增帳號", "初始密碼", QLineEdit.Password)
                if not ok:
                    return
                self.controller.create_user_account(self.actor_username, username, password, role)
                QMessageBox.information(self, "成功", f"已建立帳號：{username}")
            self.reload_users()
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))

    def _generate_temp_password(self, length: int = 8) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(max(6, length)))

    def reset_password(self):
        username = self._selected_username()
        if not username:
            QMessageBox.warning(self, "提示", "請先選取帳號")
            return
        mode, ok = QInputDialog.getItem(
            self, "重設密碼", "重設方式", ["管理員手動輸入", "系統產生臨時密碼"], 0, False
        )
        if not ok:
            return
        try:
            if mode == "系統產生臨時密碼":
                new_pw = self._generate_temp_password()
                self.controller.reset_user_password(self.actor_username, username, new_pw, mode="auto")
                QMessageBox.information(self, "重設成功", f"帳號：{username}\n臨時密碼：{new_pw}\n請妥善交付使用者。")
            else:
                new_pw, ok = QInputDialog.getText(self, "重設密碼", "請輸入新臨時密碼", QLineEdit.Password)
                if not ok:
                    return
                self.controller.reset_user_password(self.actor_username, username, new_pw, mode="manual")
                QMessageBox.information(self, "重設成功", f"帳號：{username}\n密碼已更新。")
            self.reload_users()
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))

    def toggle_active(self):
        username = self._selected_username()
        if not username:
            QMessageBox.warning(self, "提示", "請先選取帳號")
            return
        current = self._selected_is_active()
        if current is None:
            return
        target = not current
        action_text = "啟用" if target else "停用"
        reply = QMessageBox.question(self, "確認", f"確定要{action_text}帳號 {username} 嗎？")
        if reply != QMessageBox.Yes:
            return
        try:
            self.controller.toggle_user_active(self.actor_username, username, target)
            self.reload_users()
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))

    def delete_user(self):
        username = self._selected_username()
        if not username:
            QMessageBox.warning(self, "提示", "請先選取帳號")
            return
        if username == self.actor_username:
            QMessageBox.warning(self, "限制", "不可刪除目前登入中的管理員帳號")
            return
        reply = QMessageBox.question(self, "確認刪除", f"確定要刪除帳號 {username} 嗎？此動作不可復原。")
        if reply != QMessageBox.Yes:
            return
        try:
            self.controller.delete_user_account(self.actor_username, username)
            QMessageBox.information(self, "成功", f"已刪除帳號：{username}")
            self.reload_users()
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))
