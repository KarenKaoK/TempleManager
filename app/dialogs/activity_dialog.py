# app/dialogs/activity_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QDateEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,QMessageBox
)
from PyQt5.QtCore import QDate, Qt

def _fmt_int(value):
        """把 8888.0、'8888.0'、' 8888 ' 等都轉成沒有小數點的字串；失敗就原樣字串。"""
        try:
            f = float(value)
            return str(int(f))
        except Exception:
            return str(value).strip() if value is not None else ""

class NewActivityDialog(QDialog):
    def __init__(self, controller=None, mode="new", activity_data=None, scheme_rows=None):
        super().__init__()
        self.controller = controller
        self.mode = mode  # "new" or "edit"
        self.activity_data = activity_data or {}
        self.scheme_rows = scheme_rows or []

        self.setWindowTitle("修改活動" if self.mode == "edit" else "新增活動")
        self.setMinimumWidth(600)

        self.setStyleSheet("""
            QLabel, QLineEdit, QDateEdit, QTextEdit, QPushButton, QTableWidget {
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout()

        grid = QGridLayout()
        grid.addWidget(QLabel("活動名稱"), 0, 0)
        self.name_input = QLineEdit()
        grid.addWidget(self.name_input, 0, 1, 1, 3)

        grid.addWidget(QLabel("起始日期"), 1, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        grid.addWidget(self.start_date, 1, 1)

        grid.addWidget(QLabel("結束日期"), 1, 2)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        grid.addWidget(self.end_date, 1, 3)

        layout.addLayout(grid)

        # 🔸 方案表格
        self.scheme_table = QTableWidget()
        self.scheme_table.setColumnCount(3)
        self.scheme_table.setHorizontalHeaderLabels(["方案名稱", "方案項目", "金額"])
        self.scheme_table.setRowCount(3)
        self.scheme_table.horizontalHeader().setStretchLastSection(True)
        self.scheme_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        font = self.scheme_table.horizontalHeader().font()
        font.setPointSize(16)
        self.scheme_table.horizontalHeader().setFont(font)
        layout.addWidget(self.scheme_table)

        layout.addWidget(QLabel("備註說明"))
        self.note_input = QTextEdit()
        layout.addWidget(self.note_input)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("✅ 儲存")
        self.cancel_btn = QPushButton("❌ 關閉")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.save_btn.clicked.connect(self.save_activity)
        self.cancel_btn.clicked.connect(self.reject)

        self.setLayout(layout)

        if self.mode == "new":
            # 新增資料
            today = QDate.currentDate()
            self.start_date.setDate(today)
            self.end_date.setDate(today)
        # 若是編輯模式就填入舊資料
        if self.mode == "edit":
            self.populate_existing_data()

    def populate_existing_data(self):
        self.name_input.setText(self.activity_data.get("activity_name", ""))
        self.start_date.setDate(QDate.fromString(self.activity_data.get("start_date", ""), "yyyy/MM/dd"))
        self.end_date.setDate(QDate.fromString(self.activity_data.get("end_date", ""), "yyyy/MM/dd"))
        self.note_input.setText(self.activity_data.get("content", ""))

        for i, scheme in enumerate(self.scheme_rows):
            self.scheme_table.insertRow(i)
            self.scheme_table.setItem(i, 0, QTableWidgetItem(str(scheme.get("scheme_name", ""))))
            self.scheme_table.setItem(i, 1, QTableWidgetItem(str(scheme.get("scheme_item", ""))))

            amt_item = QTableWidgetItem(_fmt_int(scheme.get("amount", "")))
            amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.scheme_table.setItem(i, 2, amt_item)

    def get_data(self):
        return {
            "activity_id": self.activity_data.get("activity_id") if self.mode == "edit" else None,
            "activity_name": self.name_input.text().strip(),
            "start_date": self.start_date.date().toString("yyyy/MM/dd"),
            "end_date": self.end_date.date().toString("yyyy/MM/dd"),
            "content": self.note_input.toPlainText().strip(),
            "scheme_rows": self.get_scheme_data()
        }

    def save_activity(self):
        data = self.get_data()

        if self.mode == "edit":
            self.controller.update_activity(data)
        else:
            self.controller.insert_activity(data)

        self.accept()

    def get_scheme_data(self):
        rows = []
        for row in range(self.scheme_table.rowCount()):
            name_item = self.scheme_table.item(row, 0)
            item_item = self.scheme_table.item(row, 1)
            amount_item = self.scheme_table.item(row, 2)

            amt_text = amount_item.text().strip() if amount_item else ""
            amt_text = _fmt_int(amt_text)  # 轉成沒有小數點的字串

            row_data = {
                "scheme_name": name_item.text().strip() if name_item else "",
                "scheme_item": item_item.text().strip() if item_item else "",
                "amount": amt_text
            }
            if any(row_data.values()):
                rows.append(row_data)
        return rows

    
    

