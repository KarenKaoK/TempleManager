from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, QTabWidget
)
from PyQt5.QtCore import Qt
from app.widgets.search_bar import SearchBarWidget


class MainPageWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # 搜尋欄位與功能按鈕
        top_layout = QHBoxLayout()
        self.search_bar = SearchBarWidget()
        top_layout.addWidget(self.search_bar)

        self.query_btn = QPushButton("🔍 資料查詢")
        self.add_btn = QPushButton("➕ 新增戶籍資料")
        self.delete_btn = QPushButton("❌ 刪除戶籍資料")
        self.print_btn = QPushButton("🖨️ 資料列印")
        for btn in [self.query_btn, self.add_btn, self.delete_btn, self.print_btn]:
            btn.setStyleSheet("font-size: 14px;")
            top_layout.addWidget(btn)

        layout.addLayout(top_layout)

        # 戶長表格
        self.household_table = QTableWidget()
        self.household_table.setColumnCount(15)
        self.household_table.setHorizontalHeaderLabels([
            "標籤", "戶長姓名", "性別", "國曆生日", "農曆生日", "年份", "生肖", "年齡", "生辰",
            "聯絡電話", "手機號碼", "身份", "身分證字號", "聯絡地址", "備註說明"
        ])
        self.household_table.setStyleSheet("font-size: 14px;")
        self.household_table.resizeColumnsToContents()
        self.household_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.household_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        household_group = QGroupBox("信眾戶籍戶長資料")
        household_group.setStyleSheet("font-size: 14px;")
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.household_table)
        household_group.setLayout(group_layout)
        layout.addWidget(household_group)

        # 成員與詳情分區
        splitter = QSplitter(Qt.Horizontal)

        left_container = QWidget()
        left_layout = QHBoxLayout()
        left_inner = QVBoxLayout()

        # 🔴 成員統計標籤（紅色）
        stats_label = QLabel("戶號：1　戶長：賴阿貓　家庭成員共：1 丁 1 口")
        stats_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold; padding: 2px 4px;")
        left_inner.addWidget(stats_label)

        self.member_table = QTableWidget()
        self.member_table.setColumnCount(16)
        self.member_table.setHorizontalHeaderLabels([
            "序", "標示", "姓名", "性別", "國曆生日", "農曆生日", "年份", "生肖", "年齡", "生辰",
            "聯絡電話", "手機號碼", "身份", "身分證字號", "聯絡地址", "備註說明"
        ])
        self.member_table.setStyleSheet("font-size: 14px;")
        self.member_table.resizeColumnsToContents()
        self.member_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.member_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_inner.addWidget(self.member_table)

        left_table_box = QWidget()
        left_table_box.setLayout(left_inner)
        left_layout.addWidget(left_table_box)

        # 成員操作按鈕區塊（縮小按鈕間距）
        member_btn_layout = QVBoxLayout()
        member_btn_layout.setSpacing(2)

        btns = [
            ("➕ 新增成員", "green"),
            ("🖊 修改成員", "blue"),
            ("❌ 刪除成員", "red"),
            ("☑ 設為戶長", None),
            ("🔄 戶籍變更", None),
            ("⬆ 上移", None),
            ("⬇ 下移", None),
            ("⛔ 關閉退出", "darkred")
        ]
        for label, color in btns:
            btn = QPushButton(label)
            style = "font-size: 14px; padding: 4px;"
            if color:
                style += f" color: {color};"
            btn.setStyleSheet(style)
            member_btn_layout.addWidget(btn)

        right_btn_box = QWidget()
        right_btn_box.setLayout(member_btn_layout)
        left_layout.addWidget(right_btn_box)

        left_container.setLayout(left_layout)
        splitter.addWidget(left_container)

        # 詳情表單分頁（右側）
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("font-size: 14px;")

        # ➤ 基本資料頁籤內容（改為符合圖示布局）
        base_form = QGridLayout()
        base_form.setSpacing(6)
        base_form.setContentsMargins(10, 10, 10, 10)

        entries = [
            ("姓名：", 0, 0), ("性別：", 0, 2), ("加入日期：", 0, 4),
            ("國曆生日：", 1, 0), ("農曆生日：", 1, 2), ("年份：", 1, 4),
            ("身份：", 2, 0), ("生肖：", 2, 2), ("年齡：", 2, 4),
            ("聯絡電話：", 3, 0), ("手機號碼：", 3, 2), ("出生時辰：", 3, 4),
            ("身分證號：", 4, 0), ("電子郵件：", 4, 2),
            ("信眾地址：", 5, 0),
            ("郵遞區號：", 6, 0), ("備註說明：", 7, 0)
        ]

        for label, row, col in entries:
            base_form.addWidget(QLabel(label), row, col)

        fields = {}
        for label, row, col in entries:
            if label == "備註說明：":
                widget = QTextEdit()
                base_form.addWidget(widget, row, col + 1, 1, 5)
            elif label == "信眾地址：":
                widget = QLineEdit()
                base_form.addWidget(widget, row, col + 1, 1, 5)
            else:
                widget = QLineEdit()
                base_form.addWidget(widget, row, col + 1)
            widget.setStyleSheet("font-size: 14px;")
            fields[label] = widget

        base_widget = QWidget()
        base_widget.setLayout(base_form)
        tab_widget.addTab(base_widget, "基本資料")

        # 👉 可擴充其他分頁（例如：安燈紀錄、拜斗紀錄...）
        for tab_name in ["安燈紀錄", "拜斗紀錄", "收入記錄", "法會記錄", "支出記錄"]:
            placeholder = QWidget()
            tab_widget.addTab(placeholder, tab_name)

        splitter.addWidget(tab_widget)

        layout.addWidget(splitter)
        self.setLayout(layout)
