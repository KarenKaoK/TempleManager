from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import re

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame, QFormLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QSizePolicy, QGroupBox, QDialog, QCheckBox
)
from PyQt5.QtWidgets import QMessageBox, QTextEdit
from app.utils.id_utils import compute_display_status
from app.utils.date_utils import (
    is_valid_ymd_text,
    make_ymd_validator,
    normalize_ymd_text,
)
from app.utils.print_helper import PrintHelper
from app.dialogs.activity_edit_dialog import ActivityEditDialog
from app.dialogs.plan_edit_dialog import PlanEditDialog


# -----------------------------
# Mock Models（之後你可換成 controller / DB 的資料結構）
# -----------------------------
@dataclass
class PlanRow:
    id: str
    name: str
    items: str
    fee_type: str  # fixed / donation / other
    amount: Optional[int]  # fixed 才有


@dataclass
class SignupItemRow:
    plan_id: str
    plan_name: str
    qty: int
    unit_price: int
    subtotal: int
    is_donation: bool = False


@dataclass
class SignupRow:
    id: str
    name: str
    phone: str
    address: str
    items: List[SignupItemRow]


class WenshuPrintDialog(QDialog):
    def __init__(self, rows: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("文疏列印")
        self.resize(980, 620)
        self._rows = list(rows or [])
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        self.chk_activity_birthday_format = QPushButton("☐ 活動祝壽格式")
        self.chk_activity_birthday_format.setCheckable(True)
        self.chk_activity_birthday_format.toggled.connect(
            lambda on: self.chk_activity_birthday_format.setText("☑ 活動祝壽格式" if on else "☐ 活動祝壽格式")
        )
        self.edt_prayer_default = QLineEdit()
        self.edt_prayer_default.setPlaceholderText("預設祈求（可留空）")
        self.edt_prayer_default.setText("")
        self.chk_apply_default_prayer = QCheckBox("套用預設祈求")
        self.chk_apply_default_prayer.setChecked(False)
        btn_all = QPushButton("全選")
        btn_none = QPushButton("清空")

        self.chk_apply_default_prayer.toggled.connect(self._on_toggle_apply_default_prayer)
        btn_all.clicked.connect(lambda: self._set_all_checked(True))
        btn_none.clicked.connect(lambda: self._set_all_checked(False))
        top.addWidget(self.chk_activity_birthday_format)
        top.addWidget(QLabel("預設祈求"))
        top.addWidget(self.edt_prayer_default, 1)
        top.addWidget(self.chk_apply_default_prayer)
        top.addWidget(btn_all)
        top.addWidget(btn_none)
        root.addLayout(top)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["列印", "姓名", "生日", "地址", "祈求"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tbl.setAlternatingRowColors(True)
        root.addWidget(self.tbl, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_print = QPushButton("列印文疏（單筆/批次）")
        btn_close = QPushButton("關閉")
        btn_print.clicked.connect(self._on_print)
        btn_close.clicked.connect(self.reject)
        bottom.addWidget(btn_print)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        self._render_rows()

    def _render_rows(self):
        self.tbl.setRowCount(0)
        for r in self._rows:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            chk = QTableWidgetItem("")
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Unchecked)
            self.tbl.setItem(row, 0, chk)
            self.tbl.setItem(row, 1, QTableWidgetItem(str(r.get("person_name", ""))))
            lunar = normalize_ymd_text(str(r.get("person_birthday_lunar", "") or ""))
            ad = normalize_ymd_text(str(r.get("person_birthday_ad", "") or ""))
            is_leap = int(r.get("person_lunar_is_leap") or 0) == 1
            if lunar:
                if is_leap:
                    birthday_text = f"農曆 {lunar}(閏)"
                else:
                    birthday_text = f"農曆 {lunar}"
            elif ad:
                birthday_text = f"國曆 {ad}"
            else:
                birthday_text = ""
            self.tbl.setItem(row, 2, QTableWidgetItem(birthday_text))
            name_item = self.tbl.item(row, 1)
            birthday_item = self.tbl.item(row, 2)
            address_item = QTableWidgetItem(str(r.get("person_address", "")))
            self.tbl.setItem(row, 3, address_item)
            prayer_item = QTableWidgetItem("")
            self.tbl.setItem(row, 4, prayer_item)

            # 姓名/生日/地址為唯讀；祈求欄可手動編輯
            for readonly_item in (name_item, birthday_item, address_item):
                if readonly_item:
                    readonly_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            prayer_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)

    def _set_all_checked(self, checked: bool):
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 0)
            if it:
                it.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _on_toggle_apply_default_prayer(self, checked: bool):
        if not checked:
            return
        default_prayer = (self.edt_prayer_default.text() or "").strip()
        if not default_prayer:
            return
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 4)
            if it is None:
                it = QTableWidgetItem("")
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                self.tbl.setItem(r, 4, it)
            it.setText(default_prayer)

    def _on_print(self):
        default_prayer = (self.edt_prayer_default.text() or "").strip()
        use_default_prayer = self.chk_apply_default_prayer.isChecked()
        rows = []
        for r in range(self.tbl.rowCount()):
            chk = self.tbl.item(r, 0)
            if not chk or chk.checkState() != Qt.Checked:
                continue
            name = self.tbl.item(r, 1).text() if self.tbl.item(r, 1) else ""
            birthday = self.tbl.item(r, 2).text() if self.tbl.item(r, 2) else ""
            address = self.tbl.item(r, 3).text() if self.tbl.item(r, 3) else ""
            row_prayer = self.tbl.item(r, 4).text().strip() if self.tbl.item(r, 4) else ""
            rows.append({
                "name": name,
                "birthday": birthday,
                "address": address,
                "prayer": row_prayer if row_prayer else (default_prayer if use_default_prayer else ""),
            })
        if not rows:
            QMessageBox.information(self, "請先選擇", "請先勾選至少一位報名者再列印文疏")
            return
        template = "activity_birthday" if self.chk_activity_birthday_format.isChecked() else "blessing"
        PrintHelper.print_wenshu_report(rows, template=template)


