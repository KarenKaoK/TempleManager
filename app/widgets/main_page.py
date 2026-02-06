from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout, 
    QTabWidget, QTableWidgetItem, QMessageBox, QDialog, QSizePolicy, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal

from app.widgets.search_bar import SearchBarWidget
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.dialogs.new_member_dialog import NewMemberDialog
from app.dialogs.edit_member_dialog import EditMemberDialog
from app.dialogs.transfer_household_dialog import TransferHouseholdDialog


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
        self.delete_btn.setEnabled(False)
        self.delete_btn.setToolTip("目前版本尚未支援刪除戶籍")
        

        self.delete_btn.clicked.connect(self.delete_selected_household)

        self.print_btn = QPushButton("🖨️ 資料列印")
        for btn in [ self.add_btn, self.delete_btn, self.print_btn]:
            btn.setStyleSheet("font-size: 14px;")
            top_layout.addWidget(btn)

        layout.addLayout(top_layout)

        # 戶長表格
        # self.household_table = QTableWidget() # AutoResizingTableWidget 代替，已經繼承 QTableWidget
        self.household_table = AutoResizingTableWidget()
        self.household_table.setColumnCount(11)
        self.household_table.setHorizontalHeaderLabels([
            "戶長姓名", "性別", "國曆生日", "農曆生日", "時辰", "生肖", "年齡",
            "聯絡電話", "手機號碼", "聯絡地址", "備註說明"
        ])
        
        header = self.household_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSection(1, 50) # 性別
        header.resizeSection(2, 100) # 國曆生日
        header.resizeSection(3, 100) # 農曆生日
        header.resizeSection(4, 50) # 時辰
        header.resizeSection(5, 50) # 生肖
        header.resizeSection(6, 50) # 年齡

        header.resizeSection(7, 130) # 聯絡電話
        header.resizeSection(8, 130) # 手機號碼
        header.resizeSection(9, 380)
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
        self.member_table.setColumnCount(11)
        self.member_table.setHorizontalHeaderLabels([
            "姓名", "性別", "國曆生日", "農曆生日", "時辰", "生肖", "年齡",
            "聯絡電話", "手機號碼", "聯絡地址", "備註說明"
        ])

        header = self.member_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)

        header.resizeSection(1, 50) # 性別
        header.resizeSection(2, 100) # 國曆生日
        header.resizeSection(3, 100) # 農曆生日
        header.resizeSection(4, 50) # 時辰
        header.resizeSection(5, 50) # 生肖
        header.resizeSection(6, 50) # 年齡

        header.resizeSection(7, 130) # 聯絡電話
        header.resizeSection(8, 130) # 手機號碼
        header.resizeSection(9, 380)
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
            ("🧾 分戶成新戶長", None, self.on_set_head_clicked),
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
            ("姓名：", 0, 0), ("性別：", 0, 2), 
            ("國曆生日：", 1, 0), ("農曆生日：", 1, 2), ("時辰：", 1, 4),
            ("生肖：", 2, 2), ("年齡：", 2, 4),
            ("聯絡電話：", 3, 0), ("手機號碼：", 3, 2), ("：", 3, 4),
            ("聯絡地址：", 5, 0),
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
            elif label == "聯絡地址：":
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
        all_heads = self.controller.list_household()
        self.update_household_table(all_heads)
        # 預設載入第一筆戶長的成員與詳情
        if all_heads:
            first_head = all_heads[0]
            household_id = first_head["household_id"]
            head_person_id = first_head["head_person_id"]
            self._load_household(household_id, head_person_id)
            members = self.controller.list_people_by_household(household_id)
       
            self.fill_person_detail(first_head)

           
            self.stats_label.setText(
                f"戶長：{first_head.get('name','')}　家庭人數：{len(members)}"
            )

    def refresh_all_panels(self, select_household_id: str = None, select_head_person_id: str = None):
        """
        新增/修改完戶籍後，用這支統一刷新：
        1) reload 戶長清單
        2) 更新戶長 table
        3) 視需要自動選取某一戶並載入 members + 右側詳情
        """
        heads = self.controller.list_household()
        self.update_household_table(heads)

        if not heads:
            self.member_table.setRowCount(0)
            return

        # 優先選指定戶籍（例如新增成功後）
        if select_household_id and select_head_person_id:
            self._load_household(select_household_id, select_head_person_id)
            return

        # 否則預設載入第一戶
        first = heads[0]
        self._load_household(first["household_id"], first["head_person_id"])


    def delete_selected_household(self):
            QMessageBox.information(
                self,
                "尚未支援",
                "目前版本尚未提供刪除戶籍功能"
            )
            return

    def _get_selected_person_id(self):
        row = self.member_table.currentRow()
        if row < 0:
            return None
        item0 = self.member_table.item(row, 0)
        return item0.data(Qt.UserRole) if item0 else None


    def update_household_table(self, data):
        self.household_table.setRowCount(len(data))
        self.current_households = data

        for r, head in enumerate(data):
            # 0 姓名（順便存 meta：household_id + head_person_id）
            name = head.get("name", "") or ""
            item0 = QTableWidgetItem(name)
            item0.setData(Qt.UserRole, {
                "household_id": head.get("household_id"),
                "head_person_id": head.get("id")  # head 的 person id
            })
            self.household_table.setItem(r, 0, item0)

            # 1 性別
            self.household_table.setItem(r, 1, QTableWidgetItem(head.get("gender", "") or ""))

            # 2 國曆生日
            self.household_table.setItem(r, 2, QTableWidgetItem(head.get("birthday_ad", "") or ""))

            # 3 農曆生日（含閏月）
            lunar = head.get("birthday_lunar", "") or ""
            if str(head.get("lunar_is_leap", "0")) == "1" and lunar:
                lunar = f"{lunar}(閏)"
            self.household_table.setItem(r, 3, QTableWidgetItem(lunar))

            # 4 時辰
            self.household_table.setItem(r, 4, QTableWidgetItem(head.get("birth_time", "") or ""))

            # 5 生肖
            self.household_table.setItem(r, 5, QTableWidgetItem(str(head.get("zodiac", "") or "")))

            # 6 年齡
            age = head.get("age", "")
            self.household_table.setItem(r, 6, QTableWidgetItem("" if age is None else str(age)))

            # 7 聯絡電話
            self.household_table.setItem(r, 7, QTableWidgetItem(head.get("phone_home", "") or ""))

            # 8 手機
            self.household_table.setItem(r, 8, QTableWidgetItem(head.get("phone_mobile", "") or ""))

            # 10 地址（加 tooltip）
            addr = head.get("address", "") or ""
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.household_table.setItem(r, 9, addr_item)

            # 11 備註（加 tooltip）
            note = head.get("note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            self.household_table.setItem(r, 10, note_item)



    def on_household_row_clicked(self, row, col):
        item0 = self.household_table.item(row, 0)
        if not item0:
            return
        meta = item0.data(Qt.UserRole) or {}
        household_id = meta.get("household_id")
        head_person_id = meta.get("head_person_id")
        if household_id and head_person_id:
            self._load_household(household_id, head_person_id)

    def update_member_table(self, people):
        """
        member_table header (10 cols):
        0 姓名
        1 性別
        2 國曆生日
        3 農曆生日
        4 時辰
        5 生肖
        6 年齡
        7 聯絡電話
        8 手機號碼
        9 聯絡地址
        10 備註說明
        """
        self.member_table.setRowCount(len(people))

        for r, p in enumerate(people):
            # 0 姓名（把 person_id 存在 UserRole，供刪除/修改/設戶長用）
            name = p.get("name", "") or ""
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, p.get("id"))
            self.member_table.setItem(r, 0, name_item)

            # 1 性別
            self.member_table.setItem(r, 1, QTableWidgetItem(p.get("gender", "") or ""))

            # 2 國曆生日
            self.member_table.setItem(r, 2, QTableWidgetItem(p.get("birthday_ad", "") or ""))

            # 3 農曆生日（含閏月可自行決定要不要顯示）
            lunar = p.get("birthday_lunar", "") or ""
            if int(p.get("lunar_is_leap") or 0) == 1 and lunar:
                lunar = f"{lunar}(閏)"
            self.member_table.setItem(r, 3, QTableWidgetItem(lunar))

            # 4 時辰
            self.member_table.setItem(r, 4, QTableWidgetItem(p.get("birth_time", "") or ""))

            # 5 生肖
            self.member_table.setItem(r, 5, QTableWidgetItem(str(p.get("zodiac", "") or "")))

            # 6 年齡
            age = p.get("age", "")
            self.member_table.setItem(r, 6, QTableWidgetItem("" if age is None else str(age)))

            # 7 聯絡電話（住家）
            self.member_table.setItem(r, 7, QTableWidgetItem(p.get("phone_home", "") or ""))

            # 8 手機號碼
            self.member_table.setItem(r, 8, QTableWidgetItem(p.get("phone_mobile", "") or ""))

            # 9 聯絡地址（加 tooltip 避免太長）
            addr = p.get("address", "") or ""
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.member_table.setItem(r, 9, addr_item)

            # 10 備註說明（加 tooltip）
            note = p.get("note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            self.member_table.setItem(r, 10, note_item)

    def on_member_row_clicked(self, row, col):
        """
        點選成員列 -> 右側顯示該成員詳情
        改成：不依賴 table 欄位 index，直接用 current_people[row]
        """
        try:
            people = getattr(self, "current_people", []) or []
            if row < 0 or row >= len(people):
                return

            p = people[row]
            self.fill_person_detail(p)

        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"載入成員資料失敗：{e}")

    def fill_person_detail(self, p: dict):
        """
        右側基本資料頁籤顯示（依目前 entries 欄位）
        """
        def set_text(label, value):
            w = self.fields.get(label)
            if w is None:
                return
            if hasattr(w, "setPlainText"):
                w.setPlainText(value or "")
            else:
                w.setText(value or "")

        # 基本欄位
        set_text("姓名：", p.get("name", "") or "")
        set_text("性別：", p.get("gender", "") or "")
        set_text("國曆生日：", p.get("birthday_ad", "") or "")

        lunar = p.get("birthday_lunar", "") or ""
        if int(p.get("lunar_is_leap") or 0) == 1 and lunar:
            lunar = f"{lunar}(閏)"
        set_text("農曆生日：", lunar)

        set_text("時辰：", p.get("birth_time", "") or "")
        set_text("生肖：", str(p.get("zodiac", "") or ""))

        age = p.get("age", "")
        set_text("年齡：", "" if age is None else str(age))

        # 聯絡方式
        set_text("聯絡電話：", p.get("phone_home", "") or "")
        set_text("手機號碼：", p.get("phone_mobile", "") or "")

        # 地址與備註
        set_text("聯絡地址：", p.get("address", "") or "")
        set_text("郵遞區號：", p.get("zip_code", "") or "")
        set_text("備註說明：", p.get("note", "") or "")
    
    

    def show_household_members_by_id(self, household_id):
        people = self.controller.list_people_by_household(household_id)
        members = [p for p in people if p.get("role_in_household") == "MEMBER"]
        self.update_member_table(members)
        # self.update_stats_label(household_id, members)  # 計算丁口數等

    

    def on_add_member_clicked(self):
        """處理新增成員操作"""
        if not self.selected_household_id or not getattr(self, "selected_head_person_id", None):
            QMessageBox.warning(self, "尚未選取戶籍", "請先選擇一筆戶籍資料")
            return

        head_person_id = self.selected_head_person_id

        dialog = NewMemberDialog(self.controller, head_person_id, self)

        if dialog.exec_() == QDialog.Accepted:
            member_data = dialog.get_data()  # 若你的 dialog 叫 get_payload，就改成 get_payload()

            try:
                self.controller.create_people(head_person_id, member_data)
                self._load_household(self.selected_household_id, head_person_id)

            except Exception as e:
                QMessageBox.critical(self, "❌ 錯誤", f"新增成員時發生錯誤：{e}")

    def on_edit_member_clicked(self):
        person_id = self._get_selected_person_id()
        if not person_id:
            QMessageBox.information(self, "提示", "請先選取成員")
            return

        person = next((p for p in getattr(self, "current_people", []) if p.get("id") == person_id), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該成員資料，請重新選取戶籍")
            return

        dialog = EditMemberDialog(self.controller, person, self)
        if dialog.exec_() == QDialog.Accepted:
            # 用新流程刷新（不要用 refresh_member_table）
            self.refresh_all_panels(
                select_household_id=self.selected_household_id,
                select_head_person_id=self.selected_head_person_id
            )


    def on_delete_member_clicked(self):
        person_id = self._get_selected_person_id()
        if not person_id:
            QMessageBox.warning(self, "未選取成員", "請先選擇一位成員進行刪除")
            return

        person = next((p for p in getattr(self, "current_people", []) if p.get("id") == person_id), None)
        name = person.get("name", "") if person else ""
        is_head = (person.get("role_in_household") == "HEAD") if person else False

        if is_head:
            QMessageBox.warning(self, "刪除失敗", "無法直接刪除戶長，如需刪除請先變更戶長")
            return

        confirm = QMessageBox.question(self, "確認刪除", f"確定要刪除成員 {name} 嗎？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.controller.deactivate_person(person_id, allow_head=False)
            self._load_household(self.selected_household_id, self.selected_head_person_id)


    def on_set_head_clicked(self):
        person_id = self._get_selected_person_id()
        if not person_id:
            QMessageBox.warning(self, "未選取成員", "請選擇一位成員")
            return

        person = next((p for p in getattr(self, "current_people", []) if p.get("id") == person_id), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該成員資料")
            return

        if person.get("role_in_household") == "HEAD":
            QMessageBox.information(self, "提示", "此人已是戶長")
            return

        name = person.get("name", "")
        confirm = QMessageBox.question(
            self,
            "分戶確認",
            f"確定要將「{name}」分戶成為新戶籍的戶長嗎？\n\n"
            "此動作會建立一個新的戶籍，並將此人移到新戶籍。",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            # ✅ controller 會回傳 new_household_id
            new_household_id = self.controller.split_member_to_new_household(person_id)

            # ✅ 分戶後：刷新戶長清單 + 直接切到新戶籍（新戶長就是 person_id）
            self.refresh_all_panels(
                select_household_id=new_household_id,
                select_head_person_id=person_id
            )

            QMessageBox.information(self, "完成", f"已分戶：{name} 已成為新戶長")

        except Exception as e:
            QMessageBox.critical(self, "❌ 分戶失敗", f"{e}")


    def on_transfer_household_clicked(self):
        """戶籍變更：把選取的 MEMBER 移到另一位戶長底下"""
        member_person_id = self._get_selected_person_id()
        if not member_person_id:
            QMessageBox.warning(self, "未選取成員", "請先選擇一位成員進行戶籍變更")
            return

        people = getattr(self, "current_people", []) or []
        member = next((p for p in people if p.get("id") == member_person_id), None)
        if not member:
            QMessageBox.warning(self, "資料錯誤", "找不到該成員資料，請重新選取戶籍")
            return

        if member.get("role_in_household") != "MEMBER":
            QMessageBox.information(self, "提示", "戶籍變更只適用於成員（MEMBER），戶長請用變更戶長流程")
            return

        current_head = next((p for p in people if p.get("role_in_household") == "HEAD"), None)
        if not current_head:
            QMessageBox.warning(self, "資料錯誤", "找不到目前戶長資料（資料完整性異常）")
            return

        # 1) 跳 dialog 讓你選目標戶長
        dlg = TransferHouseholdDialog(self.controller, member, current_head, self)
        if dlg.exec_() != QDialog.Accepted:
            return

        target_head_person_id = dlg.get_target_head_person_id()
        if not target_head_person_id:
            return

        # 2) 再做一次確認（避免誤操作）
        target_text = dlg.cmb_heads.currentText()
        name = member.get("name", "")
        confirm = QMessageBox.question(
            self,
            "確認戶籍變更",
            f"確定要將「{name}」移至：\n{target_text}\n\n此動作會把該成員搬到目標戶長的戶籍底下。",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        # 3) 執行搬家
        try:
            target_household_id = self.controller.transfer_member_to_head(
                member_person_id=member_person_id,
                target_head_person_id=target_head_person_id,
                require_active=True
            )

            # 4) 刷新，並切到新戶籍（讓使用者立即看到結果）
            self.refresh_all_panels(
                select_household_id=target_household_id,
                select_head_person_id=target_head_person_id
            )

            QMessageBox.information(self, "完成", f"戶籍變更完成：{name} 已移至目標戶長底下")

        except Exception as e:
            QMessageBox.critical(self, "❌ 變更失敗", str(e))


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
        self._load_household(self.selected_household_id, self.selected_head_person_id)


        
    def _swap_member_rows(self, row1, row2):
        for col in range(self.member_table.columnCount()):
            item1 = self.member_table.takeItem(row1, col)
            item2 = self.member_table.takeItem(row2, col)
            self.member_table.setItem(row1, col, item2)
            self.member_table.setItem(row2, col, item1)

    def _find_member_row_by_person_id(self, person_id: str):
        if not person_id:
            return None
        for r in range(self.member_table.rowCount()):
            item0 = self.member_table.item(r, 0)
            if item0 and item0.data(Qt.UserRole) == person_id:
                return r
        return None


    def _load_household(self, household_id: str, head_person_id: str):
        self.selected_household_id = household_id
        self.selected_head_person_id = head_person_id

        people = self.controller.list_people_by_household(household_id, status="ACTIVE")
        self.current_people = people

        self.update_member_table(people)

        # 預設右側顯示 HEAD
        head = next((p for p in people if p.get("role_in_household") == "HEAD"), None)
        if head:
            self.fill_person_detail(head)

        # stats（用 member_count 比較準：controller list_household 才有）
        self.stats_label.setText(f"戶長：{head.get('name','') if head else ''}　家庭人數：{len(people)}")

    