import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QLabel, QLineEdit, QFormLayout, QSpinBox
)
from app.config import DB_NAME

class ExpenseSetupDialog(QDialog):
    def __init__(self, db_path=None, user_role=None):
        super().__init__()
        self.db_path = db_path or DB_NAME
        self.user_role = user_role

        self.setWindowTitle("支出項目建檔作業")
        self.setGeometry(400, 200, 500, 300)

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["支出項目代號", "支出項目名稱", "支出金額", "狀態"])
        layout.addWidget(self.table)

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

        self.btn_add.clicked.connect(self.add_expense_item)
        self.btn_edit.clicked.connect(self.edit_expense_item)
        self.btn_delete.clicked.connect(self.delete_expense_item)
        self.btn_close.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self._sync_toggle_button_text)

        self._ensure_active_column()
        self.load_data()

    def _can_toggle_active(self):
        role = (self.user_role or "").strip()
        if not role:
            return True
        return role in {"管理員", "會計", "會計人員"}

    def _can_maintain_items(self):
        return self._can_toggle_active()

    def show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def ask_confirm(self, message):
        reply = QMessageBox.question(
            self,
            "確認刪除",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _ensure_active_column(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(expense_items)")
        cols = [r[1] for r in cursor.fetchall()]
        if "is_active" not in cols:
            cursor.execute("ALTER TABLE expense_items ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.commit()
        conn.close()

    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, CAST(amount AS INTEGER), COALESCE(is_active, 1)
            FROM expense_items
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

    def add_expense_item(self):
        if not self._can_maintain_items():
            self.show_warning("權限不足", "目前角色無權限新增支出項目。")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("新增支出項目")
        layout = QFormLayout()

        next_id = self._generate_next_item_id()
        id_label = QLabel(next_id)
        name_input = QLineEdit()
        amount_input = QSpinBox()
        amount_input.setMinimum(0)
        amount_input.setMaximum(1000000000)

        layout.addRow("支出項目代號：", id_label)
        layout.addRow("支出項目名稱：", name_input)
        layout.addRow("支出金額：", amount_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_add_expense_item(dialog, next_id, name_input.text(), amount_input.value()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def _generate_next_item_id(self):
        """產生下一個兩位數代號（01, 02, ...）。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expense_items")
        rows = cursor.fetchall()
        conn.close()

        max_num = 0
        for (raw_id,) in rows:
            sid = str(raw_id or "").strip()
            if not sid:
                continue
            if sid.isdigit():
                max_num = max(max_num, int(sid))
                continue

            # 相容舊資料（例如 E01 / EXPENSE-03）：取尾端數字
            tail_digits = ""
            for ch in reversed(sid):
                if ch.isdigit():
                    tail_digits = ch + tail_digits
                else:
                    break
            if tail_digits:
                max_num = max(max_num, int(tail_digits))

        return f"{max_num + 1:02d}"

    def confirm_add_expense_item(self, dialog, id, name, amount):
        id = id.strip()
        if not id:
            self.show_warning("錯誤", "支出項目代號不可為空！")
            return

        if not name.strip():
            self.show_warning("錯誤", "請填寫支出項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM expense_items WHERE id = ?", (id,))
        if cursor.fetchone():
            self.show_warning("錯誤", f"支出項目代號 {id} 已存在，請輸入其他代號！")
            conn.close()
            return

        try:
            cursor.execute(
                "INSERT INTO expense_items (id, name, amount, is_active) VALUES (?, ?, ?, 1)",
                (id, name, int(amount))
            )
            conn.commit()
            self.show_info("成功", "支出項目新增成功！")
            self.load_data()
        except sqlite3.IntegrityError:
            self.show_warning("錯誤", "支出項目新增失敗！")
        finally:
            conn.close()

        dialog.accept()

    def edit_expense_item(self):
        if not self._can_maintain_items():
            self.show_warning("權限不足", "目前角色無權限修改支出項目。")
            return

        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.show_warning("錯誤", "請選擇要修改的支出項目！")
            return

        current_id = self.table.item(selected_row, 0).text()
        current_name = self.table.item(selected_row, 1).text()
        current_amount = int(self.table.item(selected_row, 2).text())

        dialog = QDialog(self)
        dialog.setWindowTitle("修改支出項目")
        layout = QFormLayout()

        id_label = QLabel(current_id)
        name_input = QLineEdit(current_name)
        amount_input = QSpinBox()
        amount_input.setMinimum(0)
        amount_input.setMaximum(1000000000)
        amount_input.setValue(current_amount)

        layout.addRow("支出項目代號：", id_label)
        layout.addRow("支出項目名稱：", name_input)
        layout.addRow("支出金額：", amount_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_edit_expense_item(dialog, current_id, name_input.text(), amount_input.value()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_edit_expense_item(self, dialog, id, name, amount):
        if not name:
            self.show_warning("錯誤", "請填寫支出項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE expense_items SET name = ?, amount = ? WHERE id = ?", (name, int(amount), id))
        conn.commit()
        conn.close()

        self.load_data()
        self.show_info("成功", "支出項目修改成功！")
        dialog.accept()
        
    def delete_expense_item(self):
        if not self._can_toggle_active():
            self.show_warning("權限不足", "目前角色無權限停用/啟用支出項目。")
            return

        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.show_warning("錯誤", "請選擇要停用/啟用的支出項目！")
            return

        try:
            current_id = self.table.item(selected_row, 0).text().strip()
            current_name = self.table.item(selected_row, 1).text().strip()
        except Exception:
            self.show_warning("錯誤", "無效的支出項目！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(is_active, 1) FROM expense_items WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            self.show_warning("錯誤", "支出項目不存在，無法停用/啟用！")
            return

        current_active = int(row[0] or 0)
        next_active = 0 if current_active == 1 else 1
        action = "停用" if next_active == 0 else "啟用"

        if not self.ask_confirm(f"確定要{action}支出項目「{current_id}: {current_name}」嗎？"):
            conn.close()
            return

        cursor.execute("UPDATE expense_items SET is_active = ? WHERE id = ?", (next_active, current_id))
        conn.commit()
        self.load_data()
        self.show_info("成功", f"支出項目{action}成功！")

        conn.close()
