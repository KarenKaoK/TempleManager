import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QLabel, QLineEdit, QFormLayout, QSpinBox, QInputDialog
)

DB_NAME = "temple.db"  # ✅ 確保統一使用 temple.db

class IncomeSetupDialog(QDialog):
    """收入項目建檔作業 視窗"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("收入項目建檔作業")
        self.setGeometry(400, 200, 500, 300)

        # 主佈局
        layout = QVBoxLayout()

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["收入項目代號", "收入項目名稱", "捐助金額"])
        layout.addWidget(self.table)

        # 按鈕區域
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("資料新增")
        self.btn_edit = QPushButton("資料修改")
        self.btn_delete = QPushButton("資料刪除")
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

        # 載入資料
        self.load_data()

    def load_data(self):
        """從 SQLite 載入收入項目"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, CAST(amount AS INTEGER) FROM income_items")  # ✅ 確保金額顯示整數
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, item in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))

    def get_next_id(self):
        """取得下一個可用的收入項目代號（從 1 開始）"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM income_items")
        max_id = cursor.fetchone()[0]
        conn.close()
        max_id = int(max_id) if max_id is not None else 0  # ✅ 修正 max_id 轉換錯誤
        return max_id + 1

    def add_income_item(self):
        """新增收入項目（一次輸入完整資料）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增收入項目")
        layout = QFormLayout()

        next_id = self.get_next_id()
        id_label = QLabel(str(next_id))  # ✅ 代號自動產生，不讓使用者輸入
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

    def confirm_add_income_item(self, dialog, id, name, amount):
        """確認並新增收入項目"""
        if not name:
            QMessageBox.warning(self, "錯誤", "請填寫收入項目名稱！")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO income_items (id, name, amount) VALUES (?, ?, ?)", (id, name, int(amount)))  # ✅ 確保金額為整數
            conn.commit()
            QMessageBox.information(self, "成功", "收入項目新增成功！")
            self.load_data()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "錯誤", "收入項目代號已存在！")
        finally:
            conn.close()

        dialog.accept()

    def edit_income_item(self):
        """一次修改選中的收入項目（名稱 & 金額）"""
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

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE income_items SET name = ?, amount = ? WHERE id = ?", (name, int(amount), id))
        conn.commit()
        conn.close()

        self.load_data()
        QMessageBox.information(self, "成功", "收入項目修改成功！")
        dialog.accept()

    def delete_income_item(self):
        """刪除選中的收入項目"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要刪除的收入項目！")
            return

        try:
            current_id = int(self.table.item(selected_row, 0).text())  # ✅ 確保 `id` 為 `int`
        except ValueError:
            QMessageBox.warning(self, "錯誤", "無效的收入項目 ID！")
            return

         # ✅ 設定確認刪除的按鈕為「是 / 否」
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("確認刪除")
        msg_box.setText(f"確定要刪除收入項目 {current_id} 嗎？")
        btn_yes = msg_box.addButton("是", QMessageBox.ButtonRole.AcceptRole)
        btn_no = msg_box.addButton("否", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec_()

        if msg_box.clickedButton() == btn_yes:  # ✅ 如果按下的是「是」
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # ✅ 刪除前先檢查資料是否存在
            cursor.execute("SELECT * FROM income_items WHERE id = ?", (current_id,))
            result = cursor.fetchone()

            if result is None:
                QMessageBox.warning(self, "錯誤", "收入項目不存在，無法刪除！")
                conn.close()
                return

            # ✅ 執行刪除
            cursor.execute("DELETE FROM income_items WHERE id = ?", (current_id,))
            conn.commit()

            if cursor.rowcount == 0:
                QMessageBox.warning(self, "錯誤", "刪除失敗，請檢查 ID 是否存在！")
            else:
                self.load_data()  # ✅ 重新載入資料，確保 UI 更新
                QMessageBox.information(self, "成功", "收入項目刪除成功！")

            conn.close()
