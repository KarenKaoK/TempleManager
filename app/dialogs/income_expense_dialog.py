from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QDateEdit, QTabWidget, QWidget, QMessageBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame, QListView, QAbstractSpinBox
)
from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from datetime import date

from app.utils.print_helper import PrintHelper
from app.dialogs.new_household_dialog import NewHouseholdDialog
from app.utils.date_utils import parse_qdate_flexible, qdate_to_db_ymd, to_ui_ymd_text
from app.auth.permissions import (
    can_edit_any_date,
    can_edit_handler,
    can_view_expense_entry,
    can_view_income_all_dates,
)


class CategoryComboBox(QComboBox):
    """項目下拉：展開時自動加寬，避免長文字被截斷。"""
    def showPopup(self):
        view = self.view()
        fm = self.fontMetrics()
        max_text_width = 0
        for i in range(self.count()):
            max_text_width = max(max_text_width, fm.horizontalAdvance(self.itemText(i)))

        popup_width = max(self.width(), max_text_width + 56)
        view.setMinimumWidth(popup_width)
        super().showPopup()


def style_combo_with_dividers(combo: QComboBox):
    """統一下拉選單樣式：柔和分隔線、較清楚的選取態。"""
    combo.setStyleSheet("""
        QComboBox {
            combobox-popup: 0;
        }
        QComboBox QAbstractItemView {
            border-left: 1px solid #D9D1C8;
            border-right: 1px solid #D9D1C8;
            border-top: 0;
            border-bottom: 0;
            background: #FFFFFF;
            selection-background-color: #F8EFE6;
            selection-color: #2B2B2B;
            outline: 0;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding: 4px 10px;
            border-bottom: 1px solid #EEE8E1;
            background: #FFFFFF;
        }
        QComboBox QAbstractItemView::item:last {
            border-bottom: none;
        }
        QComboBox QAbstractItemView::item:hover {
            background: #FBF5EE;
        }
    """)


class IncomeExpensePage(QWidget):
    """收支管理頁面版（供 MainWindow stack 使用）。"""
    request_close = pyqtSignal()

    def __init__(self, controller, parent=None, initial_tab=0, user_role=None, current_operator_name=""):
        super().__init__(parent)
        self.controller = controller
        self.user_role = user_role
        self.current_operator_name = (current_operator_name or "").strip()
        self.expense_tab = None
        self._build_ui(initial_tab)

    def _build_ui(self, initial_tab: int):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self.income_tab = TransactionTab(
            self.controller, "income", self, self.user_role, self.current_operator_name
        )
        self.tabs.addTab(self.income_tab, "收入資料登錄作業")
        if can_view_expense_entry(self.user_role):
            self.expense_tab = TransactionTab(
                self.controller, "expense", self, self.user_role, self.current_operator_name
            )
            self.tabs.addTab(self.expense_tab, "支出資料登錄作業")
        # 切換分頁時即時刷新，避免殘留舊列表
        self.tabs.currentChanged.connect(lambda _idx: self.refresh_current_tab())
        can_open_expense = self.expense_tab is not None
        target_idx = 1 if int(initial_tab or 0) == 1 and can_open_expense else 0
        self.tabs.setCurrentIndex(target_idx)
        layout.addWidget(self.tabs)

        foot = QHBoxLayout()
        foot.addStretch()
        btn_close = QPushButton("關閉返回")
        btn_close.setMinimumWidth(120)
        btn_close.clicked.connect(self.request_close.emit)
        foot.addWidget(btn_close)
        layout.addLayout(foot)

    def refresh_current_tab(self):
        idx = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        tab = self.income_tab if idx == 0 else self.expense_tab
        if tab is None:
            return
        if hasattr(tab, "refresh_list"):
            tab.refresh_list()

    def refresh_all_tabs(self):
        if hasattr(self, "income_tab") and hasattr(self.income_tab, "refresh_list"):
            self.income_tab.refresh_list()
        if self.expense_tab is not None and hasattr(self.expense_tab, "refresh_list"):
            self.expense_tab.refresh_list()


class IncomeExpenseDialog(QDialog):
    def __init__(self, controller, parent=None, initial_tab=0, user_role=None):
        super().__init__(parent)
        self.controller = controller
        self.user_role = user_role
        self.current_operator_name = (
            (getattr(parent, "operator_name", "") or getattr(parent, "username", "") or "").strip()
            if parent is not None else ""
        )
        self.setWindowTitle("收支管理作業")
        self.resize(1200, 800) # 加大視窗以容納左右分割
        self.setup_ui(initial_tab)

    def setup_ui(self, initial_tab):
        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # 收入頁面
        self.income_tab = TransactionTab(self.controller, "income", self, self.user_role, self.current_operator_name)
        self.tabs.addTab(self.income_tab, "收入資料登錄作業")

        # 支出頁面
        self.expense_tab = None
        if can_view_expense_entry(self.user_role):
            self.expense_tab = TransactionTab(self.controller, "expense", self, self.user_role, self.current_operator_name)
            self.tabs.addTab(self.expense_tab, "支出資料登錄作業")

        can_open_expense = self.expense_tab is not None
        target_idx = 1 if int(initial_tab or 0) == 1 and can_open_expense else 0
        self.tabs.setCurrentIndex(target_idx)
        
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