class ItemStatsDialog(QDialog):
    def __init__(self, rows: List[Tuple[str, int]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("總品項列印")
        self.resize(760, 560)
        self._rows = list(rows or [])
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels(["品項", "總數量"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        root.addWidget(self.tbl, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_print = QPushButton("列印統計")
        btn_close = QPushButton("關閉")
        btn_print.clicked.connect(self._on_print)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_print)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

        self._render()

    def _render(self):
        self.tbl.setRowCount(0)
        for item_name, qty in self._rows:
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(item_name)))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(int(qty))))

    def _on_print(self):
        rows = [[k, str(v)] for k, v in (self._rows or [])]
        if not rows:
            QMessageBox.information(self, "列印統計", "沒有可列印內容")
            return
        PrintHelper.print_table_report("總品項列印", ["品項", "總數量"], rows)


# -----------------------------
# Panel 
# -----------------------------
class ActivityDetailPanel(QWidget):
    request_back = pyqtSignal()
    activity_saved = pyqtSignal(str)
    activity_deleted = pyqtSignal(str)


    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._current_activity_id: Optional[str] = None

        self._plans: List[PlanRow] = []
        self._signups: List[SignupRow] = []

        self._current_activity_id = None
        self._default_payment_handler = ""
        self._current_user_role = ""

        self._build_ui()
        

    # -----------------------------
    # UI
    # -----------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Header（標題 + meta + 活動操作按鈕） =====
        header = QFrame()
        header.setObjectName("activityHeader")
        header.setFrameShape(QFrame.NoFrame)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(10)

        # ✅ 中間撐開，右側按鈕自然靠右
        header_layout.addStretch(1)

        # 右側：操作按鈕
        self.btn_new = QPushButton("+ 新增活動")
        self.btn_edit = QPushButton("修改活動")
        self.btn_del = QPushButton("刪除活動")

        self.btn_new.clicked.connect(self.on_new_activity)
        self.btn_edit.clicked.connect(self.on_edit_activity)
        self.btn_del.clicked.connect(self.on_delete_activity)

        for b in (self.btn_new, self.btn_edit, self.btn_del):
            b.setMinimumHeight(34)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.addWidget(self.btn_new)
        btn_box.addWidget(self.btn_edit)
        btn_box.addWidget(self.btn_del)

        # ✅ PyQt5：addLayout 只能 (layout, stretch)；不要再加 AlignRight
        header_layout.addLayout(btn_box)

        root.addWidget(header)


        # ===== Tabs =====
        self.tabs = QTabWidget()
        self.tabs.setObjectName("activityTabs")
        root.addWidget(self.tabs, 1)

        # Tab 1：新增活動 / 方案
        self.tab_manage = QWidget()
        self.tabs.addTab(self.tab_manage, "① 新增活動 / 方案")
        self._build_tab_manage()

        # Tab 2：報名統計與列印
        self.tab_signup = QWidget()
        self.tabs.addTab(self.tab_signup, "② 報名統計與列印")
        self._build_tab_signup()


        # （可選）簡單 QSS，讓整體更接近 HTML 的暖色系
        self._apply_qss()

    def _build_tab_manage(self):
        layout = QHBoxLayout(self.tab_manage)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 左：活動資料表單
        left = QGroupBox("活動資料")
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lf = QVBoxLayout(left)
        lf.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.f_name = QLineEdit()
        self.f_start = QLineEdit()
        self.f_end = QLineEdit()
        ymd_validator = make_ymd_validator(self)
        self.f_start.setValidator(ymd_validator)
        self.f_end.setValidator(ymd_validator)
        self.f_start.setPlaceholderText("YYYY/MM/DD")
        self.f_end.setPlaceholderText("YYYY/MM/DD")
        self.f_note = QTextEdit()
        self.f_note.setMinimumHeight(120)
        self.f_note.setMaximumHeight(180)
        self.f_note.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 活動資料頁僅供檢視，修改請使用「修改活動」按鈕開啟 dialog
        self.f_name.setReadOnly(True)
        self.f_start.setReadOnly(True)
        self.f_end.setReadOnly(True)
        self.f_note.setReadOnly(True)


        form.addRow("活動名稱", self.f_name)


        date_row = QWidget()
        date_row_l = QHBoxLayout(date_row)
        date_row_l.setContentsMargins(0, 0, 0, 0)
        date_row_l.setSpacing(8)
        date_row_l.addWidget(self.f_start)
        date_row_l.addWidget(QLabel("～"))
        date_row_l.addWidget(self.f_end)

        form.addRow("國曆日期", date_row)
        form.addRow("備註", self.f_note)

        lf.addLayout(form, 0)
        lf.addStretch(1)

        # 右：方案列表 + 方案操作
        right = QGroupBox("方案列表")
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rf = QVBoxLayout(right)
        rf.setContentsMargins(12, 12, 12, 12)
        rf.setSpacing(10)

        plan_btn_row = QHBoxLayout()
        plan_btn_row.setSpacing(8)

        self.btn_plan_new = QPushButton("+ 新增方案")
        self.btn_plan_edit = QPushButton("修改方案")
        self.btn_plan_del = QPushButton("刪除方案")
        for b in (self.btn_plan_new, self.btn_plan_edit, self.btn_plan_del):
            b.setMinimumHeight(32)

        self.btn_plan_new.clicked.connect(self.on_new_plan)
        self.btn_plan_edit.clicked.connect(self.on_edit_plan)
        self.btn_plan_del.clicked.connect(self.on_delete_plan)

        plan_btn_row.addWidget(self.btn_plan_new)
        plan_btn_row.addWidget(self.btn_plan_edit)
        plan_btn_row.addWidget(self.btn_plan_del)
        plan_btn_row.addStretch(1)
        rf.addLayout(plan_btn_row)

        self.tbl_plans = QTableWidget(0, 4)
        self.tbl_plans.setHorizontalHeaderLabels(["方案名稱", "方案項目", "費用方式", "金額"])
        self.tbl_plans.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setStretchLastSection(False)
        self.tbl_plans.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_plans.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_plans.setAlternatingRowColors(True)
        self.tbl_plans.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tbl_plans.setTextElideMode(Qt.ElideNone)

        rf.addWidget(self.tbl_plans, 1)


        layout.addWidget(left, 4)
        layout.addWidget(right, 6)

    def _build_tab_signup(self):
        layout = QVBoxLayout(self.tab_signup)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        self._signup_filter_mode = "all"
        self._signup_rows = []
        self._signup_rows_filtered = []

        # 統計卡片（3格）
        stats = QGridLayout()
        stats.setHorizontalSpacing(10)
        stats.setVerticalSpacing(10)

        # ⚠️ 你之前有把報名人數設 emph=True 會變橘色
        # 這裡統一用一般 statCard，避免「突兀」的高亮
        self.stat_signup_cnt = self._make_stat_card("報名人數", "0")
        self.stat_total = self._make_stat_card("預估總收入", "0")
        self.stat_donation = self._make_stat_card("其中隨喜", "0")

        stats.addWidget(self.stat_signup_cnt, 0, 0)
        stats.addWidget(self.stat_total, 0, 1)
        stats.addWidget(self.stat_donation, 0, 2)

        layout.addLayout(stats)

        # 區塊 1：報名名單（明細）
        grp_detail = QGroupBox("報名名單（明細）")
        g1 = QVBoxLayout(grp_detail)
        g1.setContentsMargins(12, 12, 12, 12)
        g1.setSpacing(8)

        search_row = QHBoxLayout()
        self.edt_signup_search = QLineEdit()
        self.edt_signup_search.setPlaceholderText("搜尋姓名 / 電話")
        self.edt_signup_search.setMaximumWidth(280)
        self.btn_show_all_signups = QPushButton("全部")
        self.btn_show_unpaid_signups = QPushButton("篩選未繳費")
        self.btn_clear_signup_search = QPushButton("清空")
        self.edt_signup_search.textChanged.connect(self._on_signup_search_changed)
        self.btn_show_all_signups.clicked.connect(self._on_show_all_signups)
        self.btn_show_unpaid_signups.clicked.connect(self._on_show_unpaid_signups)
        self.btn_clear_signup_search.clicked.connect(lambda: self.edt_signup_search.setText(""))
        search_row.addWidget(QLabel("搜尋"))
        search_row.addWidget(self.edt_signup_search)
        search_row.addWidget(self.btn_show_all_signups)
        search_row.addWidget(self.btn_show_unpaid_signups)
        search_row.addWidget(self.btn_clear_signup_search)
        search_row.addStretch(1)
        g1.addLayout(search_row)

        self.tbl_signups = QTableWidget(0, 5)
        self.tbl_signups.setHorizontalHeaderLabels(["繳費", "姓名", "電話", "方案", "金額"])
        self.tbl_signups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_signups.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_signups.setSelectionMode(QTableWidget.MultiSelection)
        self.tbl_signups.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_signups.setAlternatingRowColors(True)
        g1.addWidget(self.tbl_signups, 1)

        row_btn_1 = QHBoxLayout()
        self.btn_mark_paid = QPushButton("按此繳費")
        self.btn_print_signup_list = QPushButton("列印名單")
        self.edt_payment_handler = QLineEdit()
        self.edt_payment_handler.setPlaceholderText("經手人（必填）")
        self._apply_payment_handler_editable_state()
        self.btn_mark_paid.setEnabled(False)
        self.btn_mark_paid.clicked.connect(self._on_mark_signup_paid)
        self.edt_payment_handler.textChanged.connect(self._sync_mark_paid_enabled)
        self.btn_print_signup_list.clicked.connect(self._on_print_signup_list)
        row_btn_1.addWidget(self.btn_mark_paid)
        row_btn_1.addWidget(self.edt_payment_handler, 1)
        self.btn_open_item_stats_dialog = QPushButton("總品項列印")
        self.btn_open_item_stats_dialog.clicked.connect(self._open_item_stats_dialog)
        row_btn_1.addWidget(self.btn_open_item_stats_dialog)
        self.btn_open_wenshu_dialog = QPushButton("文疏列印")
        self.btn_open_wenshu_dialog.clicked.connect(self._open_wenshu_dialog)
        row_btn_1.addWidget(self.btn_open_wenshu_dialog)
        row_btn_1.addStretch(1)
        row_btn_1.addWidget(self.btn_print_signup_list)
        g1.addLayout(row_btn_1)
        self._apply_default_payment_handler_if_needed()

        layout.addWidget(grp_detail, 1)



    # -----------------------------
    # Render helpers
    # -----------------------------
    def _render_plans(self, plans: List[Dict]):
        """
        plans: controller.get_activity_plans 回來的 list[dict]
        例如 dict keys: id, name, items, fee_type, amount
        """
        # ✅ 同步到 self._plans（若你後續其他地方還在用 self._plans）
        self._plans = [
            PlanRow(
                id=str(p.get("id", "")),
                name=str(p.get("name", "")),
                items=str(p.get("items", "")),
                fee_type=str(p.get("fee_type", "")),
                amount=(None if p.get("amount") in (None, "") else int(float(p.get("amount")))),
            )
            for p in (plans or [])
        ]

        self.tbl_plans.setRowCount(0)

        for r, p in enumerate(self._plans):
            self.tbl_plans.insertRow(r)

            # 把 plan_id 存到 UserRole，後續「修改/刪除方案」會用到
            it0 = QTableWidgetItem(p.name)
            it0.setData(Qt.UserRole, p.id)
            self.tbl_plans.setItem(r, 0, it0)

            self.tbl_plans.setItem(r, 1, QTableWidgetItem(p.items))
            self.tbl_plans.setItem(r, 2, QTableWidgetItem(self._fee_text(p.fee_type)))

            amt_text = "報名時填" if p.fee_type == "donation" else (str(p.amount) if p.amount is not None else "-")
            self.tbl_plans.setItem(r, 3, QTableWidgetItem(amt_text))

        self.tbl_plans.resizeRowsToContents()

    def set_default_payment_handler(self, username: str):
        self._default_payment_handler = (username or "").strip()
        self._apply_default_payment_handler_if_needed()

    def set_current_user_role(self, role: str):
        self._current_user_role = (role or "").strip()
        self._apply_payment_handler_editable_state()

    def _can_edit_payment_handler(self) -> bool:
        return (self._current_user_role or "").strip() in {"管理員", "管理者", "會計", "會計人員"}

    def _apply_payment_handler_editable_state(self):
        if not hasattr(self, "edt_payment_handler"):
            return
        editable = self._can_edit_payment_handler()
        self.edt_payment_handler.setReadOnly(not editable)
        if editable:
            self.edt_payment_handler.setToolTip("")
        else:
            self.edt_payment_handler.setToolTip("僅管理員與會計可修改經手人")

    def _apply_default_payment_handler_if_needed(self):
        if not hasattr(self, "edt_payment_handler"):
            return
        if (self.edt_payment_handler.text() or "").strip():
            return
        if self._default_payment_handler:
            self.edt_payment_handler.setText(self._default_payment_handler)


    def _render_signup_stats(self):
        signup_cnt = len(self._signups)

        total = 0
        donation_total = 0
        for s in self._signups:
            for it in s.items:
                total += int(it.subtotal)
                if it.is_donation:
                    donation_total += int(it.subtotal)

        self._set_stat_value(self.stat_signup_cnt, str(signup_cnt))
        self._set_stat_value(self.stat_total, str(total))
        self._set_stat_value(self.stat_donation, str(donation_total))


    def _render_signups_table(self, select_first: bool = False):
        self.tbl_signups.setRowCount(0)
        for r, s in enumerate(self._signups):
            self.tbl_signups.insertRow(r)

            plans_text = "、".join([f"{it.plan_name}×{it.qty}" for it in s.items])
            total = sum(int(it.subtotal) for it in s.items)
            paid_item = QTableWidgetItem("")
            paid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            paid_item.setCheckState(Qt.Unchecked)
            self.tbl_signups.setItem(r, 0, paid_item)
            self.tbl_signups.setItem(r, 1, QTableWidgetItem(s.name))
            self.tbl_signups.setItem(r, 2, QTableWidgetItem(s.phone))
            self.tbl_signups.setItem(r, 3, QTableWidgetItem(plans_text))
            self.tbl_signups.setItem(r, 4, QTableWidgetItem(str(total)))

            # 存 signup_id 到 UserRole（修改/刪除要用）
            for c in range(5):
                self.tbl_signups.item(r, c).setData(Qt.UserRole, s.id)

        self.tbl_signups.resizeRowsToContents()

        if select_first and self.tbl_signups.rowCount() > 0:
            self.tbl_signups.selectRow(0)

    def _get_selected_signup_id(self):
        items = self.tbl_signups.selectedItems()
        if items:
            sid = items[0].data(Qt.UserRole)
            return str(sid) if sid else None

        row = self.tbl_signups.currentRow()
        if row < 0:
            return None
        it = self.tbl_signups.item(row, 0)
        if not it:
            return None
        sid = it.data(Qt.UserRole)
        return str(sid) if sid else None


    def on_edit_signup(self):
        sid = self._get_selected_signup_id()
        if not sid:
            QMessageBox.information(self, "請先選擇", "請先在報名名單中選擇一筆資料。")
            return

        dlg = ActivitySignupEditDialog(self.controller, sid, parent=self)
        if dlg.exec_() == dlg.Accepted:
            # ✅ 更新完要刷新報名名單 + 統計卡
            self._reload_signup_tab()

    def on_delete_signup(self):
        sid = self._get_selected_signup_id()
        if not sid:
            QMessageBox.information(self, "請先選擇", "請先在報名名單中選擇一筆資料。")
            return

        # 從目前選取列拿姓名/電話（比較直覺）
        row = self.tbl_signups.currentRow()
        name = ""
        phone = ""
        if row >= 0:
            it_name = self.tbl_signups.item(row, 1)
            it_phone = self.tbl_signups.item(row, 2)
            name = (it_name.text().strip() if it_name else "")
            phone = (it_phone.text().strip() if it_phone else "")

        # 確認視窗
        msg = f"確定要刪除以下報名資料嗎？\n\n{name} {phone}".strip()
        ok = QMessageBox.question(
            self,
            "確認刪除報名",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        # 執行刪除
        try:
            deleted = self.controller.delete_activity_signup(sid)
            if not deleted:
                QMessageBox.warning(self, "刪除失敗", "刪除失敗：找不到該筆報名資料，或已被刪除。")
                return

            QMessageBox.information(self, "刪除完成", f"已刪除：{name} {phone}".strip())

            # 刷新名單 + 統計卡（你現成的）
            self._reload_signup_tab()

            # （可選）把搜尋框清掉，避免刪完還卡在過濾結果
            # self.signup_q.setText("")

        except Exception as e:
            QMessageBox.critical(self, "刪除失敗", f"刪除報名失敗：\n{e}")

    def _clear_signup_tab(self):
        self._signup_rows = []
        self._signup_rows_filtered = []
        self._signup_filter_mode = "all"

        # 清統計卡
        self._set_stat_value(self.stat_signup_cnt, "0")
        self._set_stat_value(self.stat_total, "0")
        self._set_stat_value(self.stat_donation, "0")

        self.tbl_signups.setRowCount(0)

    def _parse_plan_items_text(self, text: str) -> List[Tuple[str, int]]:
        items: List[Tuple[str, int]] = []
        for token in re.split(r"[、,\n/]+", str(text or "")):
            t = token.strip()
            if not t:
                continue
            m = re.match(r"^(.*?)(?:[xX×*＊]\s*(\d+))?$", t)
            if not m:
                continue
            name = (m.group(1) or "").strip()
            if not name:
                continue
            qty = int(m.group(2) or 1)
            items.append((name, max(1, qty)))
        return items

    def _plan_qty_map_from_summary(self, summary: str) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for token in re.split(r"[、,\n]+", str(summary or "")):
            t = token.strip()
            if not t:
                continue
            m = re.match(r"^(.*?)[xX×*＊]\s*(\d+)$", t)
            if not m:
                continue
            name = (m.group(1) or "").strip()
            qty = int(m.group(2) or 0)
            if name and qty > 0:
                out[name] = out.get(name, 0) + qty
        return out

    def _build_item_stats_rows(self, rows: List[Dict]) -> List[Tuple[str, int]]:
        plan_item_map: Dict[str, List[Tuple[str, int]]] = {}
        for p in (getattr(self, "_plans", []) or []):
            plan_item_map[str(p.name)] = self._parse_plan_items_text(p.items)

        agg: Dict[str, int] = {}
        for r in rows or []:
            plan_qty_map = self._plan_qty_map_from_summary(str((r or {}).get("plan_summary", "")))
            for plan_name, plan_qty in plan_qty_map.items():
                for item_name, item_qty in plan_item_map.get(plan_name, []):
                    agg[item_name] = agg.get(item_name, 0) + plan_qty * item_qty

        return sorted(agg.items(), key=lambda x: x[0])

    def _render_signup_detail_table(self, rows: List[Dict]):
        self.tbl_signups.setRowCount(0)
        for r in rows or []:
            row = self.tbl_signups.rowCount()
            self.tbl_signups.insertRow(row)
            paid_item = QTableWidgetItem("")
            paid = int(r.get("is_paid") or 0) == 1
            if paid:
                paid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                paid_item.setCheckState(Qt.Checked)
            else:
                paid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                paid_item.setCheckState(Qt.Unchecked)
            self.tbl_signups.setItem(row, 0, paid_item)
            self.tbl_signups.setItem(row, 1, QTableWidgetItem(str(r.get("person_name", ""))))
            self.tbl_signups.setItem(row, 2, QTableWidgetItem(str(r.get("person_phone", ""))))
            self.tbl_signups.setItem(row, 3, QTableWidgetItem(str(r.get("plan_summary", ""))))
            self.tbl_signups.setItem(row, 4, QTableWidgetItem(str(int(r.get("total_amount", 0) or 0))))
            sid = str(r.get("signup_id", ""))
            for c in range(5):
                it = self.tbl_signups.item(row, c)
                if it:
                    it.setData(Qt.UserRole, sid)
                    it.setData(Qt.UserRole + 1, 1 if paid else 0)
            receipt_no = str(r.get("payment_receipt_number", "") or "")
            if receipt_no:
                self.tbl_signups.item(row, 0).setToolTip(f"已繳費，收據號碼：{receipt_no}")
        self.tbl_signups.resizeRowsToContents()

    def _simple_print_preview(self, title: str, lines: List[str]):
        text = "\n".join(lines or [])
        QMessageBox.information(self, title, text if text else "沒有可列印內容")

    def _on_print_signup_list(self):
        rows = []
        for r in self._signup_rows_filtered or []:
            paid_mark = "✓" if int(r.get("is_paid") or 0) == 1 else ""
            amount = int(r.get("total_amount", 0) or 0)
            rows.append([
                paid_mark,
                str(r.get("person_name", "") or ""),
                str(r.get("person_phone", "") or ""),
                str(r.get("plan_summary", "") or ""),
                str(amount),
            ])
        if not rows:
            QMessageBox.information(self, "列印名單", "沒有可列印內容")
            return
        PrintHelper.print_table_report("報名名單（明細）", ["繳費", "姓名", "電話", "方案", "金額"], rows)

    def _on_show_all_signups(self):
        self._signup_filter_mode = "all"
        self._apply_signup_filter()

    def _on_show_unpaid_signups(self):
        self._signup_filter_mode = "unpaid"
        self._apply_signup_filter()

    def _apply_signup_filter(self):
        rows = self._signup_rows or []
        kw = (self.edt_signup_search.text() or "").strip().lower() if hasattr(self, "edt_signup_search") else ""
        if self._signup_filter_mode == "unpaid":
            rows = [r for r in rows if int((r or {}).get("is_paid") or 0) == 0]
        if kw:
            rows = [
                r for r in rows
                if kw in str((r or {}).get("person_name", "")).lower()
                or kw in str((r or {}).get("person_phone", "")).lower()
            ]
        self._signup_rows_filtered = rows
        self._render_signup_detail_table(rows)
        self._sync_mark_paid_enabled()

    def _on_signup_search_changed(self, _text):
        self._apply_signup_filter()

    def _sync_mark_paid_enabled(self):
        has_handler = bool((self.edt_payment_handler.text() or "").strip()) if hasattr(self, "edt_payment_handler") else False
        if hasattr(self, "btn_mark_paid"):
            self.btn_mark_paid.setEnabled(has_handler)

    def _get_checked_signup_ids(self) -> List[str]:
        ids = set()
        for row in range(self.tbl_signups.rowCount()):
            it = self.tbl_signups.item(row, 0)
            if not it:
                continue
            if int(it.data(Qt.UserRole + 1) or 0) == 1:
                continue
            if it.checkState() != Qt.Checked:
                continue
            sid = str(it.data(Qt.UserRole) or "").strip()
            if sid:
                ids.add(sid)
        return sorted(ids)

    def _on_mark_signup_paid(self):
        if not self._current_activity_id:
            QMessageBox.information(self, "請先選擇活動", "請先選擇活動再進行繳費。")
            return
        handler = (self.edt_payment_handler.text() or "").strip()
        if not handler:
            QMessageBox.information(self, "欄位不足", "請先輸入經手人，再進行繳費。")
            return
        signup_ids = self._get_checked_signup_ids()
        if not signup_ids:
            QMessageBox.information(self, "請先選擇", "請先勾選未繳費名單，再執行繳費。")
            return
        try:
            result = self.controller.mark_activity_signups_paid(
                self._current_activity_id,
                signup_ids,
                handler=handler,
            )
        except Exception as e:
            QMessageBox.warning(self, "繳費失敗", str(e))
            return
        self._reload_signup_tab()
        paid_count = int(result.get("paid_count", 0) or 0)
        skipped_count = int(result.get("skipped_count", 0) or 0)
        msg = [f"完成繳費：{paid_count} 筆"]
        if skipped_count > 0:
            msg.append(f"略過已繳費：{skipped_count} 筆")
        receipts = result.get("receipt_numbers") or []
        if receipts:
            msg.append("收據號碼：" + "、".join(str(x) for x in receipts[:10]))
        QMessageBox.information(self, "繳費完成", "\n".join(msg))

    def _open_wenshu_dialog(self):
        dlg = WenshuPrintDialog(self._signup_rows or [], self)
        dlg.exec_()

    def _open_item_stats_dialog(self):
        rows = self._build_item_stats_rows(self._signup_rows or [])
        dlg = ItemStatsDialog(rows, self)
        dlg.exec_()


    # -----------------------------
    # Small UI helpers
    # -----------------------------
    def _make_stat_card(self, title: str, value: str, emph: bool = False) -> QWidget:
        card = QFrame()
        card.setObjectName("statCardEmph" if emph else "statCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(68)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet("color:#6B7280;")
        v = QLabel(value)
        v.setFont(self._bold_font(16))

        lay.addWidget(t)
        lay.addWidget(v)

        # 存 label 引用，方便更新
        card._value_label = v  # type: ignore
        return card

    def _set_stat_value(self, card: QWidget, value: str):
        v = getattr(card, "_value_label", None)
        if v:
            v.setText(value)

    def _bold_font(self, size: int = 12) -> QFont:
        f = QFont()
        f.setPointSize(size)
        f.setBold(True)
        return f

    def _fee_text(self, fee_type: str) -> str:
        if fee_type == "fixed":
            return "固定金額"
        if fee_type == "donation":
            return "隨喜（自由填）"
        return "其他"

    def _toast(self, msg: str):
        # 先用簡單方式（你要的話我也可以幫你做右下角 toast widget）
        print(msg)

    def _apply_qss(self):
        # 先給一點點「暖色系 + 大按鈕」的感覺（你之後也可以統一放到 global qss）
        self.setStyleSheet("""
        QGroupBox {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            margin-top: 8px;
            background: #FFFFFF;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: #8A4B09;
            font-weight: 700;
        }
        QLineEdit, QComboBox {
            padding: 8px 10px;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            background: #FFFFFF;
        }
        QPushButton {
            padding: 6px 10px;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            background: #FFFFFF;
        }
        QPushButton:hover { border-color: #D1D5DB; }
        QTabWidget::pane {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            top: -1px;
            background: #FFFFFF;
        }
        QTabBar::tab {
            padding: 10px 12px;
            border: 1px solid transparent;
            color: #6B7280;
            font-weight: 700;
        }
        QTabBar::tab:selected {
            color: #8A4B09;
            border: 1px solid #F2D1A7;
            border-bottom-color: #FFFFFF;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            background: #FFF3DF;
        }
        QTableWidget {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            gridline-color: #F1F1F1;
        }
        QHeaderView::section {
            background: #FAFAFA;
            color: #6B7280;
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid #E5E7EB;
            font-size: 12px;
        }
        QFrame#statCard {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            background: #FFFFFF;
        }
        QFrame#statCardEmph {
            border: 1px solid #F2D1A7;
            border-radius: 12px;
            background: #FFF3DF;
        }
        QTextEdit {
            padding: 8px 10px;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            background: #FFFFFF;
        }
        QTextEdit:hover { border-color: #D1D5DB; }
        QTextEdit:focus { border-color: #D1D5DB; }
        """)

    def on_new_activity(self):
        dlg = ActivityEditDialog(self.controller, mode="new", parent=self)
        if dlg.exec_() == dlg.Accepted:
            new_id = dlg.result_activity_id()
            if new_id:
                self.activity_saved.emit(new_id)

    def on_edit_activity(self):
        if not self._current_activity_id:
            QMessageBox.warning(self, "請先選擇活動", "請先從左側清單選擇一筆活動")
            return

        activity_data = self.controller.get_activity_by_id(self._current_activity_id)
        dlg = ActivityEditDialog(
            self.controller,
            mode="edit",
            activity_id=self._current_activity_id,
            activity_data=activity_data,
            parent=self
        )
        if dlg.exec_() == dlg.Accepted:
            self.activity_saved.emit(self._current_activity_id)

    def on_delete_activity(self):
        if not self._current_activity_id:
            QMessageBox.warning(self, "請先選擇活動", "請先從左側清單選擇一筆活動")
            return

        activity_id = self._current_activity_id
        data = self.controller.get_activity_by_id(activity_id) or {}
        name = data.get("name", "")
        start = data.get("activity_start_date", "")
        end = data.get("activity_end_date", "")

        # 方案/報名數提示（如果 controller 有這個方法）
        plan_cnt = None
        signup_cnt = None
        if hasattr(self.controller, "get_activity_delete_stats"):
            stat = self.controller.get_activity_delete_stats(activity_id) or {}
            plan_cnt = stat.get("plan_cnt", 0)
            signup_cnt = stat.get("signup_cnt", 0)

        detail_lines = [
            f"活動名稱：{name}",
            f"活動ID：{activity_id}",
            f"活動日期國曆：{start} ～ {end}" if start or end else "活動日期國曆：—",
        ]
        if plan_cnt is not None and signup_cnt is not None:
            detail_lines.append(f"方案數：{plan_cnt}　｜　報名數：{signup_cnt}")
            if signup_cnt > 0:
                detail_lines.append("⚠️ 注意：刪除活動會連同「報名資料/明細」一併刪除，無法復原。")

        msg = "確定要刪除這個活動嗎？\n\n" + "\n".join(detail_lines)

        ok = QMessageBox.question(
            self,
            "確認刪除活動",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        try:
            deleted = self.controller.delete_activity(activity_id)
            if not deleted:
                QMessageBox.warning(self, "刪除失敗", "刪除失敗：找不到活動或已被刪除")
                return

            # 清空右側顯示（避免還留著舊資料）
            self._current_activity_id = None
            self._clear_activity_form()
            self.tbl_plans.setRowCount(0)
            self.tbl_signups.setRowCount(0)
            self._clear_signup_tab()

            QMessageBox.information(self, "刪除完成", "活動已刪除。")

            # 通知外層刷新左側清單
            self.activity_deleted.emit(activity_id)

        except Exception as e:
            QMessageBox.critical(self, "刪除失敗", f"刪除活動失敗：\n{e}")


    def on_new_plan(self):
        if not self._current_activity_id:
            QMessageBox.warning(self, "請先選擇活動", "要新增方案前請先選擇一個活動")
            return

        dlg = PlanEditDialog(
            self.controller,
            mode="new",
            activity_id=self._current_activity_id,
            parent=self
        )
        if dlg.exec_() == dlg.Accepted:
            self.reload_plans()

    def _reload_signup_tab(self):
        if not self._current_activity_id:
            return

        rows = self.controller.get_activity_signups(self._current_activity_id)
        self._signup_rows = list(rows or [])

        # ===== 統計卡 =====
        signup_cnt = len(self._signup_rows)
        total = sum(int(r.get("total_amount", 0) or 0) for r in self._signup_rows)
        donation_total = sum(int(r.get("donation_amount", 0) or 0) for r in self._signup_rows)

        self._set_stat_value(self.stat_signup_cnt, str(signup_cnt))
        self._set_stat_value(self.stat_total, str(total))
        self._set_stat_value(self.stat_donation, str(donation_total))

        self._apply_signup_filter()
        self._sync_mark_paid_enabled()

    def load_activity(self, activity_id: str):

        activity_id = (activity_id or "").strip()
        if not activity_id:
            self._current_activity_id = None
            self._clear_activity_form()
            self.tbl_plans.setRowCount(0)
            self._clear_signup_tab()
            return

        self._current_activity_id = activity_id

        data = self.controller.get_activity_by_id(activity_id)
        if not data:
            QMessageBox.warning(self, "載入失敗", "找不到活動資料")
            return

        # 下面這些欄位名稱請用你面板上的實際 widget 名稱替換
        self.f_name.setText(data.get("name", ""))
        self.f_start.setText(normalize_ymd_text(data.get("activity_start_date", "")))
        self.f_end.setText(normalize_ymd_text(data.get("activity_end_date", "")))
        self.f_note.setPlainText(data.get("note", ""))
        self.reload_plans()
        self._reload_signup_tab()

    def reload_plans(self):
        if not self._current_activity_id:
            self.tbl_plans.setRowCount(0)
            return

        plans = self.controller.get_activity_plans(self._current_activity_id) or []
        self._render_plans(plans)


    def _collect_activity_form(self) -> Optional[dict]:
        name = self.f_name.text().strip()
        start = normalize_ymd_text(self.f_start.text().strip())
        end = normalize_ymd_text(self.f_end.text().strip())
        note = self.f_note.toPlainText().strip()
        self.f_start.setText(start)
        self.f_end.setText(end)

        # 必填檢查
        if not name:
            QMessageBox.warning(self, "欄位不足", "請輸入活動名稱")
            return None
        if not start:
            QMessageBox.warning(self, "欄位不足", "請輸入活動開始日期國曆（activity_start_date）")
            return None
        if not end:
            QMessageBox.warning(self, "欄位不足", "請輸入活動結束日期國曆（activity_end_date）")
            return None
        if not is_valid_ymd_text(start):
            QMessageBox.warning(self, "格式錯誤", "活動開始日期請使用 YYYY/MM/DD")
            return None
        if not is_valid_ymd_text(end):
            QMessageBox.warning(self, "格式錯誤", "活動結束日期請使用 YYYY/MM/DD")
            return None

        return {
            "name": name,
            "activity_start_date": start,
            "activity_end_date": end,
            "note": note,
        }

    def _clear_activity_form(self):
        self.f_name.clear()
        self.f_start.clear()
        self.f_end.clear()
        self.f_note.clear()

    def _status_text_to_int(self, text: str) -> int:
        # 你新 schema 只有 0/1，先簡化：
        # 進行中/未開始 -> 1，已結束 -> 0（你想要更細緻再加欄位）
        if text == "已結束":
            return 0
        return 1

    def _status_int_to_text(self, val: int) -> str:
        return "進行中" if int(val) == 1 else "已結束"

    def _format_date_range(self, start: str, end: str) -> str:
        if start and end and start != end:
            return f"{start} ～ {end}"
        return start or end or ""

    # -------------------------
    # Activity Plans
    # -------------------------

    def _get_selected_plan_id(self) -> Optional[str]:
        row = self.tbl_plans.currentRow()
        if row < 0:
            return None
        it = self.tbl_plans.item(row, 0)
        if it is None:
            return None
        pid = it.data(Qt.UserRole)
        return str(pid) if pid else None

    def on_edit_plan(self):
        if not self._current_activity_id:
            QMessageBox.warning(self, "請先選擇活動", "請先在左側選擇一個活動，再修改方案")
            return

        plan_id = self._get_selected_plan_id()
        if not plan_id:
            QMessageBox.information(self, "尚未選擇方案", "請先點選下方方案表格中的一列")
            return

        # 優先向 controller 取完整資料（含 note）
        plan_data = None
        if hasattr(self.controller, "get_activity_plan_by_id"):
            plan_data = self.controller.get_activity_plan_by_id(plan_id)

        # 若 controller 沒有提供，退回使用目前表格資料
        if not plan_data:
            for p in getattr(self, "_plans", []):
                if str(p.id) == str(plan_id):
                    plan_data = {
                        "id": p.id,
                        "activity_id": self._current_activity_id,
                        "name": p.name,
                        "items": p.items,
                        "fee_type": p.fee_type,
                        "amount": p.amount,
                        "note": "",
                    }
                    break

        dlg = PlanEditDialog(
            self.controller,
            mode="edit",
            activity_id=self._current_activity_id,
            plan_id=plan_id,
            plan_data=plan_data,
            parent=self,
        )
        if dlg.exec_() == dlg.Accepted:
            self.reload_plans()

    def on_delete_plan(self):
        if not self._current_activity_id:
            QMessageBox.warning(self, "請先選擇活動", "請先在左側選擇一個活動，再刪除方案")
            return

        plan_id = self._get_selected_plan_id()
        if not plan_id:
            QMessageBox.information(self, "尚未選擇方案", "請先點選下方方案表格中的一列")
            return

        plan_name = ""
        row = self.tbl_plans.currentRow()
        if row >= 0 and self.tbl_plans.item(row, 0):
            plan_name = self.tbl_plans.item(row, 0).text()

        ok = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除方案嗎？\n\n方案：{plan_name or plan_id}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ok != QMessageBox.Yes:
            return

        try:
            if not hasattr(self.controller, "delete_activity_plan"):
                raise AttributeError("controller.delete_activity_plan not found")
            self.controller.delete_activity_plan(plan_id)
            self.reload_plans()
        except Exception as e:
            QMessageBox.critical(self, "刪除失敗", f"刪除方案失敗：\n{e}")


    # def _on_signup_row_selected(self):
    #     items = self.tbl_signup_list.selectedItems()
    #     if not items:
    #         return

    #     signup_id = items[0].data(Qt.UserRole)
    #     self._show_signup_detail(signup_id)

    # def _show_signup_detail(self, signup_id):
    #     detail = self.controller.get_activity_signup_detail(signup_id)

    #     person = detail["person"]
    #     self.lbl_person_name.setText(person["name"])
    #     self.lbl_person_phone.setText(person["phone"])
    #     self.lbl_person_address.setText(person["address"] or "-")

    #     self.tbl_signup_detail.setRowCount(0)
    #     total = 0

    #     for item in detail["items"]:
    #         row = self.tbl_signup_detail.rowCount()
    #         self.tbl_signup_detail.insertRow(row)

    #         self.tbl_signup_detail.setItem(row, 0, QTableWidgetItem(item["plan_name"]))
    #         self.tbl_signup_detail.setItem(row, 1, QTableWidgetItem(str(item["qty"])))
    #         self.tbl_signup_detail.setItem(row, 2, QTableWidgetItem(str(item["unit_price"])))
    #         self.tbl_signup_detail.setItem(row, 3, QTableWidgetItem(str(item["line_total"])))

    #         total += item["line_total"]

    #     self.lbl_total_amount.setText(str(total))

    # def _on_delete_signup_clicked(self):
    #     items = self.tbl_signup_list.selectedItems()
    #     if not items:
    #         return

    #     signup_id = items[0].data(Qt.UserRole)
    #     self.controller.delete_activity_signup(signup_id)
    #     self._reload_signup_tab()
