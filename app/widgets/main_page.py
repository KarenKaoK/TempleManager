from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QFormLayout, QGroupBox, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt


class MainPageWidget(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()

        # 🔍 搜尋列
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("請輸入電話 / 姓名 / 地址")
        self.search_button = QPushButton("資料查詢")
        search_layout.addWidget(QLabel("電話／姓名／地址快速查詢："))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # 📋 戶長列表區
        self.household_table = QTableWidget()
        self.household_table.setColumnCount(10)
        self.household_table.setHorizontalHeaderLabels([
            "標示", "戶卡姓名", "性別", "國曆生日", "農曆生日", "年齡", "生肖", "生辰",
            "聯絡電話", "聯絡地址"
        ])
        self.household_table.setRowCount(1)
        self.household_table.setItem(0, 0, QTableWidgetItem("戶長"))
        self.household_table.setItem(0, 1, QTableWidgetItem("陳阿貓"))
        self.household_table.setItem(0, 2, QTableWidgetItem("女"))
        self.household_table.setItem(0, 3, QTableWidgetItem("88/12/31"))
        self.household_table.setItem(0, 4, QTableWidgetItem("88/11/24"))
        self.household_table.setItem(0, 5, QTableWidgetItem("26"))
        self.household_table.setItem(0, 6, QTableWidgetItem("兔"))
        self.household_table.setItem(0, 7, QTableWidgetItem("吉"))
        self.household_table.setItem(0, 8, QTableWidgetItem("09123456789"))
        self.household_table.setItem(0, 9, QTableWidgetItem("新北市深坑區文化街六段七樓"))
        main_layout.addWidget(self.household_table)

        # 底部區域：成員列表 + 詳情表單
        bottom_splitter = QSplitter(Qt.Horizontal)

        # 👥 成員列表
        member_widget = QWidget()
        member_layout = QVBoxLayout()
        self.member_table = QTableWidget()
        self.member_table.setColumnCount(8)
        self.member_table.setHorizontalHeaderLabels([
            "序", "標示", "姓名", "性別", "國曆生日", "農曆生日", "生肖", "年齡"
        ])
        member_layout.addWidget(self.member_table)
        member_widget.setLayout(member_layout)

        # 📋 詳細資料表單
        detail_form = QFormLayout()
        detail_form.addRow("姓名：", QLineEdit())
        detail_form.addRow("性別：", QLineEdit())
        detail_form.addRow("國曆生日：", QLineEdit())
        detail_form.addRow("農曆生日：", QLineEdit())
        detail_form.addRow("生肖：", QLineEdit())
        detail_form.addRow("年齡：", QLineEdit())
        detail_form.addRow("電話：", QLineEdit())
        detail_form.addRow("地址：", QLineEdit())
        detail_form.addRow("郵遞區號：", QLineEdit())
        detail_form.addRow("備註說明：", QTextEdit())
        detail_box = QGroupBox("基本資料")
        detail_box.setLayout(detail_form)

        bottom_splitter.addWidget(member_widget)
        bottom_splitter.addWidget(detail_box)
        main_layout.addWidget(bottom_splitter)

        self.setLayout(main_layout)
