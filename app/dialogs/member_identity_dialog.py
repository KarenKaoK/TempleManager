import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QLabel, QLineEdit, QFormLayout
)

from app.config import DB_NAME

class MemberIdentityDialog(QDialog):
    """信眾身份名稱設定 視窗"""
    def __init__(self):
        super().__init__()

        self.setWindowTitle("信眾身份名稱設定")
        self.setGeometry(400, 200, 400, 300)

        # 主佈局
        layout = QVBoxLayout()

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["身份名稱"])
        layout.addWidget(self.table)

        # 按鈕區域
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("資料新增")
        self.btn_edit = QPushButton("資料修改")
        self.btn_delete = QPushButton("資料刪除")
        self.btn_close = QPushButton("關閉返回")  # ✅ 新增關閉按鈕

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_close)  # ✅ 添加到 UI

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 綁定事件
        self.btn_add.clicked.connect(self.add_identity)
        self.btn_edit.clicked.connect(self.edit_identity)
        self.btn_delete.clicked.connect(self.delete_identity)
        self.btn_close.clicked.connect(self.close)  # ✅ 點擊後關閉視窗

        # 載入資料
        self.load_data()

    def load_data(self):
        """從 SQLite 載入身份名稱"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM member_identity ORDER BY id ASC")  # 依 `id` 順序排列
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(row[1]))  # 只顯示身份名稱

    def add_identity(self):
        """新增身份名稱"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增身份名稱")
        layout = QFormLayout()

        name_input = QLineEdit()

        layout.addRow("身份名稱：", name_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_add_identity(dialog, name_input.text()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_add_identity(self, dialog, name):
        """確認並新增身份名稱"""
        if not name.strip():
            QMessageBox.warning(self, "錯誤", "請輸入身份名稱！")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO member_identity (name) VALUES (?)", (name,))
            conn.commit()
            QMessageBox.information(self, "成功", "身份名稱新增成功！")
            self.load_data()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "錯誤", "身份名稱已存在！")
        finally:
            conn.close()

        dialog.accept()

    def edit_identity(self):
        """修改選中的身份名稱"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要修改的身份名稱！")
            return

        current_name = self.table.item(selected_row, 0).text()

        dialog = QDialog(self)
        dialog.setWindowTitle("修改身份名稱")
        layout = QFormLayout()

        name_input = QLineEdit(current_name)

        layout.addRow("新身份名稱：", name_input)

        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")

        btn_ok.clicked.connect(lambda: self.confirm_edit_identity(dialog, current_name, name_input.text()))
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def confirm_edit_identity(self, dialog, old_name, new_name):
        """確認並修改身份名稱"""
        if not new_name.strip():
            QMessageBox.warning(self, "錯誤", "請輸入新身份名稱！")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE member_identity SET name = ? WHERE name = ?", (new_name, old_name))
        conn.commit()
        conn.close()

        self.load_data()
        QMessageBox.information(self, "成功", "身份名稱修改成功！")
        dialog.accept()

    def delete_identity(self):
        """刪除選中的身份名稱"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "錯誤", "請選擇要刪除的身份名稱！")
            return

        current_name = self.table.item(selected_row, 0).text()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("確認刪除")
        msg_box.setText(f"確定要刪除身份名稱 '{current_name}' 嗎？")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText("是")
        msg_box.button(QMessageBox.StandardButton.No).setText("否")

        reply = msg_box.exec_()

        if reply == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM member_identity WHERE name = ?", (current_name,))
            conn.commit()
            conn.close()

            self.load_data()
            QMessageBox.information(self, "成功", "身份名稱刪除成功！")
