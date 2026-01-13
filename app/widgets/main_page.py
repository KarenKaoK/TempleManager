from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, 
    QTabWidget, QTableWidgetItem, QMessageBox, QDialog, QSizePolicy, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal

from app.widgets.search_bar import SearchBarWidget
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.utils.data_transformers import convert_head_to_member_format
from app.dialogs.new_member_dialog import NewMemberDialog
from app.dialogs.edit_member_dialog import EditMemberDialog

class MainPageWidget(QWidget):

    new_household_triggered = pyqtSignal()  

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.current_households = []
        self.selected_household_id = None
        layout = QVBoxLayout()
        self.fields = {}  # 用來存放欄位

        # 搜尋欄位與功能按鈕
        top_layout = QHBoxLayout()
        self.search_bar = SearchBarWidget()
        top_layout.addWidget(self.search_bar)
    

        self.add_btn = QPushButton("➕ 新增戶籍資料")
        self.add_btn.clicked.connect(self.new_household_triggered.emit)

        self.delete_btn = QPushButton("❌ 刪除戶籍資料")
        self.delete_btn.clicked.connect(self.delete_selected_household)

        self.print_btn = QPushButton("🖨️ 資料列印")
        for btn in [ self.add_btn, self.delete_btn, self.print_btn]:
            btn.setStyleSheet("font-size: 14px;")
            top_layout.addWidget(btn)

        layout.addLayout(top_layout)

        # 戶長表格
        # self.household_table = QTableWidget() # AutoResizingTableWidget 代替，已經繼承 QTableWidget
        self.household_table = AutoResizingTableWidget()
        self.household_table.setColumnCount(16)
        self.household_table.setHorizontalHeaderLabels([
            "戶號", "標籤", "戶長姓名", "性別", "國曆生日", "農曆生日", "年份", "生肖", "年齡", "生辰",
            "聯絡電話", "手機號碼", "身份", "電子郵件", "聯絡地址", "備註說明"
        ])
        
        header = self.household_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)

        # 地址欄（第 14 欄）≈ 35 個中文字
        header.resizeSection(14, 380)

        # 備註欄（第 15 欄）吃剩餘空間
        header.setStretchLastSection(True)

        self.household_table.setTextElideMode(Qt.ElideRight)

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

        header = self.member_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSection(14, 380)
        header.setStretchLastSection(True)

        self.member_table.setTextElideMode(Qt.ElideRight)

        self.member_table.setStyleSheet("font-size: 14px;")
        self.member_table.cellClicked.connect(self.on_member_row_clicked)
        left_inner.addWidget(self.member_table)

        left_table_box = QWidget()
        left_table_box.setLayout(left_inner)
        left_layout.addWidget(left_table_box)

        # 成員操作按鈕區塊（縮小按鈕間距）
        # 定義要連接的按鈕與槽函數對應關係
        self.member_buttons = {}  # 儲存按鈕參考

        btns = [
            ("➕ 新增成員", "green", self.on_add_member_clicked),
            ("🖊 修改成員", "blue", self.on_edit_member_clicked),
            ("❌ 刪除成員", "red", self.on_delete_member_clicked),
            ("☑ 設為戶長", None, self.on_set_head_clicked),
            ("🔄 戶籍變更", None, self.on_transfer_household_clicked),
            ("⬆ 上移", None, self.on_move_up_clicked),
            ("⬇ 下移", None, self.on_move_down_clicked),
            ("⛔ 關閉退出", "darkred", self.on_close_clicked),
        ]

        member_btn_layout = QVBoxLayout()
        member_btn_layout.setSpacing(2)

        for label, color, handler in btns:
            btn = QPushButton(label)
            style = "font-size: 14px; padding: 4px;"
            if color:
                style += f" color: {color};"
            btn.setStyleSheet(style)

            btn.clicked.connect(handler)  # 連接事件
            self.member_buttons[label] = btn  # 儲存參考
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
        for tab_name in ["安燈紀錄", "活動紀錄", "添油香記錄"]:
            placeholder = QWidget()
            tab_widget.addTab(placeholder, tab_name)

        splitter.addWidget(tab_widget)
        layout.addWidget(splitter)

        layout.setStretchFactor(household_group, 55)  # 上：戶長表格
        layout.setStretchFactor(splitter, 45)         # 下：成員+詳情

        self.setLayout(layout)

        # 讀取所有戶長並排序（controller 需提供這個方法）
        all_heads = self.controller.get_all_households_ordered()
        self.update_household_table(all_heads)
        # 預設載入第一筆戶長的成員與詳情
        if all_heads:
            first_head = all_heads[0]
            household_id = first_head['id']
            members = self.controller.get_household_members(household_id)
            self.update_member_table(members)
            self.fill_head_detail(first_head)
            num_adults = sum(1 for m in members if m.get("gender") == "男")
            num_dependents = sum(1 for m in members if m.get("gender") == "女")
            self.stats_label.setText(
                f"戶號：{household_id}　戶長：{first_head['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
            )

    def update_household_table(self, data):
        self.household_table.setRowCount(len(data))
        self.current_households = data  # ✅ 儲存供其他 function 使用

        for row_idx, row in enumerate(data):
            self.household_table.setItem(row_idx, 0, QTableWidgetItem(str(row.get("id", ""))))

            # 以下順序要對齊你表格標題設定的順序
            self.household_table.setItem(row_idx, 1, QTableWidgetItem("預設標籤"))
            self.household_table.setItem(row_idx, 2, QTableWidgetItem(row.get("head_name", "")))
            self.household_table.setItem(row_idx, 3, QTableWidgetItem(row.get("head_gender", "")))
            self.household_table.setItem(row_idx, 4, QTableWidgetItem(row.get("head_birthday_ad", "")))
            self.household_table.setItem(row_idx, 5, QTableWidgetItem(row.get("head_birthday_lunar", "")))
            self.household_table.setItem(row_idx, 6, QTableWidgetItem(row.get("head_birth_year", "")))
            self.household_table.setItem(row_idx, 7, QTableWidgetItem(row.get("head_zodiac", "")))
            self.household_table.setItem(row_idx, 8, QTableWidgetItem(str(row.get("head_age", ""))))
            self.household_table.setItem(row_idx, 9, QTableWidgetItem(row.get("head_birth_time", "")))
            self.household_table.setItem(row_idx, 10, QTableWidgetItem(row.get("head_phone_home", "")))
            self.household_table.setItem(row_idx, 11, QTableWidgetItem(row.get("head_phone_mobile", "")))
            self.household_table.setItem(row_idx, 12, QTableWidgetItem(row.get("head_identity", "")))
            self.household_table.setItem(row_idx, 13, QTableWidgetItem(row.get("head_email", "")))

            addr = row.get("head_address", "") or ""
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.household_table.setItem(row_idx, 14, addr_item)

            note = row.get("household_note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            self.household_table.setItem(row_idx, 15, note_item)

        
        # 調整表格大小
        # self.household_table.adjust_to_contents()

    def on_household_row_clicked(self, row, col):
        household_id_item = self.household_table.item(row, 0)  # 假設 id 在第 0 欄
        if not household_id_item:
            return

        household_id = household_id_item.text()
        self.selected_household_id = household_id

        # 取得戶長本身資料
        data = self.current_households[row] # 你需在 update_household_table() 存這個
        
        # ➤ 將戶長轉換成 member 格式，判斷丁/口
        head_as_member = convert_head_to_member_format(data)
            
        # 呼叫 controller 拿成員資料 (不含戶長)
        members = self.controller.get_household_members(household_id)
        # 過濾掉與戶長同 ID 的成員（避免重複）
        members_filtered = [
            m for m in members
            if m.get("name") != data.get("head_name")
        ]
        # 插入戶長在成員清單第一位
        full_member_list = [head_as_member] + members_filtered

        # 更新 member panel
        self.update_member_table(full_member_list, head_id=data.get("id"))

        # 更新右側戶長詳情
        self.fill_head_detail(data)

        # 更新統計標籤
        num_adults = sum(1 for m in full_member_list if m.get("gender") == "男")
        num_dependents = sum(1 for m in full_member_list if m.get("gender") == "女")
        self.stats_label.setText(
            f"戶號：{household_id}　戶長：{data['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
        )
    def update_member_table(self, data, head_id=None):
        self.member_table.setRowCount(len(data))
        for row_idx, row in enumerate(data):
            self.member_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))  # 序
            self.member_table.setItem(row_idx, 1, QTableWidgetItem(""))  # 標示（可加角色）
            # ➤ 標示（若是戶長則顯示）
            is_head = head_id is not None and row.get("id") == head_id
            self.member_table.setItem(row_idx, 1, QTableWidgetItem("戶長" if is_head else ""))
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
            
            addr = row.get("address", "") or ""
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.member_table.setItem(row_idx, 14, addr_item)

            note = row.get("note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            self.member_table.setItem(row_idx, 15, note_item)
            
            # 在任一 cell 上存放 "email", "zip_code", "joined_at" 等隱藏資料
            hidden_data = {
                "head_email": row.get("email", ""),
                "head_zip_code": row.get("zip_code", ""),
                "head_joined_at": row.get("joined_at", ""),
            }
            item = self.member_table.item(row_idx, 2)  # 用姓名那欄當作隱藏資料載體
            item.setData(Qt.UserRole, hidden_data)
        # 調整表格大小
        # self.member_table.adjust_to_contents()
        
    def on_member_row_clicked(self, row, col):
        name_item = self.member_table.item(row, 2)
        hidden = name_item.data(Qt.UserRole) or {}
        # 取出該列的所有欄位資料
        data = {
            "head_name": name_item.text(),
            "head_gender": self.member_table.item(row, 3).text(),
            "head_birthday_ad": self.member_table.item(row, 4).text(),
            "head_birthday_lunar": self.member_table.item(row, 5).text(),
            "head_birth_year": "",  # 暫不處理
            "head_zodiac": self.member_table.item(row, 7).text(),
            "head_age": self.member_table.item(row, 8).text(),
            "head_birth_time": self.member_table.item(row, 9).text(),
            "head_phone_home": self.member_table.item(row, 10).text(),
            "head_phone_mobile": self.member_table.item(row, 11).text(),
            "head_identity": self.member_table.item(row, 12).text(),
            "head_email": hidden.get("head_email", ""),
            "head_address": self.member_table.item(row, 14).text(),
            "head_zip_code": hidden.get("head_zip_code", ""),
            "head_joined_at": hidden.get("head_joined_at", ""),
            "household_note": self.member_table.item(row, 15).text()
        }

        self.fill_head_detail(data)

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

    def delete_selected_household(self):
        selected_ranges = self.household_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "刪除失敗", "請先選擇要刪除的戶籍資料。")
            return

        # 取第一個選取區塊
        selected_range = selected_ranges[0]
        row = selected_range.topRow()

        # 從指定 row 抓欄位
        household_id = self.household_table.item(row, 0).text()
        head_name = self.household_table.item(row, 2).text()

        # 檢查該戶是否有成員
        if self.controller.household_has_members(household_id):
            QMessageBox.information(
                self,
                "無法刪除",
                "此戶籍下尚有成員，請先變更戶長或移除成員後再刪除。"
            )
            return

        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除戶長：{head_name}（戶號 {household_id}）？\n刪除後無法復原！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.controller.delete_household(household_id)

            # 重新載入資料
            all_heads = self.controller.get_all_households_ordered()
            self.update_household_table(all_heads)

            # 清空下方面板
            self.update_member_table([])
            for field in self.fields.values():
                if isinstance(field, QTextEdit):
                    field.clear()
                else:
                    field.setText("")

            self.stats_label.setText("戶號：　戶長：　家庭成員共：0 丁 0 口")

    def on_add_member_clicked(self):
        """處理新增成員操作"""
        current_household_id = self.selected_household_id
        if not current_household_id:
            QMessageBox.warning(self, "尚未選取戶籍", "請先選擇一筆戶籍資料")
            return

        dialog = NewMemberDialog(self.controller, current_household_id, self)
        if dialog.exec_() == QDialog.Accepted:
            member_data = dialog.get_data()
            member_data["household_id"] = self.selected_household_id  # 關鍵補上這行

            try:
                self.controller.insert_member(member_data)
                self.refresh_member_table(self.selected_household_id)
            except Exception as e:
                QMessageBox.critical(self, "❌ 錯誤", f"新增成員時發生錯誤：{e}")

    def on_edit_member_clicked(self):
        """處理修改成員操作"""
        selected_row = self.member_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "未選取成員", "請先選擇一位成員進行編輯")
            return

        person_id = self.member_table.item(selected_row, 13).text()
        dialog = EditMemberDialog(self.controller, person_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_member_table(self.selected_household_id)

    def on_delete_member_clicked(self):
        """處理刪除成員操作"""
        selected_row = self.member_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "未選取成員", "請先選擇一位成員進行刪除")
            return

        name = self.member_table.item(selected_row, 2).text()
        person_id = self.member_table.item(selected_row, 13).text()
        is_head = self.member_table.item(selected_row, 1).text() == "戶長"

        if is_head:
            QMessageBox.warning(self, "刪除失敗", "無法直接刪除戶長，如需刪除請先變更戶長")
            return

        confirm = QMessageBox.question(self, "確認刪除", f"確定要刪除成員 {name} 嗎？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.controller.delete_member_by_id(person_id)
            self.refresh_member_table(self.selected_household_id)

    def on_set_head_clicked(self):
        """設為戶長"""
        selected_row = self.member_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "未選取成員", "請選擇一位成員設為戶長")
            return

        new_head_id = self.member_table.item(selected_row, 13).text()
        new_head_name = self.member_table.item(selected_row, 2).text()
        confirm = QMessageBox.question(self, "設為戶長", f"確定要將 {new_head_name} 設為戶長嗎？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.controller.set_household_head(self.selected_household_id, new_head_id)
            self.refresh_all_panels()

    def on_transfer_household_clicked(self):
        """戶籍變更"""
        selected_row = self.member_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "未選取成員", "請選擇一位成員進行戶籍變更")
            return

        person_id = self.member_table.item(selected_row, 13).text()
        dialog = TransferHouseholdDialog(self.controller, person_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_all_panels()

    def on_move_up_clicked(self):
        """成員上移"""
        row = self.member_table.currentRow()
        if row <= 0:
            return
        self._swap_member_rows(row, row - 1)
        self.member_table.selectRow(row - 1)

    def on_move_down_clicked(self):
        """成員下移"""
        row = self.member_table.currentRow()
        if row < 0 or row >= self.member_table.rowCount() - 1:
            return
        self._swap_member_rows(row, row + 1)
        self.member_table.selectRow(row + 1)

    def on_close_clicked(self):
        """關閉退出按鈕"""
        self.close()
    
    def refresh_member_table(self, household_id):
        if not household_id:
            return

        # 取得戶長資料
        head_data = self.controller.get_household_by_id(household_id)

        # 取得 household 成員（people）資料
        member_data = self.controller.get_household_members(household_id)

        # 戶長轉為 member 格式，插入最前面
        head_as_member = convert_head_to_member_format(head_data)
        members_filtered = [
            m for m in member_data
            if m.get("name") != head_data.get("head_name")
        ]
        # 插入戶長在成員清單第一位
        full_member_list = [head_as_member] + members_filtered

        # 更新 member panel 表格
        self.update_member_table(full_member_list, head_id=head_data.get("id"))

        # 更新統計欄
        num_adults = sum(1 for m in full_member_list if m.get("gender") == "男")
        num_dependents = sum(1 for m in full_member_list if m.get("gender") == "女")
        self.stats_label.setText(
            f"戶號：{household_id}　戶長：{head_data['head_name']}　家庭成員共：{num_adults} 丁 {num_dependents} 口"
        )
        
    def _swap_member_rows(self, row1, row2):
        for col in range(self.member_table.columnCount()):
            item1 = self.member_table.takeItem(row1, col)
            item2 = self.member_table.takeItem(row2, col)
            self.member_table.setItem(row1, col, item2)
            self.member_table.setItem(row2, col, item1)
