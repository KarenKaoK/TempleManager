# app/widgets/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTableWidget
)
from app.widgets.auto_resizing_table import AutoResizingTableWidget

class ActivityManagePage(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        layout = QVBoxLayout()

        # 🔷 活動管理區塊
        activity_group = QGroupBox("活動項目管理")
        activity_group.setStyleSheet("font-size: 18px; font-weight: bold;")
        activity_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("活動搜尋："))
        self.activity_search_input = QLineEdit()
        search_layout.addWidget(self.activity_search_input)

        self.search_activity_btn = QPushButton("🔍 搜尋")
        self.add_activity_btn = QPushButton("➕ 新增活動")
        self.edit_activity_btn = QPushButton("🖊 修改活動")
        self.delete_activity_btn = QPushButton("❌ 刪除活動")
        self.close_activity_btn = QPushButton("⛔ 關閉活動")

        for btn in [
            self.search_activity_btn, self.add_activity_btn,
            self.edit_activity_btn, self.delete_activity_btn,
            self.close_activity_btn
        ]:
            btn.setStyleSheet("font-size: 14px;")
            search_layout.addWidget(btn)

        activity_layout.addLayout(search_layout)

        self.activity_table = AutoResizingTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(["活動編號", "活動名稱", "起始日期", "結束日期"])
        self.activity_table.setStyleSheet("font-size: 14px;")
        activity_layout.addWidget(self.activity_table)

        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)

        # 🔶 報名人員區塊
        signup_group = QGroupBox("活動報名人員")
        signup_group.setStyleSheet("font-size: 18px; font-weight: bold;")
        signup_layout = QVBoxLayout()

        signup_search_layout = QHBoxLayout()
        signup_search_layout.addWidget(QLabel("參加人員姓名搜尋："))
        self.signup_search_input = QLineEdit()
        signup_search_layout.addWidget(self.signup_search_input)

        self.search_signup_btn = QPushButton("🔍 搜尋")
        self.add_signup_btn = QPushButton("➕ 新增人員")
        self.edit_signup_btn = QPushButton("🖊 修改人員")
        self.delete_signup_btn = QPushButton("❌ 刪除人員")
        self.print_signup_btn = QPushButton("🖨️ 資料列印")

        for btn in [
            self.search_signup_btn, self.add_signup_btn,
            self.edit_signup_btn, self.delete_signup_btn,
            self.print_signup_btn
        ]:
            btn.setStyleSheet("font-size: 14px;")
            signup_search_layout.addWidget(btn)

        signup_layout.addLayout(signup_search_layout)

        self.signup_table = AutoResizingTableWidget()
        self.signup_table.setColumnCount(16)
        self.signup_table.setHorizontalHeaderLabels([
            "序", "姓名", "性別", "國曆生日", "農曆生日",
            "年份", "生肖", "年齡", "生辰", "聯絡電話", "手機號碼",
            "身份", "身份證字號", "聯絡地址", "備註說明","報名日期"
        ])
        self.signup_table.setStyleSheet("font-size: 14px;")
        signup_layout.addWidget(self.signup_table)

        signup_group.setLayout(signup_layout)
        layout.addWidget(signup_group)

        self.setLayout(layout)
