from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, 
    QTabWidget, QTableWidgetItem, QMessageBox, QDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from app.widgets.search_bar import SearchBarWidget
from app.dialogs.household_dialog import NewHouseholdDialog
from app.widgets.auto_resizing_table import AutoResizingTableWidget




class MainPageWidget(QWidget):

    new_household_triggered = pyqtSignal()  

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.fields = {}  #

        # 搜尋欄位與功能按鈕
        top_layout = QHBoxLayout()
        self.search_bar = SearchBarWidget()
        top_layout.addWidget(self.search_bar)
    

        self.add_btn = QPushButton("➕ 新增戶籍資料")
        self.add_btn.clicked.connect(self.new_household_triggered.emit)

        self.delete_btn = QPushButton("❌ 刪除戶籍資料")
        self.print_btn = QPushButton("🖨️ 資料列印")
        for btn in [ self.add_btn, self.delete_btn, self.print_btn]:
            btn.setStyleSheet("font-size: 14px;")
            top_layout.addWidget(btn)

        layout.addLayout(top_layout)

        # 戶長表格
        # self.household_table = QTableWidget() # AutoResizingTableWidget 代替，已經繼承 QTableWidget
        self.household_table = AutoResizingTableWidget()
        self.household_table.setColumnCount(15)
        self.household_table.setHorizontalHeaderLabels([
            "標籤", "戶長姓名", "性別", "國曆生日", "農曆生日", "年份", "生肖", "年齡", "生辰",
            "聯絡電話", "手機號碼", "身份", "身分證字號", "聯絡地址", "備註說明"
        ])
        self.household_table.setStyleSheet("font-size: 14px;")
        self.household_table.cellClicked.connect(self.on_household_row_clicked)


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
        self.stats_label = QLabel("戶號：1　戶長：賴阿貓　家庭成員共：1 丁 1 口")
        self.stats_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold; padding: 2px 4px;")
        left_inner.addWidget(self.stats_label)

        # self.member_table = QTableWidget()
        self.member_table = AutoResizingTableWidget()
        self.member_table.setColumnCount(16)
        self.member_table.setHorizontalHeaderLabels([
            "序", "標示", "姓名", "性別", "國曆生日", "農曆生日", "年份", "生肖", "年齡", "生辰",
            "聯絡電話", "手機號碼", "身份", "身分證字號", "聯絡地址", "備註說明"
        ])
        self.member_table.setStyleSheet("font-size: 14px;")
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

        self.fields = {}  #
        for label, row, col in entries:
            if label == "備註說明：":
                widget = QTextEdit()
                widget.setReadOnly(True)  # 設為唯讀
                base_form.addWidget(widget, row, col + 1, 1, 5)
            elif label == "信眾地址：":
                widget = QLineEdit()
                widget.setReadOnly(True)  # 設為唯讀
                base_form.addWidget(widget, row, col + 1, 1, 5)
            elif label == "電子郵件：":
                widget = QLineEdit()
                widget.setReadOnly(True)  # 設為唯讀
                base_form.addWidget(widget, row, col + 1, 1, 5)
            else:
                widget = QLineEdit()
                widget.setReadOnly(True)  # 設為唯讀
                base_form.addWidget(widget, row, col + 1)
            widget.setStyleSheet("font-size: 14px;")
            self.fields[label] = widget

        base_widget = QWidget()
        base_widget.setLayout(base_form)
        base_widget.setMinimumWidth(600)
        base_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        for label, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        tab_widget.addTab(base_widget, "基本資料")

        # 👉 可擴充其他分頁（例如：安燈紀錄、拜斗紀錄...）
        for tab_name in ["安燈紀錄", "拜斗紀錄", "收入記錄", "法會記錄", "支出記錄"]:
            placeholder = QWidget()
            tab_widget.addTab(placeholder, tab_name)

        splitter.addWidget(tab_widget)

        layout.addWidget(splitter)
        self.setLayout(layout)

    def update_household_table(self, data):
        self.household_table.setRowCount(len(data))

        for row_idx, row in enumerate(data):
            self.household_table.setItem(row_idx, 0, QTableWidgetItem("預設標籤"))

            # 以下順序要對齊你表格標題設定的順序
            self.household_table.setItem(row_idx, 1, QTableWidgetItem(row.get("head_name", "")))
            self.household_table.setItem(row_idx, 2, QTableWidgetItem(row.get("head_gender", "")))
            self.household_table.setItem(row_idx, 3, QTableWidgetItem(row.get("head_birthday_ad", "")))
            self.household_table.setItem(row_idx, 4, QTableWidgetItem(row.get("head_birthday_lunar", "")))
            self.household_table.setItem(row_idx, 5, QTableWidgetItem(row.get("head_birth_year", "")))
            self.household_table.setItem(row_idx, 6, QTableWidgetItem(row.get("head_zodiac", "")))
            self.household_table.setItem(row_idx, 7, QTableWidgetItem(str(row.get("head_age", ""))))
            self.household_table.setItem(row_idx, 8, QTableWidgetItem(row.get("head_birth_time", "")))
            self.household_table.setItem(row_idx, 9, QTableWidgetItem(row.get("head_phone_home", "")))
            self.household_table.setItem(row_idx, 10, QTableWidgetItem(row.get("head_phone_mobile", "")))
            self.household_table.setItem(row_idx, 11, QTableWidgetItem(row.get("head_identity", "")))
            self.household_table.setItem(row_idx, 12, QTableWidgetItem(row.get("head_email", "")))
            self.household_table.setItem(row_idx, 13, QTableWidgetItem(row.get("head_address", "")))
            self.household_table.setItem(row_idx, 14, QTableWidgetItem(row.get("household_note", "")))
        
        # 調整表格大小
        self.household_table.adjust_to_contents()

    def on_household_row_clicked(self, row, col):
        household_id_item = self.household_table.item(row, 0)  # 假設 id 在第 0 欄
        if not household_id_item:
            return

        household_id = household_id_item.text()
        
        # 呼叫 controller 拿成員資料
        members = self.controller.get_household_members(household_id)
        self.update_member_table(members)

        # 更新右側戶長詳情
        data = self.current_households[row]  # 你需在 update_household_table() 存這個
        self.fill_head_detail(data)

        # 更新統計標籤
        num_adults = sum(1 for m in members if m.get("identity") == "丁")
        num_dependents = sum(1 for m in members if m.get("identity") == "口")
        self.stats_label.setText(
            f"戶號：{household_id}　戶長：{data['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
        )
    def update_member_table(self, data):
        self.member_table.setRowCount(len(data))
        for row_idx, row in enumerate(data):
            self.member_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))  # 序
            self.member_table.setItem(row_idx, 1, QTableWidgetItem(""))  # 標示（可加角色）
            self.member_table.setItem(row_idx, 2, QTableWidgetItem(row.get("name", "")))
            self.member_table.setItem(row_idx, 3, QTableWidgetItem(row.get("gender", "")))
            self.member_table.setItem(row_idx, 4, QTableWidgetItem(row.get("birthday_ad", "")))
            self.member_table.setItem(row_idx, 5, QTableWidgetItem(row.get("birthday_lunar", "")))
            self.member_table.setItem(row_idx, 6, QTableWidgetItem(""))  # 年份（可補）
            self.member_table.setItem(row_idx, 7, QTableWidgetItem(row.get("zodiac", "")))
            self.member_table.setItem(row_idx, 8, QTableWidgetItem(str(row.get("age", ""))))
            self.member_table.setItem(row_idx, 9, QTableWidgetItem(row.get("birth_time", "")))
            self.member_table.setItem(row_idx, 10, QTableWidgetItem(row.get("phone_home", "")))
            self.member_table.setItem(row_idx, 11, QTableWidgetItem(row.get("phone_mobile", "")))
            self.member_table.setItem(row_idx, 12, QTableWidgetItem(row.get("identity", "")))
            self.member_table.setItem(row_idx, 13, QTableWidgetItem(row.get("id", "")))  # ID 當作身份證
            self.member_table.setItem(row_idx, 14, QTableWidgetItem(row.get("address", "")))
            self.member_table.setItem(row_idx, 15, QTableWidgetItem(row.get("note", "")))
        # 調整表格大小
        self.member_table.adjust_to_contents()
    def fill_head_detail(self, data):
        self.fields["姓名："].setText(data.get("head_name", ""))
        self.fields["性別："].setText(data.get("head_gender", ""))
        self.fields["加入日期："].setText(data.get("head_joined_at", ""))
        self.fields["國曆生日："].setText(data.get("head_birthday_ad", ""))
        self.fields["農曆生日："].setText(data.get("head_birthday_lunar", ""))
        self.fields["年份："].setText("")  # 如你有欄位再補
        self.fields["身份："].setText(data.get("head_identity", ""))
        self.fields["生肖："].setText(data.get("head_zodiac", ""))
        self.fields["年齡："].setText(str(data.get("head_age", "")))
        self.fields["聯絡電話："].setText(data.get("head_phone_home", ""))
        self.fields["手機號碼："].setText(data.get("head_phone_mobile", ""))
        self.fields["出生時辰："].setText(data.get("head_birth_time", ""))
        self.fields["身分證號："].setText("")  # head_id 可以補這裡
        self.fields["電子郵件："].setText(data.get("head_email", ""))
        self.fields["信眾地址："].setText(data.get("head_address", ""))
        self.fields["郵遞區號："].setText(data.get("head_zip_code", ""))
        self.fields["備註說明："].setPlainText(data.get("household_note", ""))

    def show_household_members_by_id(self, household_id):
        members = self.controller.get_household_members(household_id)
        self.update_member_table(members)
        # self.update_stats_label(household_id, members)  # 計算丁口數等

