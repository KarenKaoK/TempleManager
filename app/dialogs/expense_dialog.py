import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QLabel, QLineEdit, QFormLayout, QSpinBox
)
from app.config import DB_NAME


class ExpenseSetupDialog(QDialog):
    """支出項目建檔作業 視窗"""
    def __init__(self,db_path=None):
        super().__init__()
        from app.config import DB_NAME
        self.db_path = db_path or DB_NAME

        self.setWindowTitle("支出項目建檔作業")
        self.setGeometry(400, 200, 500, 300)

        # 主佈局
        layout = QVBoxLayout()

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["支出項目代號", "支出項目名稱", "支出金額"])
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

        # 綁定事件
        self.btn_add.clicked.connect(self.add_expense_item)
        self.btn_edit.clicked.connect(self.edit_expense_item)
        self.btn_delete.clicked.connect(self.delete_expense_item)
        self.btn_close.clicked.connect(self.close)

        # 載入資料
        self.load_data()

    def load_data(self):
        """從 SQLite 載入支出項目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expense_items")
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, item in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))



    def add_expense_item(self):
        """新增支出項目"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增支出項目")
        layout = QFormLayout()

        id_input = QLineEdit()
        name_input = QLineEdit()
        amount_input = QSpinBox()  
        amount_input.setMinimum(0)  
        amount_input.setMaximum(1000000000)  

        layout.addRow("支出項目代號：", id_input)
        layout.addRow("支出項目名稱：", name_input)
        layout.addRow("支出金額：", amount_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_add_expense_item(dialog, id_input.text(), name_input.text(), amount_input.value()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_add_expense_item(self, dialog, id, name, amount):
        """確認並新增支出項目"""
        id = id.strip()  # ✅ 確保 ID 不能是空白
        if not id:
            QMessageBox.warning(self, "錯誤", "支出項目代號不可為空！")
            return

        if not name.strip():
            QMessageBox.warning(self, "錯誤", "請填寫支出項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 🔍 檢查 ID 是否已存在於 `expense_items`
        cursor.execute("SELECT id FROM expense_items WHERE id = ?", (id,))
        if cursor.fetchone():
            QMessageBox.warning(self, "錯誤", f"支出項目代號 {id} 已存在，請輸入其他代號！")
            conn.close()
            return

        try:
            cursor.execute("INSERT INTO expense_items (id, name, amount) VALUES (?, ?, ?)", (id, name, int(amount)))
            conn.commit()
            QMessageBox.information(self, "成功", "支出項目新增成功！")
            self.load_data()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "錯誤", "支出項目新增失敗！")
        finally:
            conn.close()

        dialog.accept()  # ✅ 關閉對話框


        

    def edit_expense_item(self):
        """一次修改選中的支出項目（名稱 & 金額）"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要修改的支出項目！")
            return

        current_id = self.table.item(selected_row, 0).text()
        current_name = self.table.item(selected_row, 1).text()
        current_amount = int(self.table.item(selected_row, 2).text())

        # 彈跳對話框
        dialog = QDialog(self)
        dialog.setWindowTitle("修改支出項目")
        layout = QFormLayout()

        id_label = QLabel(current_id)  # 代號不可修改
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
        """確認並修改支出項目"""
        if not name:
            QMessageBox.warning(self, "錯誤", "請填寫支出項目名稱！")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE expense_items SET name = ?, amount = ? WHERE id = ?", (name, int(amount), id))
        conn.commit()
        conn.close()

        self.load_data()
        QMessageBox.information(self, "成功", "支出項目修改成功！")
        dialog.accept()
    def delete_expense_item(self):
        """刪除選中的支出項目"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要刪除的支出項目！")
            return

        try:
            current_id = int(self.table.item(selected_row, 0).text())

            current_name = self.table.item(selected_row, 1).text()  
        except ValueError:
            QMessageBox.warning(self, "錯誤", "無效的支出項目 ID！")
            return
 
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("確認刪除")
        msg_box.setText(f"確定要刪除支出 '項目{current_id}: {current_name} ' 嗎？")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText("是")
        msg_box.button(QMessageBox.StandardButton.No).setText("否")
        reply = msg_box.exec_()

        if reply == QMessageBox.StandardButton.Yes:  
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM expense_items WHERE id = ?", (current_id,))
            conn.commit()

            if cursor.rowcount == 0:
                QMessageBox.warning(self, "錯誤", "刪除失敗，請檢查 ID 是否存在！")
            else:
                self.load_data()  
                QMessageBox.information(self, "成功", "支出項目刪除成功！")

            conn.close()
