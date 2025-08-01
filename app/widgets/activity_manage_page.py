# app/widgets/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTableWidget, QDialog, QTableWidgetItem
)
from PyQt5.QtCore import Qt
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.dialogs.activity_dialog import NewActivityDialog

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
        self.activity_table.setColumnCount(8)
        self.activity_table.setHorizontalHeaderLabels([
            "活動編號", "活動名稱", "起始日期", "結束日期",
            "方案名稱", "方案項目", "金額", "狀態"
        ])

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

        self.add_activity_btn.clicked.connect(self.open_new_activity_dialog)
        self.setLayout(layout)

        self.search_activity_btn.clicked.connect(self.load_activities_to_table)
        self.load_activities_to_table()
        



    def open_new_activity_dialog(self):
        dialog = NewActivityDialog(self.controller)
        if dialog.exec_() == QDialog.Accepted:
            print("✅ 活動新增成功")
            self.load_activities_to_table()  # 新增後自動刷新表格

   

    def load_activities_to_table(self):
        self.activity_table.setRowCount(0)

        activities = self.controller.get_all_activities()

        for row_index, activity in enumerate(activities):
            self.activity_table.insertRow(row_index)
            for col_index, value in enumerate(activity):
                if col_index == 7:  # is_closed 欄位
                    value = "已關閉" if value == 1 else "進行中"
                elif col_index == 6:  # amount 欄位（第7欄）
                    try:
                        # 將換行的多筆金額格式化（去除小數點、加上逗號）
                        amounts = str(value).split('\n')
                        value = '\n'.join([f"{int(float(a)):,}" for a in amounts])
                    except:
                        pass  # 防止空值或轉換錯誤
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignTop)  # 上對齊，看起來比較整齊
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)  # 不能編輯
                self.activity_table.setItem(row_index, col_index, item)

        self.activity_table.resizeRowsToContents()




