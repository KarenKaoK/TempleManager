from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QDateEdit, QTabWidget, QWidget, QMessageBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame
)
from PyQt5.QtCore import QDate, Qt
from datetime import datetime, date

from app.utils.print_helper import PrintHelper
from app.dialogs.new_household_dialog import NewHouseholdDialog

class IncomeExpenseDialog(QDialog):
    def __init__(self, controller, parent=None, initial_tab=0):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("收支管理作業")
        self.resize(1200, 800) # 加大視窗以容納左右分割
        self.setup_ui(initial_tab)

    def setup_ui(self, initial_tab):
        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # 收入頁面
        self.income_tab = TransactionTab(self.controller, "income", self)
        self.tabs.addTab(self.income_tab, "收入資料登錄作業")
        
        # 支出頁面
        self.expense_tab = TransactionTab(self.controller, "expense", self)
        self.tabs.addTab(self.expense_tab, "支出資料登錄作業")
        
        self.tabs.setCurrentIndex(initial_tab)
        
        layout.addWidget(self.tabs)
        
        # 底部關閉按鈕
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("關閉返回")
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addWidget(self.tabs)
        
        # 底部關閉按鈕
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("關閉返回")
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

class TransactionTab(QWidget):
    def __init__(self, controller, transaction_type, parent_dialog):
        super().__init__()
        self.controller = controller
        self.t_type = transaction_type # "income" or "expense"
        self.parent_dialog = parent_dialog
        
        # 用於暫存選擇的信徒 ID (僅 Income 用到)
        self.selected_person_id = None
        
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # --- 1. 頂部篩選工具列 (Filter Bar) ---
        filter_layout = QHBoxLayout()
        
        # 年份
        self.year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        for y in range(current_year - 5, current_year + 6):
            self.year_combo.addItem(f"{y}年", y)
        self.year_combo.setCurrentText(f"{current_year}年")
        self.year_combo.currentIndexChanged.connect(self.refresh_list)
        
        # 月份
        self.month_combo = QComboBox()
        for m in range(1, 13):
            self.month_combo.addItem(f"{m}月", m)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.currentIndexChanged.connect(self.refresh_list)
        
        # 導航按鈕
        btn_prev = QPushButton("◀ 上個月")
        btn_curr = QPushButton("本月")
        btn_next = QPushButton("下個月 ▶")
        
        btn_prev.clicked.connect(lambda: self.change_month(-1))
        btn_curr.clicked.connect(self.set_current_month)
        btn_next.clicked.connect(lambda: self.change_month(1))
        
        # 排序
        # self.sort_combo = QComboBox()
        # self.sort_combo.addItems(["日期 (新->舊)", "日期 (舊->新)"])
        
        filter_layout.addWidget(QLabel("年份:"))
        filter_layout.addWidget(self.year_combo)
        filter_layout.addWidget(QLabel("月份:"))
        filter_layout.addWidget(self.month_combo)
        filter_layout.addWidget(btn_prev)
        filter_layout.addWidget(btn_curr)
        filter_layout.addWidget(btn_next)
        filter_layout.addStretch()
        # filter_layout.addWidget(QLabel("排序:")) # 暫時不放，預設新到舊
        # filter_layout.addWidget(self.sort_combo)
        
        main_layout.addLayout(filter_layout)
        
        # --- 2. 主內容 (分割視窗：左表單，右列表) ---
        splitter = QSplitter(Qt.Horizontal)
        
        # 左側：資料登錄表單
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # 標題
        title_label = QLabel("📝 資料登錄")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        left_layout.addWidget(title_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 日期
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        
        # 收據號碼 (唯讀，自動產生)
        self.receipt_input = QLineEdit()
        self.receipt_input.setPlaceholderText("系統自動產生")
        self.receipt_input.setReadOnly(True) # 雖然唯讀，但存檔時後端會真正產生
        
        # 經手人
        self.handler_input = QLineEdit()
        
        # 項目 (Category)
        self.category_combo = QComboBox()
        
        # 金額
        self.amount_input = QLineEdit()
        
        # 摘要
        self.note_input = QLineEdit()
        
        form_layout.addRow("日期:", self.date_input)
        form_layout.addRow("收據號碼:", self.receipt_input)
        form_layout.addRow("經手人:", self.handler_input)
        form_layout.addRow("項目:", self.category_combo)
        form_layout.addRow("金額:", self.amount_input)
        form_layout.addRow("摘要:", self.note_input)
        
        left_layout.addLayout(form_layout)
        
        # 信徒搜尋區塊 (僅收入需要)
        self.person_info_widget = QWidget() # 用來顯示搜尋結果或選定的信徒
        person_layout = QFormLayout()
        
        if self.t_type == "income":
            # 搜尋框
            search_box = QHBoxLayout()
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("輸入姓名/電話搜尋...")
            search_btn = QPushButton("🔍")
            search_btn.clicked.connect(self.perform_search)
            search_box.addWidget(self.search_input)
            search_box.addWidget(search_btn)
            
            left_layout.addWidget(QLabel("<b>信徒資料 (付款人)</b>"))
            left_layout.addLayout(search_box)
            
            # 搜尋結果列表 (點選用)
            self.search_result_list = QTableWidget()
            self.search_result_list.setColumnCount(3)
            self.search_result_list.setHorizontalHeaderLabels(["姓名", "電話", "地址"])
            self.search_result_list.setMaximumHeight(100)
            self.search_result_list.setSelectionBehavior(QTableWidget.SelectRows)
            self.search_result_list.cellClicked.connect(self.on_person_selected)
            left_layout.addWidget(self.search_result_list)
            
            # 顯示選定的信徒資料
            self.payer_name_display = QLineEdit()
            self.payer_phone_display = QLineEdit()
            self.payer_name_display.setReadOnly(True)
            self.payer_phone_display.setReadOnly(True)
            self.payer_name_display.setPlaceholderText("請先搜尋並點選")
            
            person_layout.addRow("姓名:", self.payer_name_display)
            person_layout.addRow("電話:", self.payer_phone_display)
            
            # 快速建檔按鈕
            new_person_btn = QPushButton("找不到？建立新信徒資料")
            new_person_btn.clicked.connect(self.open_new_person_dialog)
            person_layout.addRow("", new_person_btn)
            
            self.person_info_widget.setLayout(person_layout)
            left_layout.addWidget(self.person_info_widget)
        else:
            # 支出：只需填寫對象名稱 (廠商/領款人)
            self.payee_input = QLineEdit()
            form_layout.insertRow(4, "支付對象:", self.payee_input) 

        left_layout.addStretch()
        
        # 按鈕區
        btn_box = QHBoxLayout()
        save_btn = QPushButton("💾 僅存檔")
        save_btn.clicked.connect(lambda: self.save_data(print_receipt=False))
        
        btn_box.addWidget(save_btn)
        if self.t_type == "income":
            save_print_btn = QPushButton("🖨️ 存檔並列印")
            save_print_btn.clicked.connect(lambda: self.save_data(print_receipt=True))
            btn_box.addWidget(save_print_btn)
            
        left_layout.addLayout(btn_box)
        left_widget.setLayout(left_layout)
        
        # 右側：列表
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        type_tc = "收入" if self.t_type == "income" else "支出"
        list_label = QLabel(f"📋 {type_tc}明細列表")
        list_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        
        self.table = QTableWidget()
        cols = ["日期", "單號", "項目", "對象", "金額", "經手人", "摘要"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 右鍵選單
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        right_layout.addWidget(list_label)
        right_layout.addWidget(self.table)
        right_widget.setLayout(right_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 2) # 右邊寬一點
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # 編輯模式狀態
        self.editing_transaction_id = None
        self.selected_person_data = None
        self.save_btn = save_btn # 存引用以便改文字
        
        # 增加取消編輯按鈕 (預設隱藏)
        self.cancel_edit_btn = QPushButton("❌ 取消編輯")
        self.cancel_edit_btn.setVisible(False)
        self.cancel_edit_btn.clicked.connect(self.cancel_edit)
        btn_box.insertWidget(0, self.cancel_edit_btn)

    def load_initial_data(self):
        # 載入項目
        if self.t_type == "income":
            items = self.controller.get_all_income_items()
        else:
            items = self.controller.get_all_expense_items()
            
        self.category_combo.clear()
        for item in items:
            self.category_combo.addItem(f"{item['id']} - {item['name']}", item) # userData 存整包
            
        # 載入列表
        self.refresh_list()

    def perform_search(self):
        kw = self.search_input.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "請輸入搜尋關鍵字")
            return
            
        results = self.controller.search_people(kw)
        if not results:
            reply = QMessageBox.question(self, "查無資料", "找不到此信徒，是否立即建立新資料？", 
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_new_person_dialog()
            return
            
        self.search_result_list.setRowCount(len(results))
        for i, row in enumerate(results):
            self.search_result_list.setItem(i, 0, QTableWidgetItem(row['name']))
            self.search_result_list.setItem(i, 1, QTableWidgetItem(row['phone_mobile'] or row['phone_home']))
            self.search_result_list.setItem(i, 2, QTableWidgetItem(row['address']))
            self.search_result_list.item(i, 0).setData(Qt.UserRole, row) # 存整包

    def on_person_selected(self, row, col):
        person_data = self.search_result_list.item(row, 0).data(Qt.UserRole)
        self.set_person(person_data)
        
    def set_person(self, person_data):
        self.selected_person_data = person_data # Store full data for address
        self.selected_person_id = person_data['id']
        self.payer_name_display.setText(person_data['name'])
        self.payer_phone_display.setText(person_data['phone_mobile'] or person_data['phone_home'])

    def open_new_person_dialog(self):
        dialog = NewHouseholdDialog(self.controller, self)
        # 用 save_data 後這裡一樣會是 Accepted (如果成功)
        if dialog.exec_() == QDialog.Accepted:
            if hasattr(dialog, 'created_person_id'):
                # new_id = dialog.created_person_id
                pass
                
            QMessageBox.information(self, "成功", "新信徒建立成功，請重新搜尋並選取。")
            if hasattr(dialog, 'name_input'):
                 self.search_input.setText(dialog.name_input.text())
                 self.perform_search()

    def change_month(self, delta):
        idx = self.month_combo.currentIndex() + delta
        year_idx = self.year_combo.currentIndex()
        
        if idx < 0:
            idx = 11
            year_idx -= 1
        elif idx > 11:
            idx = 0
            year_idx += 1
            
        if 0 <= year_idx < self.year_combo.count():
            self.year_combo.setCurrentIndex(year_idx)
            self.month_combo.setCurrentIndex(idx)

    def set_current_month(self):
        today = QDate.currentDate()
        self.year_combo.setCurrentText(f"{today.year()}年")
        self.month_combo.setCurrentIndex(today.month() - 1)

    def refresh_list(self):
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        
        start_date = f"{year}-{month:02d}-01"
        try:
           import calendar
           last_day = calendar.monthrange(year, month)[1]
           end_date = f"{year}-{month:02d}-{last_day}"
        except:
             end_date =  f"{year}-{month:02d}-31"

        data = self.controller.get_transactions(self.t_type, start_date, end_date)
        
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(row['date']))
            self.table.setItem(i, 1, QTableWidgetItem(row['receipt_number']))
            self.table.setItem(i, 2, QTableWidgetItem(f"{row['category_name']}"))
            self.table.setItem(i, 3, QTableWidgetItem(row['payer_name']))
            self.table.setItem(i, 4, QTableWidgetItem(str(row['amount'])))
            self.table.setItem(i, 5, QTableWidgetItem(row['handler']))
            self.table.setItem(i, 6, QTableWidgetItem(row['note']))
            
            # 將整筆資料存入第一欄的 UserRole，供修改/刪除/列印使用
            self.table.item(i, 0).setData(Qt.UserRole, row)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        data = self.table.item(row, 0).data(Qt.UserRole)
        if not data:
            return

        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        
        if self.t_type == "income":
            print_action = QAction("🖨️ 列印收據", self)
            print_action.triggered.connect(lambda: self.on_print_receipt(data))
            menu.addAction(print_action)
            menu.addSeparator()

        edit_action = QAction("✏️ 修改", self)
        edit_action.triggered.connect(lambda: self.load_transaction_to_form(data))
        menu.addAction(edit_action)
        
        del_action = QAction("🗑️ 刪除", self)
        del_action.triggered.connect(lambda: self.delete_transaction(data))
        menu.addAction(del_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def on_print_receipt(self, data):
        PrintHelper.print_receipt(data)

    def delete_transaction(self, data):
        reply = QMessageBox.question(
            self, "確認刪除", 
            f"確定要刪除這筆資料嗎？\n單號：{data['receipt_number']}\n金額：{data['amount']}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.controller.delete_transaction(data['id'])
                QMessageBox.information(self, "成功", "資料已刪除")
                self.refresh_list()
                
                # 如果正在編輯這筆，取消編輯
                if self.editing_transaction_id == data['id']:
                    self.cancel_edit()
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"刪除失敗: {str(e)}")

    def load_transaction_to_form(self, data):
        self.editing_transaction_id = data['id']
        
        # 填入表單
        self.date_input.setDate(QDate.fromString(data['date'], "yyyy-MM-dd"))
        self.receipt_input.setText(data['receipt_number'])
        self.handler_input.setText(data['handler'] or "")
        self.amount_input.setText(str(data['amount']))
        self.note_input.setText(data['note'] or "")
        
        # 項目 Selection
        # 比較 category_id
        cid = data['category_id']
        idx = -1
        for i in range(self.category_combo.count()):
            item_data = self.category_combo.itemData(i)
            if item_data and str(item_data['id']) == str(cid):
                idx = i
                break
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
            
        # 對象 (Income/Expense)
        if self.t_type == "income":
            if data['payer_person_id']:
                # 簡單設定，不重新 Search
                self.selected_person_id = data['payer_person_id']
                self.selected_person_data = data # Store for address (from get_transactions)
                self.payer_name_display.setText(data['payer_name'])
                # 電話沒在 transactions 裡，若要顯示要去撈，或是從 list join 來的資料裡拿
                # get_transactions 有 JOIN phone_mobile
                self.payer_phone_display.setText(data.get('phone_mobile') or "")
        else:
            self.payee_input.setText(data['payer_name'])
            
        # 切換 UI 狀態
        self.save_btn.setText("🔄 更新資料")
        self.cancel_edit_btn.setVisible(True)
        
    def cancel_edit(self):
        self.editing_transaction_id = None
        self.save_btn.setText("💾 僅存檔")
        self.cancel_edit_btn.setVisible(False)
        
        # 清空
        self.amount_input.clear()
        self.note_input.clear()
        self.receipt_input.setPlaceholderText("系統自動產生")
        self.receipt_input.setText("")
        # 日期、經手人 通常保留比較好用
        
        if self.t_type == "income":
            # 清空選定的人?? 看需求，通常清空以免誤修
            self.selected_person_id = None
            self.selected_person_data = None
            self.payer_name_display.clear()
            self.payer_phone_display.clear()
        else:
            self.payee_input.clear()

    def save_data(self, print_receipt):
        # 1. 蒐集資料
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        handler = self.handler_input.text()
        amount_str = self.amount_input.text()
        note = self.note_input.text()
        
        cat_data = self.category_combo.currentData()
        if not cat_data:
            QMessageBox.warning(self, "錯誤", "請選擇項目")
            return
            
        cat_id = cat_data['id']
        cat_name = cat_data['name']
        
        payer_person_id = None
        payer_name = ""
        
        if self.t_type == "income":
            if not self.selected_person_id:
                QMessageBox.warning(self, "錯誤", "請先搜尋並點選信徒")
                return
            payer_person_id = self.selected_person_id
            payer_name = self.payer_name_display.text()
        else:
            payer_name = self.payee_input.text()
            if not payer_name:
                QMessageBox.warning(self, "錯誤", "請輸入支付對象")
                return

        if not amount_str.isdigit():
            QMessageBox.warning(self, "錯誤", "金額必須為數字")
            return
        
        try:
            # 判斷是新增還是更新
            if self.editing_transaction_id:
                # Update
                payload = {
                    "date": date_str,
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "amount": int(amount_str),
                    "payer_person_id": payer_person_id,
                    "payer_name": payer_name,
                    "handler": handler,
                    "note": note
                }
                self.controller.update_transaction(self.editing_transaction_id, payload)
                QMessageBox.information(self, "成功", "資料已更新")
                self.cancel_edit() # 退出編輯模式
                
            else:
                # New
                receipt_num = self.controller.generate_receipt_number(date_str)
                
                # 住址 (for printing)
                payer_address = ""
                if self.t_type == "income" and hasattr(self, 'selected_person_data') and self.selected_person_data:
                    payer_address = self.selected_person_data.get('address', '')
                
                payload = {
                    "date": date_str,
                    "type": self.t_type,
                    "category_id": cat_id,
                    "category_name": cat_name,
                    "amount": int(amount_str),
                    "payer_person_id": payer_person_id,
                    "payer_name": payer_name,
                    "address": payer_address,
                    "handler": handler,
                    "receipt_number": receipt_num,
                    "note": note
                }
                self.controller.add_transaction(payload)
                QMessageBox.information(self, "成功", "資料已儲存")
                
                if print_receipt and self.t_type == "income":
                    PrintHelper.print_receipt(payload)
                
                # 清空表單 (只清部分)
                self.amount_input.clear()
                # self.note_input.clear()
                # self.selected_person_id = None ...
            
            # 刷新列表
            self.refresh_list()
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"作業失敗: {str(e)}")
