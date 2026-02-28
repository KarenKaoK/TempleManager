import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QLabel, QLineEdit, QFormLayout, QSpinBox, QInputDialog,
    QHeaderView
)
from app.config import DB_NAME

class IncomeSetupDialog(QDialog):
    """收入項目建檔作業 視窗"""
    def __init__(self, db_path=None, user_role=None):
        super().__init__()
        from app.config import DB_NAME
        self.db_path = db_path or DB_NAME  # ✅ 預設為原本的 DB_NAME
        self.user_role = user_role

        self.setWindowTitle("收入項目建檔作業")
        self.resize(760, 460)
        self.setMinimumSize(680, 400)

        # 主佈局
        layout = QVBoxLayout()

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["收入項目代號", "收入項目名稱", "捐助金額", "狀態"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # 按鈕區域
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("資料新增")
        self.btn_edit = QPushButton("資料修改")
        self.btn_delete = QPushButton("停用/啟用")
        self.btn_close = QPushButton("關閉返回")

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_close)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 綁定事件（確保所有方法已定義）
        self.btn_add.clicked.connect(self.add_income_item)
        self.btn_edit.clicked.connect(self.edit_income_item)
        self.btn_delete.clicked.connect(self.delete_income_item)  # ✅ 確保方法名稱正確
        self.btn_close.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self._sync_toggle_button_text)

        # 載入資料
        self.load_data()

    def _can_toggle_active(self):
        role = (self.user_role or "").strip()
        if not role:
            return True
        return role in {"管理員", "會計", "會計人員"}

    def _can_maintain_items(self):
        return self._can_toggle_active()

    def load_data(self):
        """從 SQLite 載入收入項目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, CAST(amount AS INTEGER), COALESCE(is_active, 1)
            FROM income_items
            ORDER BY id
        """)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row[1])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row[2])))
            status_text = "啟用" if int(row[3] or 0) == 1 else "停用"
            self.table.setItem(row_idx, 3, QTableWidgetItem(status_text))
        self._sync_toggle_button_text()

    def _sync_toggle_button_text(self):
        can_maintain = self._can_maintain_items()
        self.btn_add.setEnabled(can_maintain)
        self.btn_edit.setEnabled(can_maintain)

        if not self._can_toggle_active():
            self.btn_delete.setText("停用/啟用")
            self.btn_delete.setEnabled(False)
            return

        self.btn_delete.setEnabled(True)
        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.btn_delete.setText("停用/啟用")
            return

        status_item = self.table.item(selected_row, 3)
        if not status_item:
            self.btn_delete.setText("停用/啟用")
            return

        self.btn_delete.setText("啟用" if status_item.text() == "停用" else "停用")
    def add_income_item(self):
        """新增收入項目（一次輸入完整資料）"""
        if not self._can_maintain_items():
            QMessageBox.warning(self, "權限不足", "目前角色無權限新增收入項目。")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("新增收入項目")
        layout = QFormLayout()

        next_id = self._generate_next_item_id()
        id_label = QLabel(next_id)
        name_input = QLineEdit()
        amount_input = QSpinBox()  # ✅ 設定為整數輸入框
        amount_input.setMinimum(0)  
        amount_input.setMaximum(1000000000)  

        layout.addRow("收入項目代號：", id_label)
        layout.addRow("收入項目名稱：", name_input)
        layout.addRow("捐助金額：", amount_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_add_income_item(dialog, next_id, name_input.text(), amount_input.value()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def _generate_next_item_id(self):
        """產生下一個兩位數代號（01, 02, ...）。"""
        reserved_ids = {"90", "91"}  # 系統保留項目：活動收入 / 點燈收入
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM income_items")
        rows = cursor.fetchall()
        conn.close()

        max_num = 0
        for (raw_id,) in rows:
            sid = str(raw_id or "").strip()
            if not sid:
                continue
            if sid.isdigit():
                if sid in reserved_ids:
                    continue
                max_num = max(max_num, int(sid))
                continue

            # 相容舊資料（例如 I01 / INCOME-03）：取尾端數字
            tail_digits = ""
            for ch in reversed(sid):
                if ch.isdigit():
                    tail_digits = ch + tail_digits
                else:
                    break
            if tail_digits:
                if tail_digits in reserved_ids:
                    continue
                max_num = max(max_num, int(tail_digits))

        return f"{max_num + 1:02d}"

    def confirm_add_income_item(self, dialog, id, name, amount):
        """確認並新增收入項目"""
        id = id.strip()  # ✅ 確保 ID 不能是空白
        if not id:
            QMessageBox.warning(self, "錯誤", "收入項目代號不可為空！")
            return

        if not name.strip():
            QMessageBox.warning(self, "錯誤", "請填寫收入項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 🔍 檢查 ID 是否已存在
        cursor.execute("SELECT id FROM income_items WHERE id = ?", (id,))
        if cursor.fetchone():
            QMessageBox.warning(self, "錯誤", f"收入項目代號 {id} 已存在，請輸入其他代號！")
            conn.close()
            return

        try:
            cursor.execute(
                "INSERT INTO income_items (id, name, amount, is_active) VALUES (?, ?, ?, 1)",
                (id, name, int(amount))
            )
            conn.commit()
            QMessageBox.information(self, "成功", "收入項目新增成功！")
            self.load_data()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "錯誤", "收入項目新增失敗！")
        finally:
            conn.close()

        dialog.accept()  # ✅ 關閉對話框


    def edit_income_item(self):
        """一次修改選中的收入項目（名稱 & 金額）"""
        if not self._can_maintain_items():
            QMessageBox.warning(self, "權限不足", "目前角色無權限修改收入項目。")
            return

        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要修改的收入項目！")
            return

        current_id = self.table.item(selected_row, 0).text()
        current_name = self.table.item(selected_row, 1).text()
        current_amount = int(self.table.item(selected_row, 2).text())

        # 彈跳對話框
        dialog = QDialog(self)
        dialog.setWindowTitle("修改收入項目")
        layout = QFormLayout()

        id_label = QLabel(current_id)  # 代號不可修改
        name_input = QLineEdit(current_name)
        amount_input = QSpinBox()
        amount_input.setMinimum(0)
        amount_input.setMaximum(1000000000)
        amount_input.setValue(current_amount)

        layout.addRow("收入項目代號：", id_label)
        layout.addRow("收入項目名稱：", name_input)
        layout.addRow("捐助金額：", amount_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_edit_income_item(dialog, current_id, name_input.text(), amount_input.value()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_edit_income_item(self, dialog, id, name, amount):
        """確認並修改收入項目"""
        if not name:
            QMessageBox.warning(self, "錯誤", "請填寫收入項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE income_items SET name = ?, amount = ? WHERE id = ?", (name, int(amount), id))
        conn.commit()
        conn.close()

        self.load_data()
        QMessageBox.information(self, "成功", "收入項目修改成功！")
        dialog.accept()

    def delete_income_item(self):
        """停用/啟用選中的收入項目（不可刪除歷史資料）。"""
        if not self._can_toggle_active():
            QMessageBox.warning(self, "權限不足", "目前角色無權限停用/啟用收入項目。")
            return

        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要停用/啟用的收入項目！")
            return

        try:
            current_id = self.table.item(selected_row, 0).text().strip()  # ✅ ID 可以是文字或數字
            current_name = self.table.item(selected_row, 1).text().strip()
        except ValueError:
            QMessageBox.warning(self, "錯誤", "無效的收入項目 ID！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(is_active, 1) FROM income_items WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        if row is None:
            QMessageBox.warning(self, "錯誤", "收入項目不存在，無法停用/啟用！")
            conn.close()
            return

        current_active = int(row[0] or 0)
        next_active = 0 if current_active == 1 else 1
        action = "停用" if next_active == 0 else "啟用"

        # ✅ 設定確認刪除的按鈕為「是 / 否」
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"確認{action}")
        msg_box.setText(f"確定要{action}收入項目「{current_id}: {current_name}」嗎？")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        if msg_box.exec_() == QMessageBox.StandardButton.Yes:
            cursor.execute("UPDATE income_items SET is_active = ? WHERE id = ?", (next_active, current_id))
            conn.commit()
            self.load_data()  # ✅ 重新載入資料，確保 UI 更新
            QMessageBox.information(self, "成功", f"收入項目{action}成功！")

        conn.close()
