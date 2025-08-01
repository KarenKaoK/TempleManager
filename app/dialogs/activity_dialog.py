# app/dialogs/activity_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QDateEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView,QMessageBox
)
from PyQt5.QtCore import QDate

class NewActivityDialog(QDialog):
    def __init__(self,controller=None):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("新增活動")
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
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        grid.addWidget(self.start_date, 1, 1)

        grid.addWidget(QLabel("結束日期"), 1, 2)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
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
        layout.addWidget(self.scheme_table)
        font = self.scheme_table.horizontalHeader().font()
        font.setPointSize(16)
        self.scheme_table.horizontalHeader().setFont(font)

        layout.addWidget(QLabel("備註說明"))
        self.note_input = QTextEdit()
        layout.addWidget(self.note_input)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("✅ 存入")
        self.cancel_btn = QPushButton("❌ 關閉")
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.setLayout(layout)
        self.save_btn.clicked.connect(self.save_activity)

    def get_data(self):
        return {
            "activity_name": self.name_input.text().strip(),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),   
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),       
            "note": self.note_input.toPlainText().strip(),                 
            "scheme_rows": self.get_scheme_data()                          
        }
    def save_activity(self):
        data = {
            "activity_name": self.name_input.text().strip(),
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),
            "location": "", 
            "content": self.note_input.toPlainText().strip(),
            "scheme_rows": self.get_scheme_data()
        }

        self.controller.insert_activity(data)
        self.accept()

    def get_scheme_data(self):
        rows = []
        for row in range(self.scheme_table.rowCount()):
            name_item = self.scheme_table.item(row, 0)
            item_item = self.scheme_table.item(row, 1)
            amount_item = self.scheme_table.item(row, 2)

            row_data = {
                "scheme_name": name_item.text().strip() if name_item else "",
                "scheme_item": item_item.text().strip() if item_item else "",
                "amount": amount_item.text().strip() if amount_item else ""
            }
            if any(row_data.values()):
                rows.append(row_data)
        return rows

