# app/dialogs/activity_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QDateEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QComboBox
)
from PyQt5.QtCore import QDate, Qt

FEE_TYPE_OPTIONS = ["隨喜隨緣", "固定金額", "其他"]

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
        self.scheme_table.setColumnCount(4)
        self.scheme_table.setHorizontalHeaderLabels(["方案名稱", "方案項目", "費用方式", "金額"])
        
        self.scheme_table.setRowCount(3)
        self.scheme_table.horizontalHeader().setStretchLastSection(True)
        self.scheme_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        font = self.scheme_table.horizontalHeader().font()
        font.setPointSize(16)
        self.scheme_table.horizontalHeader().setFont(font)
        layout.addWidget(self.scheme_table)

        # 初始化每列的「費用方式」下拉 + 金額規則
        for r in range(self.scheme_table.rowCount()):
            self._ensure_fee_type_combo(r, default="固定金額")
            self._ensure_amount_item(r)
            self._apply_fee_rule(r)

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

    def _apply_fee_rule(self, row: int):
        """依費用方式套用金額欄位規則。"""
        combo: QComboBox = self.scheme_table.cellWidget(row, 2)
        if combo is None:
            return

        fee_type = combo.currentText().strip()
        self._ensure_amount_item(row)

        if fee_type == "隨喜隨緣":
            # 清空 + 禁止輸入
            self.scheme_table.item(row, 3).setText("")
            self._set_amount_editable(row, editable=False)
        else:
            # 可輸入
            self._set_amount_editable(row, editable=True)

    def _ensure_fee_type_combo(self, row: int, default: str = "固定金額"):
        """在 (row, 2) 放入費用方式下拉選單。"""
        

        combo = self.scheme_table.cellWidget(row, 2)
        if combo is None:
            combo = QComboBox()
            combo.addItems(FEE_TYPE_OPTIONS)
            self.scheme_table.setCellWidget(row, 2, combo)

            # 用 lambda 綁 row（注意：用預設參數避免 late binding）
            combo.currentIndexChanged.connect(lambda _idx, r=row: self._apply_fee_rule(r))

        # 設定預設值
        if default in FEE_TYPE_OPTIONS:
            combo.setCurrentText(default)
        else:
            combo.setCurrentIndex(0)

    def _ensure_amount_item(self, row: int):
        """確保 (row, 3) 有一個 QTableWidgetItem 當作金額輸入格。"""
        item = self.scheme_table.item(row, 3)
        if item is None:
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.scheme_table.setItem(row, 3, item)

    def _set_amount_editable(self, row: int, editable: bool):
        """控制金額欄是否可編輯。"""
        self._ensure_amount_item(row)
        amt_item = self.scheme_table.item(row, 3)

        flags = amt_item.flags()
        if editable:
            amt_item.setFlags(flags | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            amt_item.setBackground(Qt.white)
        else:
            # 不可編輯：移除 editable，並灰底提示
            amt_item.setFlags((flags | Qt.ItemIsEnabled) & ~Qt.ItemIsEditable)
            amt_item.setBackground(Qt.lightGray)

    def populate_existing_data(self):
        self.name_input.setText(self.activity_data.get("activity_name", ""))
        self.start_date.setDate(QDate.fromString(self.activity_data.get("start_date", ""), "yyyy/MM/dd"))
        self.end_date.setDate(QDate.fromString(self.activity_data.get("end_date", ""), "yyyy/MM/dd"))
        self.note_input.setText(self.activity_data.get("content", ""))

        for i, scheme in enumerate(self.scheme_rows):
            self.scheme_table.item(i, 0).setText(str(scheme.get("scheme_name", "")).strip())
            self.scheme_table.item(i, 1).setText(str(scheme.get("scheme_item", "")).strip())

            # ✅ 讀取 fee_type（你 DB 已新增欄位）
            fee_type = str(scheme.get("fee_type", "")).strip()
            if fee_type not in FEE_TYPE_OPTIONS:
                fee_type = "固定金額"
            combo: QComboBox = self.scheme_table.cellWidget(i, 2)
            combo.setCurrentText(fee_type)

            # 先套規則（若隨喜，金額會被鎖住並清空）
            self._apply_fee_rule(i)

            # 若不是隨喜，才填入金額
            if fee_type != "隨喜隨緣":
                amt = _fmt_int(scheme.get("amount", ""))
                self.scheme_table.item(i, 3).setText(amt)

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

        print("DEBUG scheme_rows:", data["scheme_rows"])

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
            combo: QComboBox = self.scheme_table.cellWidget(row, 2)
            amount_item = self.scheme_table.item(row, 3)

            scheme_name = name_item.text().strip() if name_item else ""
            scheme_item = item_item.text().strip() if item_item else ""
            fee_type = combo.currentText().strip() if combo else ""

            amt_text = amount_item.text().strip() if amount_item else ""
            amt_text = _fmt_int(amt_text)

            # 規則：隨喜隨緣 → amount 一律空字串
            if fee_type == "隨喜隨緣":
                amt_text = ""

            row_data = {
                "scheme_name": scheme_name,
                "scheme_item": scheme_item,
                "fee_type": fee_type,
                "amount": amt_text,
            }

            # fee_type 不應該單獨讓這列被存進 DB（因為它永遠有預設值）
            has_content = any([scheme_name, scheme_item, amt_text])
            if has_content:
                rows.append(row_data)

        return rows

    
    

