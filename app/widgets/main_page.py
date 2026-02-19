from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSplitter, QGroupBox, QFormLayout,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QPushButton, QGridLayout,
    QComboBox,
    QTabWidget, QTableWidgetItem, QMessageBox, QDialog, QSizePolicy, QHeaderView,
    QAbstractScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal

from app.widgets.search_bar import SearchBarWidget
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.dialogs.new_member_dialog import NewMemberDialog
from app.dialogs.edit_member_dialog import EditMemberDialog
from app.dialogs.transfer_household_dialog import TransferHouseholdDialog
from app.utils.date_utils import normalize_ymd_text


class MainPageWidget(QWidget):

    new_household_triggered = pyqtSignal()
    font_size_changed = pyqtSignal(str)

    def __init__(self, controller, user_role=None):
        super().__init__()
        self.controller = controller
        self.user_role = user_role
        self.current_households = []
        self.selected_household_id = None
        layout = QVBoxLayout()
        self.fields = {}  # 用來存放欄位

        # 搜尋欄位與功能按鈕
        top_layout = QHBoxLayout()
        self.search_bar = SearchBarWidget()
        top_layout.addWidget(self.search_bar)

        font_label = QLabel("字體大小：")
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["小", "中", "大"])
        self.font_size_combo.setCurrentText("中")
        self.font_size_combo.currentTextChanged.connect(self._on_font_size_changed)
        top_layout.addWidget(font_label)
        top_layout.addWidget(self.font_size_combo)


        self.add_btn = QPushButton("➕ 新增戶長資料")
        self.add_btn.clicked.connect(self.new_household_triggered.emit)

        self.delete_btn = QPushButton("❌ 刪除戶長資料")
        self.delete_btn.clicked.connect(self.delete_selected_household)
        self.restore_btn = QPushButton("♻ 恢復停用資料")
        self.restore_btn.clicked.connect(self.open_restore_people_dialog)

        # self.print_btn = QPushButton("🖨️ 資料列印")
        for btn in [self.add_btn, self.delete_btn, self.restore_btn]:
            top_layout.addWidget(btn)

        layout.addLayout(top_layout)

        # 戶長表格
        # self.household_table = QTableWidget() # AutoResizingTableWidget 代替，已經繼承 QTableWidget
        self.household_table = AutoResizingTableWidget()
        self.household_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.household_table.setColumnCount(12)
        self.household_table.setHorizontalHeaderLabels([
            "類型", "姓名", "性別", "國曆生日", "農曆生日", "時辰", "生肖", "年齡",
            "聯絡電話", "手機號碼", "聯絡地址", "備註說明"
        ])
        
        header = self.household_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.resizeSection(0, 50) # 類型
        header.resizeSection(1, 100) # 姓名
        header.resizeSection(2, 50) # 性別
        header.resizeSection(3, 100) # 國曆生日
        header.resizeSection(4, 100) # 農曆生日
        header.resizeSection(5, 50) # 時辰
        header.resizeSection(6, 50) # 生肖
        header.resizeSection(7, 50) # 年齡

        header.resizeSection(8, 130) # 聯絡電話
        header.resizeSection(9, 130) # 手機號碼
        header.resizeSection(10, 380)
        header.setStretchLastSection(False)

        self.household_table.setTextElideMode(Qt.ElideNone)
        self.household_table.setWordWrap(False)
        self.household_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.household_table.verticalHeader().setDefaultSectionSize(32)

        self.household_table.cellClicked.connect(self.on_household_row_clicked)


        household_group = QGroupBox("信眾戶長戶員資料")
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
        self.stats_label.setStyleSheet("color: red; font-weight: bold; padding: 2px 4px;")
        left_inner.addWidget(self.stats_label)

        # self.member_table = QTableWidget()
        self.member_table = AutoResizingTableWidget()
        self.member_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.member_table.setColumnCount(11)
        self.member_table.setHorizontalHeaderLabels([
            "姓名", "性別", "國曆生日", "農曆生日", "時辰", "生肖", "年齡",
            "聯絡電話", "手機號碼", "聯絡地址", "備註說明"
        ])

        header = self.member_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        header.resizeSection(1, 50) # 性別
        header.resizeSection(2, 100) # 國曆生日
        header.resizeSection(3, 100) # 農曆生日
        header.resizeSection(4, 50) # 時辰
        header.resizeSection(5, 50) # 生肖
        header.resizeSection(6, 50) # 年齡

        header.resizeSection(7, 130) # 聯絡電話
        header.resizeSection(8, 130) # 手機號碼
        header.resizeSection(9, 380)
        header.setStretchLastSection(False)

        self.member_table.setTextElideMode(Qt.ElideNone)
        self.member_table.setWordWrap(False)
        self.member_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.member_table.verticalHeader().setDefaultSectionSize(32)

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
            ("🔄 變更戶長", None, self.on_transfer_household_clicked),
            ("⬆ 上移", None, self.on_move_up_clicked),
            ("⬇ 下移", None, self.on_move_down_clicked),
        ]

        member_btn_layout = QVBoxLayout()
        member_btn_layout.setSpacing(2)

        for label, color, handler in btns:
            btn = QPushButton(label)
            style = "padding: 4px;"
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
        tab_widget.setMinimumWidth(600)

        # ➤ 基本資料頁籤內容（改為符合圖示布局）
        base_form = QGridLayout()
        base_form.setSpacing(8)
        base_form.setVerticalSpacing(10)
        base_form.setContentsMargins(10, 10, 10, 10)
        # 避免中文標籤（如「農曆生日」）在大字體下被截斷
        base_form.setColumnMinimumWidth(0, 96)   # 左側標籤
        base_form.setColumnMinimumWidth(1, 180)  # 左側輸入
        base_form.setColumnMinimumWidth(2, 96)   # 中間標籤
        base_form.setColumnMinimumWidth(3, 180)  # 中間輸入
        base_form.setColumnMinimumWidth(4, 96)   # 右側標籤
        base_form.setColumnMinimumWidth(5, 140)  # 右側輸入
        base_form.setColumnStretch(0, 0)
        base_form.setColumnStretch(1, 3)
        base_form.setColumnStretch(2, 0)
        base_form.setColumnStretch(3, 3)
        base_form.setColumnStretch(4, 0)
        base_form.setColumnStretch(5, 2)

        entries = [
            ("姓名：", 0, 0), ("性別：", 0, 2), 
            ("國曆生日：", 1, 0), ("農曆生日：", 1, 2),
            ("時辰：", 2, 0), ("生肖：", 2, 2), ("年齡：", 2, 4),
            ("聯絡電話：", 3, 0), ("手機號碼：", 3, 2),
            ("聯絡地址：", 5, 0),
            ("郵遞區號：", 6, 0), ("備註說明：", 7, 0)
        ]


        for label, row, col in entries:
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(90)
            label_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            base_form.addWidget(label_widget, row, col)

        self.fields = {}  #
        for label, row, col in entries:
            if label == "備註說明：":
                widget = QTextEdit()
                widget.setReadOnly(True)  # 設為唯讀
                widget.setMinimumHeight(90)
                base_form.addWidget(widget, row, col + 1, 1, 5)
            elif label == "聯絡地址：":
                widget = QLineEdit()
                widget.setReadOnly(True)  # 設為唯讀
                widget.setMinimumHeight(34)
                base_form.addWidget(widget, row, col + 1, 1, 5)

            else:
                widget = QLineEdit()
                widget.setReadOnly(True)  # 設為唯讀
                widget.setMinimumHeight(34)  # 避免大字體時內容被裁切
                # 不使用跨欄，避免壓到右側標籤（曾造成「農曆生日」只剩冒號）
                base_form.addWidget(widget, row, col + 1)
            self.fields[label] = widget

        base_widget = QWidget()
        base_widget.setLayout(base_form)
        # base_widget.setMinimumWidth(500)
        base_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        for label, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        tab_widget.addTab(base_widget, "基本資料")

        # 三個紀錄分頁：添油香 / 活動 / 安燈
        donation_tab, self.donation_summary_label, self.donation_table = self._build_income_record_tab("添油香記錄")
        tab_widget.addTab(donation_tab, "添油香記錄")

        activity_tab, self.activity_summary_label, self.activity_table = self._build_income_record_tab("活動紀錄")
        tab_widget.addTab(activity_tab, "活動紀錄")

        light_tab, self.light_summary_label, self.light_table = self._build_income_record_tab("安燈紀錄")
        tab_widget.addTab(light_tab, "安燈紀錄")

        splitter.addWidget(tab_widget)
        layout.addWidget(splitter)

        splitter.setChildrenCollapsible(False)

        # 左:右 接近 1:1（較接近實際操作需求）
        splitter.setStretchFactor(0, 50)
        splitter.setStretchFactor(1, 50)

        # 初始寬度比例（會覆蓋 stretch 的初始效果，因此需同步調整）
        splitter.setSizes([860, 860])

        layout.setStretchFactor(household_group, 55)  # 上：戶長表格
        layout.setStretchFactor(splitter, 45)         # 下：成員+詳情

        self.setLayout(layout)

        # 讀取所有信眾並排序
        all_people = self.controller.get_all_people()
        self.update_household_table(all_people)
        
        # 預設載入第一筆資料的戶籍資訊
        if all_people:
            first_p = all_people[0]
            household_id = first_p["household_id"]
            
            # Find the head's person_id for this household
            h_people = self.controller.list_people_by_household(household_id)
            head_row = next((p for p in h_people if p.get("role_in_household") == "HEAD"), first_p)
            head_person_id = head_row.get("id")
            
            self._load_household(household_id, head_person_id)
            self.fill_person_detail(first_p)
            
            self.stats_label.setText(
                f"戶長：{head_row.get('name','')}　家庭人數：{len(h_people)}"
            )

        self._apply_role_permissions()

    def _on_font_size_changed(self, size_label):
        self.font_size_changed.emit(size_label)

    def set_font_size_label(self, label):
        if label not in ("小", "中", "大"):
            label = "中"
        self.font_size_combo.blockSignals(True)
        self.font_size_combo.setCurrentText(label)
        self.font_size_combo.blockSignals(False)

    def set_user_role(self, role):
        self.user_role = role
        self._apply_role_permissions()

    def _is_admin(self):
        return (self.user_role or "").strip() == "管理員"

    def _apply_role_permissions(self):
        # 只有管理員可見「恢復停用」入口；其餘角色維持停用流程。
        if hasattr(self, "restore_btn"):
            self.restore_btn.setVisible(self._is_admin())

    @staticmethod
    def _fmt_date_text(v):
        return normalize_ymd_text(v)

    @staticmethod
    def _to_amount_number(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_amount_text(value):
        try:
            return f"{float(value):,.0f}"
        except (TypeError, ValueError):
            return str(value or "")

    def _build_income_record_tab(self, title: str):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        summary_label = QLabel(f"{title}：尚未選取信眾")
        layout.addWidget(summary_label)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["日期", "收據號碼", "項目", "金額", "經手人", "備註"])
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setTextElideMode(Qt.ElideNone)
        table.setWordWrap(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(False)
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 140)
        table.setColumnWidth(2, 180)
        table.setColumnWidth(3, 110)
        table.setColumnWidth(4, 120)
        table.setColumnWidth(5, 520)
        layout.addWidget(table)

        return tab, summary_label, table

    def _fill_income_record_table(self, table: QTableWidget, rows: list):
        table.setRowCount(len(rows))
        for r, tx in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(self._fmt_date_text(tx.get("date", "") or "")))
            table.setItem(r, 1, QTableWidgetItem(tx.get("receipt_number", "") or ""))
            table.setItem(r, 2, QTableWidgetItem(tx.get("category_name", "") or ""))
            table.setItem(r, 3, QTableWidgetItem(self._to_amount_text(tx.get("amount"))))
            table.setItem(r, 4, QTableWidgetItem(tx.get("handler", "") or ""))
            note = tx.get("note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            table.setItem(r, 5, note_item)

    def refresh_all_panels(self, select_household_id: str = None, select_head_person_id: str = None):
        """
        統一刷新：
        1) reload 所有信眾清單
        2) 更新左上表格
        3) 視需要自動選取某一戶並載入 members + 右側詳情
        """
        people = self.controller.get_all_people()
        self.update_household_table(people)

        if not people:
            self.member_table.setRowCount(0)
            return

        # 優先選指定戶長（例如新增成功後）
        if select_household_id and select_head_person_id:
            self._load_household(select_household_id, select_head_person_id)
            return

        # 否則預設載入第一人所屬戶
        first = people[0]
        # 需找到該戶的戶長 ID
        household_id = first["household_id"]
        h_people = self.controller.list_people_by_household(household_id)
        head = next((p for p in h_people if p.get("role_in_household") == "HEAD"), first)
        self._load_household(household_id, head["id"])


    def delete_selected_household(self):
        # 必須先選到一戶（_load_household 會把 selected_* 存起來）
        household_id = getattr(self, "selected_household_id", None)
        head_person_id = getattr(self, "selected_head_person_id", None)

        if not household_id or not head_person_id:
            QMessageBox.information(self, "提示", "請先從上方戶長清單選取一筆戶長資料")
            return

        # 取戶長名字（從 current_people 裡找 HEAD）
        people = getattr(self, "current_people", []) or []
        head = next((p for p in people if p.get("role_in_household") == "HEAD"), None)
        head_name = head.get("name", "") if head else ""

        msg = (
            f"確定要刪除戶長嗎？\n\n"
            f"戶長：{head_name}\n\n"
            "規則：此戶底下必須沒有戶員，才允許刪除戶長。"
        )

        box = QMessageBox(self)
        box.setWindowTitle("確認刪除戶長")
        box.setText(msg)

        btn_yes = box.addButton("是", QMessageBox.AcceptRole)
        btn_no = box.addButton("否", QMessageBox.RejectRole)
        box.setDefaultButton(btn_no)  # 預設選「否」避免誤刪

        box.exec_()

        if box.clickedButton() != btn_yes:
            return


        try:
            affected = self.controller.deactivate_household_head_if_no_members(
                household_id=household_id,
                head_person_id=head_person_id,
                require_active=True
            )

            if affected <= 0:
                QMessageBox.information(self, "提示", "此戶長可能已是停用狀態，未更新任何資料。")
            else:
                QMessageBox.information(self, "完成", f"已刪除戶長：{head_name}")

            # ✅ 刷新整頁：戶長清單 + 預設選第一戶
            self.refresh_all_panels()

            # 若刷新後完全沒戶長，順便把刪除鈕關掉
            if not getattr(self, "current_households", None):
                self.delete_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.warning(self, "刪除失敗", str(e))

    def open_restore_people_dialog(self):
        if not self._is_admin():
            QMessageBox.warning(self, "權限不足", "目前角色無權限恢復停用資料。")
            return

        inactive_people = self.controller.get_all_people(status="INACTIVE")
        if not inactive_people:
            QMessageBox.information(self, "提示", "目前沒有可恢復的停用資料。")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("恢復停用資料")
        dialog.resize(760, 420)
        layout = QVBoxLayout(dialog)

        search_layout = QHBoxLayout()
        search_label = QLabel("搜尋：")
        search_input = QLineEdit(dialog)
        search_input.setPlaceholderText("輸入姓名或電話")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)

        table = QTableWidget(dialog)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["類型", "姓名", "電話"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        def _reload_inactive(keyword=""):
            rows = self.controller.get_all_people(status="INACTIVE")
            kw = (keyword or "").strip()
            if kw:
                filtered = []
                for person in rows:
                    name = str(person.get("name", "") or "")
                    phone = str(person.get("phone_mobile") or person.get("phone_home") or "")
                    if kw in name or kw in phone:
                        filtered.append(person)
                rows = filtered

            table.setRowCount(len(rows))
            for i, person in enumerate(rows):
                role_text = "戶長" if person.get("role_in_household") == "HEAD" else "戶員"
                i0 = QTableWidgetItem(role_text)
                i0.setData(Qt.UserRole, person)
                table.setItem(i, 0, i0)
                table.setItem(i, 1, QTableWidgetItem(person.get("name", "") or ""))
                phone = person.get("phone_mobile") or person.get("phone_home") or ""
                table.setItem(i, 2, QTableWidgetItem(phone))

        _reload_inactive()
        search_input.textChanged.connect(lambda text: _reload_inactive(text))
        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        restore_btn = QPushButton("恢復")
        close_btn = QPushButton("關閉")
        btn_layout.addWidget(restore_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        def _restore_selected():
            row = table.currentRow()
            if row < 0:
                QMessageBox.warning(dialog, "提示", "請先選取一筆停用資料。")
                return

            item = table.item(row, 0)
            person = item.data(Qt.UserRole) if item else None
            if not person:
                QMessageBox.warning(dialog, "提示", "找不到選取資料，請重試。")
                return

            name = person.get("name", "")
            confirm = QMessageBox.question(
                dialog,
                "確認恢復",
                f"確定要恢復「{name}」嗎？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            try:
                self.controller.reactivate_person(person.get("id"))
                QMessageBox.information(dialog, "完成", f"已恢復：{name}")

                household_id = person.get("household_id")
                if person.get("role_in_household") == "HEAD":
                    head_person_id = person.get("id")
                else:
                    active_people = self.controller.list_people_by_household(household_id, status="ACTIVE")
                    head = next((p for p in active_people if p.get("role_in_household") == "HEAD"), None)
                    head_person_id = head.get("id") if head else None

                if household_id and head_person_id:
                    self.refresh_all_panels(
                        select_household_id=household_id,
                        select_head_person_id=head_person_id
                    )
                else:
                    self.refresh_all_panels()

                _reload_inactive(search_input.text())
            except Exception as e:
                QMessageBox.warning(dialog, "恢復失敗", str(e))

        restore_btn.clicked.connect(_restore_selected)
        close_btn.clicked.connect(dialog.accept)
        dialog.exec_()


    def _get_selected_person_id(self):
        row = self.member_table.currentRow()
        if row < 0:
            return None
        item0 = self.member_table.item(row, 0)
        return item0.data(Qt.UserRole) if item0 else None


    def update_household_table(self, data):
        self.household_table.setRowCount(len(data))
        self.current_households = data # 這裡其實是 current_people_list

        for r, person in enumerate(data):
            # 0 類型
            role = person.get("role_in_household", "")
            role_text = "戶長" if role == "HEAD" else "戶員"
            role_item = QTableWidgetItem(role_text)
            if role == "HEAD":
                role_item.setForeground(Qt.red)
            self.household_table.setItem(r, 0, role_item)

            # 1 姓名（順便存 meta：household_id + head_person_id）
            # 注意：點擊這一行應該還是載入該人的「整戶」
            name = person.get("name", "") or ""
            item1 = QTableWidgetItem(name)
            item1.setData(Qt.UserRole, {
                "household_id": person.get("household_id"),
                "person_id": person.get("id")  # 這是該人的 id
            })
            self.household_table.setItem(r, 1, item1)

            # 2 性別
            self.household_table.setItem(r, 2, QTableWidgetItem(person.get("gender", "") or ""))

            # 3 國曆生日
            self.household_table.setItem(r, 3, QTableWidgetItem(self._fmt_date_text(person.get("birthday_ad", "") or "")))

            # 4 農曆生日
            lunar = self._fmt_date_text(person.get("birthday_lunar", "") or "")
            if str(person.get("lunar_is_leap", "0")) == "1" and lunar:
                lunar = f"{lunar}(閏)"
            self.household_table.setItem(r, 4, QTableWidgetItem(lunar))

            # 5 時辰
            self.household_table.setItem(r, 5, QTableWidgetItem(person.get("birth_time", "") or ""))

            # 6 生肖
            self.household_table.setItem(r, 6, QTableWidgetItem(str(person.get("zodiac", "") or "")))

            # 7 年齡
            age = person.get("age", "")
            self.household_table.setItem(r, 7, QTableWidgetItem("" if age is None else str(age)))

            # 8 聯絡電話
            self.household_table.setItem(r, 8, QTableWidgetItem(person.get("phone_home", "") or ""))

            # 9 手機
            self.household_table.setItem(r, 9, QTableWidgetItem(person.get("phone_mobile", "") or ""))

            # 10 地址
            addr = person.get("address", "") or ""
            addr_item = QTableWidgetItem(addr)
            addr_item.setToolTip(addr)
            self.household_table.setItem(r, 10, addr_item)

            # 11 備註
            note = person.get("note", "") or ""
            note_item = QTableWidgetItem(note)
            note_item.setToolTip(note)
            self.household_table.setItem(r, 11, note_item)
        self.household_table.resizeColumnsToContents()



    def on_household_row_clicked(self, row, col):
        item1 = self.household_table.item(row, 1)
        if not item1:
            return
        meta = item1.data(Qt.UserRole) or {}
        household_id = meta.get("household_id")
        person_id = meta.get("person_id")
        
        # 找到該戶的戶長
        h_people = self.controller.list_people_by_household(household_id)
        head = next((p for p in h_people if p.get("role_in_household") == "HEAD"), None)
        head_person_id = head["id"] if head else person_id

        if household_id and head_person_id:
            self._load_household(household_id, head_person_id)
            
            # 選中該人
            p = next((x for x in h_people if x.get("id") == person_id), None)
            if p:
                self.fill_person_detail(p)
                # 在下方表格選中該人
                member_row = self._find_member_row_by_person_id(person_id)
                if member_row is not None:
                    self.member_table.selectRow(member_row)

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
            self.member_table.setItem(r, 2, QTableWidgetItem(self._fmt_date_text(p.get("birthday_ad", "") or "")))

            # 3 農曆生日（含閏月可自行決定要不要顯示）
            lunar = self._fmt_date_text(p.get("birthday_lunar", "") or "")
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
        self.member_table.resizeColumnsToContents()

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
        set_text("國曆生日：", self._fmt_date_text(p.get("birthday_ad", "") or ""))

        lunar = self._fmt_date_text(p.get("birthday_lunar", "") or "")
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
        self._refresh_donation_records(p)

    def _refresh_donation_records(self, person: dict):
        if not hasattr(self, "donation_table"):
            return
        person_id = str(person.get("id") or "")
        name = person.get("name", "") or ""
        if not person_id:
            self.donation_summary_label.setText("添油香記錄：尚未選取信眾")
            self.donation_table.setRowCount(0)
            if hasattr(self, "activity_summary_label"):
                self.activity_summary_label.setText("活動紀錄：尚未選取信眾")
            if hasattr(self, "activity_table"):
                self.activity_table.setRowCount(0)
            if hasattr(self, "light_summary_label"):
                self.light_summary_label.setText("安燈紀錄：尚未選取信眾")
            if hasattr(self, "light_table"):
                self.light_table.setRowCount(0)
            return

        all_rows = self.controller.get_income_transactions_by_person(person_id)
        activity_rows = []
        light_rows = []
        donation_rows = []

        for tx in all_rows:
            cid = str(tx.get("category_id", "") or "").strip()
            if cid == "90":
                activity_rows.append(tx)
            elif cid == "91":
                light_rows.append(tx)
            else:
                donation_rows.append(tx)

        donation_total = sum(self._to_amount_number(tx.get("amount")) for tx in donation_rows)
        activity_total = sum(self._to_amount_number(tx.get("amount")) for tx in activity_rows)
        light_total = sum(self._to_amount_number(tx.get("amount")) for tx in light_rows)

        self.donation_summary_label.setText(
            f"添油香記錄：{name}（共 {len(donation_rows)} 筆，總額 {donation_total:,.0f} 元）"
        )
        if hasattr(self, "activity_summary_label"):
            self.activity_summary_label.setText(
                f"活動紀錄：{name}（共 {len(activity_rows)} 筆，總額 {activity_total:,.0f} 元）"
            )
        if hasattr(self, "light_summary_label"):
            self.light_summary_label.setText(
                f"安燈紀錄：{name}（共 {len(light_rows)} 筆，總額 {light_total:,.0f} 元）"
            )

        self._fill_income_record_table(self.donation_table, donation_rows)
        if hasattr(self, "activity_table"):
            self._fill_income_record_table(self.activity_table, activity_rows)
        if hasattr(self, "light_table"):
            self._fill_income_record_table(self.light_table, light_rows)
    
    

    def show_household_members_by_id(self, household_id):
        people = self.controller.list_people_by_household(household_id)
        members = [p for p in people if p.get("role_in_household") == "MEMBER"]
        self.update_member_table(members)
        # self.update_stats_label(household_id, members)  # 計算丁口數等

    

    def on_add_member_clicked(self):
        """處理新增成員操作"""
        if not self.selected_household_id or not getattr(self, "selected_head_person_id", None):
            QMessageBox.warning(self, "尚未選取戶長", "請先選擇一筆戶長資料")
            return

        head_person_id = self.selected_head_person_id

        dialog = NewMemberDialog(self.controller, head_person_id, self)

        if dialog.exec_() == QDialog.Accepted:
            member_data = dialog.get_data()  # 若你的 dialog 叫 get_payload，就改成 get_payload()

            try:
                self.controller.create_people(head_person_id, member_data)
                # 新增後需要同步刷新上方「信眾戶長戶員資料」與下方明細
                self.refresh_all_panels(
                    select_household_id=self.selected_household_id,
                    select_head_person_id=head_person_id
                )

            except Exception as e:
                QMessageBox.critical(self, "❌ 錯誤", f"新增成員時發生錯誤：{e}")

    def on_edit_member_clicked(self):
        person_id = self._get_selected_person_id()
        if not person_id:
            QMessageBox.information(self, "提示", "請先選取成員")
            return

        person = next((p for p in getattr(self, "current_people", []) if p.get("id") == person_id), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該成員資料，請重新選取戶長")
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

        box = QMessageBox(self)
        box.setWindowTitle("確認刪除")
        box.setText(f"確定要刪除成員 {name} 嗎？")

        btn_yes = box.addButton("是", QMessageBox.AcceptRole)
        btn_no = box.addButton("否", QMessageBox.RejectRole)

        box.setDefaultButton(btn_no)  # 預設選「否」避免誤刪

        box.exec_()

        if box.clickedButton() == btn_yes:
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
        
        box = QMessageBox(self)
        box.setWindowTitle("分戶確認")
        box.setText(
            f"確定要將「{name}」分戶成為新戶長嗎？\n\n"
            "此動作會建立一個新的戶長，並將此人移到新戶長。"
        )

        btn_yes = box.addButton("是", QMessageBox.AcceptRole)
        btn_no = box.addButton("否", QMessageBox.RejectRole)

        box.setDefaultButton(btn_no)  # 預設選「否」避免誤操作

        box.exec_()

        if box.clickedButton() != btn_yes:
            return


        try:
            # ✅ controller 會回傳 new_household_id
            new_household_id = self.controller.split_member_to_new_household(person_id)

            # ✅ 分戶後：刷新戶長清單 + 直接切到新戶長（新戶長就是 person_id）
            self.refresh_all_panels(
                select_household_id=new_household_id,
                select_head_person_id=person_id
            )

            QMessageBox.information(self, "完成", f"已分戶：{name} 已成為新戶長")

        except Exception as e:
            QMessageBox.critical(self, "❌ 分戶失敗", f"{e}")


    def on_transfer_household_clicked(self):
        """戶長變更：把選取的 MEMBER 移到另一位戶長底下"""
        member_person_id = self._get_selected_person_id()
        if not member_person_id:
            QMessageBox.warning(self, "未選取成員", "請先選擇一位成員進行戶長變更")
            return

        people = getattr(self, "current_people", []) or []
        member = next((p for p in people if p.get("id") == member_person_id), None)
        if not member:
            QMessageBox.warning(self, "資料錯誤", "找不到該成員資料，請重新選取戶長")
            return

        if member.get("role_in_household") != "MEMBER":
            QMessageBox.information(self, "提示", "變更戶長只適用於成員，戶長請用變更戶長流程")
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
            "確認變更戶長",
            f"確定要將「{name}」移至：\n{target_text}\n\n此動作會把該成員搬到目標戶長的戶長底下。",
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

            # 4) 刷新，並切到新戶長戶員（讓使用者立即看到結果）
            self.refresh_all_panels(
                select_household_id=target_household_id,
                select_head_person_id=target_head_person_id
            )

            QMessageBox.information(self, "完成", f"變更戶長完成：{name} 已移至目標戶長底下")

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

    