class PersonSearchDialog(QDialog):
    def __init__(self, controller, keyword="", parent=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_person = None

        self.setWindowTitle("信徒搜尋結果")
        self.resize(700, 420)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["姓名", "電話", "地址"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # ✅ 關鍵：強制可見的表格設定
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setMinimumHeight(260)
        self.table.setStyleSheet("""
            QTableWidget::item { 
                color: #2B2B2B; 
                background: #FFFFFF;   /* 固定未選取為白底 */
            }
            QTableWidget::item:selected { 
                background: #FFF3E3; 
                color: #2B2B2B; 
            }
        """)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("確定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(self.accept_selected)
        cancel_btn.clicked.connect(self.reject)
        self.table.cellDoubleClicked.connect(lambda r, c: self.accept_selected())

        self.load_data(keyword)

    def load_data(self, keyword):
        results = self.controller.search_people(keyword) or []

        if not results:
            QMessageBox.information(self, "查無資料", "找不到符合條件的信徒")
            self.table.setRowCount(0)
            self.table.clearContents()
            return

        # 不要用 clear()，用 clearContents
        self.table.setRowCount(0)
        self.table.clearContents()
        self.table.setRowCount(len(results))

        for i, d in enumerate(results):
            name = d.get("name") or ""
            phone = d.get("phone_mobile") or d.get("phone_home") or ""
            addr = d.get("address") or ""

            self.table.setItem(i, 0, QTableWidgetItem(str(name)))
            self.table.setItem(i, 1, QTableWidgetItem(str(phone)))
            self.table.setItem(i, 2, QTableWidgetItem(str(addr)))
            self.table.item(i, 0).setData(Qt.UserRole, d)

        self.table.selectRow(0)
        self.table.setCurrentCell(0, 0)
        self.table.setFocus()
        self.table.repaint()

    def accept_selected(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "請先選取一筆資料")
            return
        self.selected_person = self.table.item(r, 0).data(Qt.UserRole)
        self.accept()

class TransactionTab(QWidget):
    def __init__(self, controller, transaction_type, parent_dialog, user_role=None, current_operator_name=""):
        super().__init__()
        self.controller = controller
        self.t_type = transaction_type # "income" or "expense"
        self.parent_dialog = parent_dialog
        self.user_role = user_role
        self.current_operator_name = (current_operator_name or "").strip()
        
        # 用於暫存選擇的信徒 ID (僅 Income 用到)
        self.selected_person_id = None
        self.show_all_mode = False
        self.void_only_mode = False
        
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # --- 1. 頂部篩選工具列 (Filter Bar) ---
        filter_layout = QHBoxLayout()
        
        # 年份
        self.year_combo = QComboBox()
        style_combo_with_dividers(self.year_combo)
        current_year = QDate.currentDate().year()
        for y in range(2000, current_year + 6):
            self.year_combo.addItem(f"{y}年", y)
        self.year_combo.setCurrentText(f"{current_year}年")
        self.year_combo.currentIndexChanged.connect(self.on_period_changed)
        
        # 月份
        self.month_combo = QComboBox()
        style_combo_with_dividers(self.month_combo)
        for m in range(1, 13):
            self.month_combo.addItem(f"{m}月", m)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.currentIndexChanged.connect(self.on_period_changed)
        
        # 導航按鈕
        self.btn_prev = QPushButton("◀ 上個月")
        self.btn_curr = QPushButton("本月")
        self.btn_next = QPushButton("下個月 ▶")
        self.btn_all = QPushButton("全部")

        self.btn_prev.clicked.connect(lambda: self.change_month(-1))
        self.btn_curr.clicked.connect(self.set_current_month)
        self.btn_next.clicked.connect(lambda: self.change_month(1))
        self.btn_all.clicked.connect(self.show_all_records)

        # 明細搜尋 / 作廢篩選
        self.list_search_input = QLineEdit()
        self.list_search_input.setPlaceholderText("搜尋姓名/電話/單號")
        self.list_search_input.setClearButtonEnabled(True)
        self.list_search_input.returnPressed.connect(self.apply_list_search)
        self.btn_list_search = QPushButton("搜尋")
        self.btn_list_search.clicked.connect(self.apply_list_search)
        self.btn_list_clear = QPushButton("清除")
        self.btn_list_clear.clicked.connect(self.clear_list_search)
        self.btn_void_only = QPushButton("作廢單據")
        self.btn_void_only.setCheckable(True)
        self.btn_void_only.toggled.connect(self.toggle_void_only)
        
        # 排序
        # self.sort_combo = QComboBox()
        # self.sort_combo.addItems(["日期 (新->舊)", "日期 (舊->新)"])
        
        filter_layout.addWidget(QLabel("年份:"))
        filter_layout.addWidget(self.year_combo)
        filter_layout.addWidget(QLabel("月份:"))
        filter_layout.addWidget(self.month_combo)
        filter_layout.addWidget(self.btn_prev)
        filter_layout.addWidget(self.btn_curr)
        filter_layout.addWidget(self.btn_next)
        filter_layout.addWidget(self.btn_all)
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
        self.date_input.setCalendarPopup(False)
        self.date_input.setDisplayFormat("yyyy/MM/dd")
        self.date_input.setFixedWidth(140)
        self._apply_date_editable_state()
        
        # 收據號碼 (唯讀，自動產生)
        self.receipt_input = QLineEdit()
        self.receipt_input.setPlaceholderText("系統自動產生")
        self.receipt_input.setReadOnly(True) # 雖然唯讀，但存檔時後端會真正產生
        
        # 經手人
        self.handler_input = QLineEdit()
        if self.current_operator_name:
            self.handler_input.setText(self.current_operator_name)
        self._apply_handler_editable_state()
        
        # 項目 (Category)
        self.category_combo = CategoryComboBox()
        self.category_combo.setObjectName("categoryCombo")
        category_view = QListView(self.category_combo)
        category_view.setSpacing(0)
        category_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        category_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        category_view.setTextElideMode(Qt.ElideNone)
        self.category_combo.setMaxVisibleItems(12)
        self.category_combo.setView(category_view)
        style_combo_with_dividers(self.category_combo)
        
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
            search_btn.clicked.connect(self.open_person_search_dialog)
            self.search_input.returnPressed.connect(self.open_person_search_dialog)
            search_box.addWidget(self.search_input)
            search_box.addWidget(search_btn)
            
            left_layout.addWidget(QLabel("<b>信徒資料 (付款人)</b>"))
            left_layout.addLayout(search_box)
            
            # # 搜尋結果列表 (點選用)
            # self.search_result_list = QTableWidget()
            # self.search_result_list.setColumnCount(3)
            # self.search_result_list.setHorizontalHeaderLabels(["姓名", "電話", "地址"])
            # self.search_result_list.setMaximumHeight(180)
            # self.search_result_list.setSelectionBehavior(QTableWidget.SelectRows)
            # self.search_result_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            # self.search_result_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            # self.search_result_list.cellClicked.connect(self.on_person_selected)
            # left_layout.addWidget(self.search_result_list)
            
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
        save_print_btn = None
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

        # 明確操作列：避免只靠右鍵，操作不明顯
        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("搜尋:"))
        action_row.addWidget(self.list_search_input)
        action_row.addWidget(self.btn_list_search)
        action_row.addWidget(self.btn_list_clear)
        action_row.addWidget(self.btn_void_only)
        action_row.addStretch()

        self.btn_edit_row = QPushButton("修改資料")
        self.btn_del_row = QPushButton("刪除資料")
        self.btn_edit_row.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self.btn_del_row.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self.btn_edit_row.setStyleSheet(
            "QPushButton:disabled { color: #9E9E9E; background: #F3EFEA; border: 1px solid #E0D8CF; }"
        )
        self.btn_del_row.setStyleSheet(
            "QPushButton:disabled { color: #9E9E9E; background: #F3EFEA; border: 1px solid #E0D8CF; }"
        )
        self.btn_print_row = None
        self.btn_void_row = None
        if self.t_type == "income":
            self.btn_print_row = QPushButton("補印收據")
            self.btn_print_row.clicked.connect(self._print_selected_row)
            self.btn_void_row = QPushButton("作廢")
            self.btn_void_row.clicked.connect(self._void_selected_row)

        self.btn_edit_row.clicked.connect(self._edit_selected_row)
        self.btn_del_row.clicked.connect(self._delete_selected_row)

        self.table = QTableWidget()
        cols = ["日期", "單號", "項目", "對象", "金額", "經手人", "作廢", "類型", "摘要"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setWordWrap(False)
        self.table.setColumnWidth(0, 120)  # 日期
        self.table.setColumnWidth(1, 140)  # 單號
        self.table.setColumnWidth(2, 180)  # 項目
        self.table.setColumnWidth(3, 180)  # 對象
        self.table.setColumnWidth(4, 110)  # 金額
        self.table.setColumnWidth(5, 120)  # 經手人
        self.table.setColumnWidth(6, 70)   # 作廢
        self.table.setColumnWidth(7, 100)  # 類型
        self.table.setColumnWidth(8, 320)  # 摘要
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            """
            QTableWidget::item:selected {
                background: #D9ECFF;
                color: #1F2937;
                border: 1px solid #8CB8E8;
            }
            """
        )
        
        # 右鍵選單
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self._sync_row_action_buttons)

        # 表格下方操作列
        bottom_action_row = QHBoxLayout()
        bottom_action_row.addStretch()
        if self.btn_print_row is not None:
            bottom_action_row.addWidget(self.btn_print_row)
        if self.btn_void_row is not None:
            bottom_action_row.addWidget(self.btn_void_row)
        bottom_action_row.addWidget(self.btn_edit_row)
        bottom_action_row.addWidget(self.btn_del_row)
        
        right_layout.addWidget(list_label)
        right_layout.addLayout(action_row)
        right_layout.addWidget(self.table)
        right_layout.addLayout(bottom_action_row)
        right_widget.setLayout(right_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 2) # 右邊寬一點
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        self.editing_transaction_id = None
        self.editing_source_date = None
        self.selected_person_data = None
        self.save_btn = save_btn # 存引用以便改文字
        self.save_print_btn = save_print_btn
        
        # 增加取消編輯按鈕 (預設隱藏)
        self.cancel_edit_btn = QPushButton("❌ 取消編輯")
        self.cancel_edit_btn.setVisible(False)
        self.cancel_edit_btn.clicked.connect(self.cancel_edit)
        btn_box.insertWidget(0, self.cancel_edit_btn)
        self._apply_role_scope_permissions()
        self._sync_row_action_buttons()

    def _is_income_limited_scope(self):
        return self.t_type == "income" and (not can_view_income_all_dates(self.user_role))

    def _has_income_row_write_permission(self):
        # 收入頁：僅管理員與會計可修改/刪除資料
        if self.t_type != "income":
            return True
        return can_view_income_all_dates(self.user_role)

    def _apply_role_scope_permissions(self):
        if not self._is_income_limited_scope():
            # 收入編修權限 tooltip 仍需套用
            if not self._has_income_row_write_permission():
                self.btn_edit_row.setEnabled(False)
                self.btn_del_row.setEnabled(False)
                self.btn_edit_row.setToolTip("僅管理員與會計可修改收入資料。")
                self.btn_del_row.setToolTip("僅管理員與會計可刪除收入資料。")
            else:
                self.btn_edit_row.setToolTip("")
                self.btn_del_row.setToolTip("")
            return
        self.btn_all.setEnabled(False)
        self.btn_all.setToolTip("工作人員僅可檢視上個月1日至今日收入。")
        self.year_combo.setEnabled(False)
        self.month_combo.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_curr.setEnabled(False)
        self.btn_next.setEnabled(False)
        if not self._has_income_row_write_permission():
            self.btn_edit_row.setEnabled(False)
            self.btn_del_row.setEnabled(False)
            self.btn_edit_row.setToolTip("僅管理員與會計可修改收入資料。")
            self.btn_del_row.setToolTip("僅管理員與會計可刪除收入資料。")
        else:
            self.btn_edit_row.setToolTip("")
            self.btn_del_row.setToolTip("")
    
    def open_person_search_dialog(self):
        kw = self.search_input.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "請輸入搜尋關鍵字")
            return

        # 先查一次，避免查無資料時還彈出空白搜尋視窗
        results = self.controller.search_people(kw) or []
        if not results:
            QMessageBox.information(self, "查無資料", "找不到符合條件的信徒")
            return

        dialog = PersonSearchDialog(self.controller, kw, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_person:
            self.set_person(dialog.selected_person)

    def load_initial_data(self):
        self._reload_category_items(keep_selection=False)
        # 載入列表
        self.refresh_list()

    def _reload_category_items(self, keep_selection: bool = True):
        selected_id = ""
        if keep_selection:
            current = self.category_combo.currentData()
            if isinstance(current, dict):
                selected_id = str(current.get("id") or "").strip()

        # 載入項目
        if self.t_type == "income":
            items = self.controller.get_all_income_items()
        else:
            items = self.controller.get_all_expense_items()

        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        target_idx = -1
        for item in items:
            self.category_combo.addItem(f"{item['id']} - {item['name']}", item) # userData 存整包
            if selected_id and str(item.get("id") or "").strip() == selected_id:
                target_idx = self.category_combo.count() - 1

        if self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(target_idx if target_idx >= 0 else 0)
        self.category_combo.blockSignals(False)

    def perform_search(self):
        # 相容舊呼叫點：改為走目前的彈窗搜尋流程（不再使用已移除的 search_result_list）
        self.open_person_search_dialog()

    def on_person_selected(self, row, col):
        # 舊版 inline 搜尋表格已移除，保留防呆避免舊訊號誤連接時報錯。
        if not hasattr(self, "search_result_list"):
            return
        item = self.search_result_list.item(row, 0)
        if not item:
            return
        person_data = item.data(Qt.UserRole)
        if person_data:
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
        self.show_all_mode = False
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
        self.show_all_mode = False
        today = QDate.currentDate()
        self.year_combo.setCurrentText(f"{today.year()}年")
        self.month_combo.setCurrentIndex(today.month() - 1)
        # 若原本就已是本月，上面兩行可能不觸發 currentIndexChanged；
        # 仍需強制刷新，確保新交易能即時顯示
        self.refresh_list()

    def on_period_changed(self):
        self.show_all_mode = False
        self.refresh_list()

    def show_all_records(self):
        if self._is_income_limited_scope():
            QMessageBox.information(self, "限制", "工作人員僅可檢視上個月1日至今日收入。")
            self.show_all_mode = False
            self.refresh_list()
            return
        self.show_all_mode = True
        self.refresh_list()

    def apply_list_search(self):
        self.refresh_list()

    def clear_list_search(self):
        self.list_search_input.clear()
        self.refresh_list()

    def toggle_void_only(self, checked):
        self.void_only_mode = bool(checked)
        self.btn_void_only.setText("顯示全部" if checked else "作廢單據")
        self.refresh_list()

    def refresh_list(self):
        self._reload_category_items(keep_selection=True)
        keyword = self.list_search_input.text().strip() if hasattr(self, "list_search_input") else None
        if self._is_income_limited_scope():
            curr = QDate.currentDate()
            prev = curr.addMonths(-1)
            start_date = f"{prev.year()}-{prev.month():02d}-01"
            end_date = f"{curr.year()}-{curr.month():02d}-{curr.day():02d}"
            rows = self.controller.get_transactions(
                self.t_type,
                start_date=None,
                end_date=None,
                keyword=keyword,
                voided_filter="only" if self.void_only_mode else "all",
            )
            start_dt = date(prev.year(), prev.month(), 1)
            end_dt = date(curr.year(), curr.month(), curr.day())
            data = []
            for row in rows:
                tx_date = self._to_date_obj((row or {}).get("date", ""))
                if tx_date and start_dt <= tx_date <= end_dt:
                    data.append(row)
        elif self.void_only_mode:
            data = self.controller.get_transactions(
                self.t_type,
                start_date=None,
                end_date=None,
                keyword=keyword,
                voided_filter="only",
            )
        elif self.show_all_mode:
            data = self.controller.get_transactions(
                self.t_type,
                start_date=None,
                end_date=None,
                keyword=keyword,
            )
        else:
            year = self.year_combo.currentData()
            month = self.month_combo.currentData()
            
            start_date = f"{year}-{month:02d}-01"
            try:
               import calendar
               last_day = calendar.monthrange(year, month)[1]
               end_date = f"{year}-{month:02d}-{last_day}"
            except:
                 end_date =  f"{year}-{month:02d}-31"

            data = self.controller.get_transactions(
                self.t_type,
                start_date,
                end_date,
                keyword=keyword,
            )
        
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(self._format_ui_date(row['date'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['receipt_number']))
            self.table.setItem(i, 2, QTableWidgetItem(f"{row['category_name']}"))
            self.table.setItem(i, 3, QTableWidgetItem(row['payer_name']))
            self.table.setItem(i, 4, QTableWidgetItem(str(row['amount'])))
            self.table.setItem(i, 5, QTableWidgetItem(row['handler']))
            self.table.setItem(i, 6, QTableWidgetItem("作廢" if int((row or {}).get("is_voided") or 0) == 1 else ""))
            self.table.setItem(i, 7, QTableWidgetItem(self._format_adjustment_kind_label(row)))
            self.table.setItem(i, 8, QTableWidgetItem(row['note']))
            
            # 將整筆資料存入第一欄的 UserRole，供修改/刪除/列印使用
            self.table.item(i, 0).setData(Qt.UserRole, row)
            self._apply_source_group_row_style(i, row)
        self._sync_row_action_buttons()

    def _format_adjustment_kind_label(self, row_data):
        source_type = str((row_data or {}).get("source_type") or "").strip().upper()
        kind = str((row_data or {}).get("adjustment_kind") or "").strip().upper()
        # 類型欄位對齊業務頁語意（初始 / 追加）。
        # REFUND 由「作廢」欄位表達，不在類型欄顯示。
        if source_type in {"LIGHTING_SIGNUP", "ACTIVITY_SIGNUP"}:
            if kind == "PRIMARY":
                return "初始"
            if kind == "SUPPLEMENT":
                return "追加"
            return ""
        mapping = {
            "PRIMARY": "初始",
            "SUPPLEMENT": "追加",
        }
        return mapping.get(kind, "")

    def _adjustment_kind_sort_priority(self, row_data):
        kind = str((row_data or {}).get("adjustment_kind") or "").strip().upper()
        return {"PRIMARY": 0, "SUPPLEMENT": 1, "REFUND": 2}.get(kind, 9)

    def _source_group_key(self, row_data):
        stype = str((row_data or {}).get("source_type") or "").strip()
        sid = str((row_data or {}).get("source_id") or "").strip()
        if not stype or not sid:
            return ""
        return f"{stype}:{sid}"

    def _group_rows_by_source_for_display(self, rows):
        src_rows = list(rows or [])
        if not src_rows:
            return src_rows

        first_pos_by_group = {}
        for idx, row in enumerate(src_rows):
            key = self._source_group_key(row)
            if key and key not in first_pos_by_group:
                first_pos_by_group[key] = idx

        indexed_rows = list(enumerate(src_rows))

        def _sort_key(pair):
            idx, row = pair
            key = self._source_group_key(row)
            if not key:
                return (idx, 1, 0, idx)
            return (
                first_pos_by_group.get(key, idx),
                0,
                self._adjustment_kind_sort_priority(row),
                idx,
            )

        indexed_rows.sort(key=_sort_key)
        return [row for _, row in indexed_rows]

    def _source_group_color(self, row_data):
        """
        同來源（source_type + source_id）套用同一淡底色，提升主收款/補繳/退費關聯可讀性。
        """
        key = self._source_group_key(row_data)
        if not key:
            return None
        # 只使用兩種底色：白色 + 主題色
        palette = [
            "#FFFFFF",
            "#FFF3E3",
        ]
        if not hasattr(self, "_source_group_color_cache"):
            self._source_group_color_cache = {}
            self._source_group_color_next_idx = 0
        if key not in self._source_group_color_cache:
            idx = int(getattr(self, "_source_group_color_next_idx", 0)) % len(palette)
            self._source_group_color_cache[key] = palette[idx]
            self._source_group_color_next_idx = int(getattr(self, "_source_group_color_next_idx", 0)) + 1
        return QColor(self._source_group_color_cache[key])

    def _apply_source_group_row_style(self, row_idx: int, row_data):
        # 收支頁以時間排序為主，底色僅做逐列交錯輔助（白色 / 主題色）
        palette = ["#FFFFFF", "#FFF3E3"]
        color = QColor(palette[row_idx % len(palette)])
        for c in range(self.table.columnCount()):
            item = self.table.item(row_idx, c)
            if item:
                item.setBackground(color)

    def _get_selected_row_data(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _can_edit_any_date(self):
        return can_edit_any_date(self.user_role)

    def _apply_date_editable_state(self):
        if not hasattr(self, "date_input"):
            return
        editable = self._can_edit_any_date()
        self.date_input.setReadOnly(not editable)
        self.date_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.date_input.lineEdit().setReadOnly(not editable)
        self.date_input.setFocusPolicy(Qt.StrongFocus if editable else Qt.NoFocus)
        if editable:
            self.date_input.setToolTip("")
        else:
            self.date_input.setToolTip("僅管理員與會計可修改日期")

    def _can_edit_handler(self):
        return can_edit_handler(self.user_role)

    def _apply_handler_editable_state(self):
        if not hasattr(self, "handler_input"):
            return
        editable = self._can_edit_handler()
        self.handler_input.setReadOnly(not editable)
        if editable:
            self.handler_input.setToolTip("")
        else:
            self.handler_input.setToolTip("僅管理員與會計可修改經手人")

    def _is_editable_today(self, data):
        if not data:
            return False
        if self._can_edit_any_date():
            return True
        tx_date = self._to_date_obj(data.get("date", ""))
        return bool(tx_date and tx_date == date.today())

    def _can_delete_data(self, data):
        if not data:
            return False
        if self._can_edit_any_date():
            return True
        tx_date = self._to_date_obj(data.get("date", ""))
        return bool(tx_date and tx_date == date.today())

    def _is_system_business_income_txn(self, data):
        """
        Phase 1 止血：
        - 90 活動收入
        - 91 安燈收入（點燈收入）
        這兩類交易應回原業務頁處理，不允許在收支頁直接修改/刪除。
        """
        if self.t_type != "income" or not data:
            return False
        cid = str((data or {}).get("category_id") or "").strip()
        return cid in {"90", "91"}

    def _can_direct_edit_data(self, data):
        if not data:
            return False
        if int((data or {}).get("is_voided") or 0) == 1:
            return False
        if not self._has_income_row_write_permission():
            return False
        if self._is_system_business_income_txn(data):
            return False
        return self._is_editable_today(data)

    def _can_direct_delete_data(self, data):
        if not data:
            return False
        if int((data or {}).get("is_voided") or 0) == 1:
            return False
        if not self._has_income_row_write_permission():
            return False
        if self._is_system_business_income_txn(data):
            return False
        return self._can_delete_data(data)

    def _can_void_data(self, data):
        if self.t_type != "income" or not data:
            return False
        if self._is_system_business_income_txn(data):
            return False
        if int((data or {}).get("is_voided") or 0) == 1:
            return False
        return True

    def _show_system_income_lock_message(self):
        QMessageBox.information(
            self,
            "限制",
            "90活動收入 / 91安燈收入為系統保留業務交易，請回原業務頁（活動/安燈）處理。",
        )

    def _sync_row_action_buttons(self):
        data = self._get_selected_row_data()
        has_row = data is not None
        if self.btn_void_row is not None:
            self.btn_void_row.setEnabled(has_row and self._can_void_data(data))
            if has_row and self._is_system_business_income_txn(data):
                self.btn_void_row.setToolTip("90/91 收入請回活動或安燈頁處理作廢。")
            elif has_row and int((data or {}).get("is_voided") or 0) == 1:
                self.btn_void_row.setToolTip("此單據已作廢。")
            else:
                self.btn_void_row.setToolTip("")
        if not self._has_income_row_write_permission():
            self.btn_edit_row.setEnabled(False)
            self.btn_del_row.setEnabled(False)
            self.btn_edit_row.setToolTip("僅管理員與會計可修改收入資料。")
            self.btn_del_row.setToolTip("僅管理員與會計可刪除收入資料。")
        else:
            self.btn_edit_row.setEnabled(has_row and self._can_direct_edit_data(data))
            self.btn_del_row.setEnabled(has_row and self._can_direct_delete_data(data))
            self.btn_edit_row.setToolTip("")
            self.btn_del_row.setToolTip("")
        if self.btn_print_row is not None:
            self.btn_print_row.setEnabled(has_row)

    def _edit_selected_row(self):
        data = self._get_selected_row_data()
        if data and int((data or {}).get("is_voided") or 0) == 1:
            QMessageBox.information(self, "限制", "作廢單據不可修改。")
            return
        if not self._has_income_row_write_permission():
            QMessageBox.warning(self, "權限不足", "目前角色無權限修改收入資料。")
            return
        data = self._get_selected_row_data()
        if not data:
            QMessageBox.warning(self, "提示", "請先選取一筆資料")
            return
        if self._is_system_business_income_txn(data):
            self._show_system_income_lock_message()
            return
        if not self._is_editable_today(data):
            QMessageBox.information(self, "限制", "交易資料修改僅限當日資料。")
            return
        self.load_transaction_to_form(data)

    def _delete_selected_row(self):
        data = self._get_selected_row_data()
        if data and int((data or {}).get("is_voided") or 0) == 1:
            QMessageBox.information(self, "限制", "作廢單據不可刪除。")
            return
        if not self._has_income_row_write_permission():
            QMessageBox.warning(self, "權限不足", "目前角色無權限刪除收入資料。")
            return
        data = self._get_selected_row_data()
        if not data:
            QMessageBox.warning(self, "提示", "請先選取一筆資料")
            return
        if self._is_system_business_income_txn(data):
            self._show_system_income_lock_message()
            return
        if not self._can_delete_data(data):
            QMessageBox.information(self, "限制", "交易資料刪除僅限當日資料。")
            return
        self.delete_transaction(data)

    def _print_selected_row(self):
        data = self._get_selected_row_data()
        if not data:
            QMessageBox.warning(self, "提示", "請先選取一筆資料")
            return
        self.on_print_receipt(data)

    def _void_selected_row(self):
        data = self._get_selected_row_data()
        if not data:
            QMessageBox.warning(self, "提示", "請先選取一筆資料")
            return
        if self._is_system_business_income_txn(data):
            self._show_system_income_lock_message()
            return
        if int((data or {}).get("is_voided") or 0) == 1:
            QMessageBox.information(self, "提示", "此單據已作廢。")
            return

        reply = QMessageBox.question(
            self,
            "確認作廢",
            f"確定要作廢這筆收入資料嗎？\n單號：{data.get('receipt_number','')}\n金額：{data.get('amount','')}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.controller.void_transaction(data["id"])
            QMessageBox.information(self, "完成", "單據已作廢。")
            self.refresh_list()
            if self.editing_transaction_id == data.get("id"):
                self.cancel_edit()
        except Exception as e:
            QMessageBox.warning(self, "作廢失敗", str(e))

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        self.table.selectRow(row)
        data = self.table.item(row, 0).data(Qt.UserRole)
        if not data:
            return

        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        # 右鍵選單專用樣式：提高對比，避免字色與背景撞色看不清
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #D6CFC6;
                padding: 6px;
            }
            QMenu::item {
                color: #1F2937;
                padding: 8px 14px;
                border-radius: 6px;
                margin: 2px 0;
            }
            QMenu::item:selected {
                background: #FFF3E3;
                color: #111827;
            }
            QMenu::separator {
                height: 1px;
                background: #E6D8C7;
                margin: 6px 4px;
            }
        """)
        
        if self.t_type == "income":
            print_action = QAction("補印收據", self)
            print_action.triggered.connect(lambda: self.on_print_receipt(data))
            menu.addAction(print_action)

            void_action = QAction("作廢單據", self)
            void_action.triggered.connect(lambda: self._void_selected_row())
            void_action.setEnabled(self._can_void_data(data))
            menu.addAction(void_action)
            menu.addSeparator()

        edit_action = QAction("修改資料", self)
        edit_action.triggered.connect(lambda: self.load_transaction_to_form(data))
        edit_action.setEnabled(self._can_direct_edit_data(data))
        menu.addAction(edit_action)
        menu.addSeparator()
        
        del_action = QAction("刪除資料", self)
        del_action.triggered.connect(lambda: self.delete_transaction(data))
        del_action.setEnabled(self._can_direct_delete_data(data))
        menu.addAction(del_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def on_print_receipt(self, data):
        PrintHelper.print_receipt(data)

    def delete_transaction(self, data):
        if int((data or {}).get("is_voided") or 0) == 1:
            QMessageBox.warning(self, "限制", "作廢單據不可刪除。")
            return
        if not self._has_income_row_write_permission():
            QMessageBox.warning(self, "權限不足", "目前角色無權限刪除收入資料。")
            return
        if self._is_system_business_income_txn(data):
            self._show_system_income_lock_message()
            return
        if not self._can_delete_data(data):
            QMessageBox.warning(self, "限制", "交易資料刪除僅限當日資料。")
            return
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
        if int((data or {}).get("is_voided") or 0) == 1:
            QMessageBox.warning(self, "限制", "作廢單據不可修改。")
            return
        if not self._has_income_row_write_permission():
            QMessageBox.warning(self, "權限不足", "目前角色無權限修改收入資料。")
            return
        if self._is_system_business_income_txn(data):
            self._show_system_income_lock_message()
            return
        if not self._is_editable_today(data):
            QMessageBox.information(self, "限制", "交易資料修改僅限當日資料。")
            return
        self.editing_transaction_id = data['id']
        self.editing_source_date = str(data.get('date', '')).strip()
        
        # 填入表單
        qd = self._to_qdate(data.get("date", ""))
        if qd is None:
            qd = QDate.currentDate()
        self.date_input.setDate(qd)
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
        self.editing_source_date = None
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

    def _clear_after_new_save(self):
        """
        新增成功後清空輸入欄位，避免連續登錄時誤用上一筆資料。
        """
        self.amount_input.clear()
        self.note_input.clear()
        self.receipt_input.setText("")
        self.receipt_input.setPlaceholderText("系統自動產生")
        # 同步清空搜尋欄，避免殘留上一筆搜尋條件
        if hasattr(self, "list_search_input"):
            self.list_search_input.clear()
        if self.t_type == "income" and hasattr(self, "search_input"):
            self.search_input.clear()

        if self.t_type == "income":
            self.selected_person_id = None
            self.selected_person_data = None
            self.payer_name_display.clear()
            self.payer_phone_display.clear()
        else:
            self.payee_input.clear()

    def save_data(self, print_receipt):
        # 1. 蒐集資料
        date_str = qdate_to_db_ymd(self.date_input.date())
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
                if not self._has_income_row_write_permission():
                    QMessageBox.warning(self, "權限不足", "目前角色無權限修改收入資料。")
                    self.cancel_edit()
                    return
                # 只允許修改原始日期為今日的交易
                src_day = self._to_date_obj(self.editing_source_date)
                if (not self._can_edit_any_date()) and (src_day != date.today()):
                    QMessageBox.warning(self, "限制", "交易資料修改僅限當日資料。")
                    self.cancel_edit()
                    return

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

                # 編輯模式若按「存檔並列印」，收入也要補印
                if print_receipt and self.t_type == "income":
                    payer_address = ""
                    if self.selected_person_data:
                        payer_address = self.selected_person_data.get("address", "") or ""

                    print_payload = {
                        **payload,
                        "type": "income",
                        "receipt_number": self.receipt_input.text().strip(),
                        "address": payer_address,
                    }
                    PrintHelper.print_receipt(print_payload)

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
                
                self._clear_after_new_save()
            
            # 刷新列表
            self.refresh_list()
            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"作業失敗: {str(e)}")

    @staticmethod
    def _to_qdate(raw):
        return parse_qdate_flexible(raw)

    @classmethod
    def _to_date_obj(cls, raw):
        qd = cls._to_qdate(raw)
        if qd is None:
            return None
        return date(qd.year(), qd.month(), qd.day())

    @classmethod
    def _format_ui_date(cls, raw):
        return to_ui_ymd_text(raw)
