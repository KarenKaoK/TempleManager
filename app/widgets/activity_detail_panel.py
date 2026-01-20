from dataclasses import dataclass
from typing import List, Optional, Dict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame, QFormLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QSizePolicy, QGroupBox
)
from PyQt5.QtWidgets import QMessageBox
import uuid
from datetime import datetime


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


# -----------------------------
# Panel 
# -----------------------------
class ActivityDetailPanel(QWidget):
    request_back = pyqtSignal()
    activity_saved = pyqtSignal(str)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._current_activity_id: Optional[str] = None

        self._plans: List[PlanRow] = []
        self._signups: List[SignupRow] = []

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

        # 左側：標題 + meta
        self.lbl_title = QLabel("安座大典")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        self.lbl_title.setFont(f)

        self.lbl_meta = QLabel("20260115-001 ｜ 2026/01/15 ～ 2026/01/15 ｜ 進行中")
        self.lbl_meta.setStyleSheet("color:#6B7280;")

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_meta)

        header_layout.addLayout(title_box, 1)

        # ✅ 中間撐開，右側按鈕自然靠右
        header_layout.addStretch(1)

        # 右側：操作按鈕
        self.btn_back = QPushButton("返回")
        self.btn_new = QPushButton("+ 新增活動")
        self.btn_edit = QPushButton("修改活動")
        self.btn_del = QPushButton("刪除活動")

        self.btn_back.clicked.connect(self.request_back.emit)

        self.btn_new.clicked.connect(self.on_new_activity)
        self.btn_edit.clicked.connect(lambda: self._toast("TODO: 修改活動"))
        self.btn_del.clicked.connect(lambda: self._toast("TODO: 刪除活動"))

        for b in (self.btn_back, self.btn_new, self.btn_edit, self.btn_del):
            b.setMinimumHeight(34)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.addWidget(self.btn_back)
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

        # Tab 2：報名狀況 / 名單
        self.tab_signup = QWidget()
        self.tabs.addTab(self.tab_signup, "② 報名狀況 / 報名名單")
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
        self.f_status = QComboBox()
        self.f_status.addItems(["進行中", "未開始", "已結束"])
        self.f_note = QLineEdit()

        form.addRow("活動名稱", self.f_name)


        date_row = QWidget()
        date_row_l = QHBoxLayout(date_row)
        date_row_l.setContentsMargins(0, 0, 0, 0)
        date_row_l.setSpacing(8)
        date_row_l.addWidget(self.f_start)
        date_row_l.addWidget(QLabel("～"))
        date_row_l.addWidget(self.f_end)

        form.addRow("日期", date_row)
        form.addRow("狀態", self.f_status)
        form.addRow("備註", self.f_note)

        lf.addLayout(form, 1)

        btn_save = QPushButton("儲存活動資料")
        btn_save.setMinimumHeight(36)
        btn_save.clicked.connect(self.on_save_activity)
        lf.addWidget(btn_save, 0, Qt.AlignRight)

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

        self.btn_plan_new.clicked.connect(lambda: self._toast("TODO: 新增方案 Dialog"))
        self.btn_plan_edit.clicked.connect(lambda: self._toast("TODO: 修改方案 Dialog"))
        self.btn_plan_del.clicked.connect(lambda: self._toast("TODO: 刪除方案"))

        plan_btn_row.addWidget(self.btn_plan_new)
        plan_btn_row.addWidget(self.btn_plan_edit)
        plan_btn_row.addWidget(self.btn_plan_del)
        plan_btn_row.addStretch(1)
        rf.addLayout(plan_btn_row)

        self.tbl_plans = QTableWidget(0, 4)
        self.tbl_plans.setHorizontalHeaderLabels(["方案名稱", "方案項目", "費用方式", "金額"])
        self.tbl_plans.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_plans.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_plans.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_plans.setAlternatingRowColors(True)

        rf.addWidget(self.tbl_plans, 1)

        hint = QLabel("✔ 隨喜方案：金額在報名時可自由填寫（這版已預留行為）")
        hint.setStyleSheet("color:#6B7280;")
        rf.addWidget(hint)

        layout.addWidget(left, 4)
        layout.addWidget(right, 6)

    def _build_tab_signup(self):
        layout = QVBoxLayout(self.tab_signup)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 統計卡片（4格）
        stats = QGridLayout()
        stats.setHorizontalSpacing(10)
        stats.setVerticalSpacing(10)

        self.stat_signup_cnt = self._make_stat_card("報名人數", "0", emph=True)
        self.stat_plan_cnt = self._make_stat_card("方案數量", "0")
        self.stat_total = self._make_stat_card("預估總收入", "0")
        self.stat_donation = self._make_stat_card("其中隨喜", "0")

        stats.addWidget(self.stat_signup_cnt, 0, 0)
        stats.addWidget(self.stat_plan_cnt, 0, 1)
        stats.addWidget(self.stat_total, 0, 2)
        stats.addWidget(self.stat_donation, 0, 3)

        layout.addLayout(stats)

        # 下半部：左名單、右明細
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        layout.addLayout(bottom, 1)

        # 左：報名名單
        left = QGroupBox("報名名單（點選一筆 → 右側顯示明細）")
        lf = QVBoxLayout(left)
        lf.setContentsMargins(12, 12, 12, 12)
        lf.setSpacing(10)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.signup_q = QLineEdit()
        self.signup_q.setPlaceholderText("搜尋姓名 / 電話")
 
        search_row.addWidget(self.signup_q, 1)
        lf.addLayout(search_row)

        self.tbl_signups = QTableWidget(0, 4)
        self.tbl_signups.setHorizontalHeaderLabels(["姓名", "電話", "方案", "應收"])
        self.tbl_signups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_signups.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_signups.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_signups.setAlternatingRowColors(True)
        self.tbl_signups.itemSelectionChanged.connect(self._on_signup_selected)

        lf.addWidget(self.tbl_signups, 1)

        # 右：報名明細
        right = QGroupBox("報名明細")
        rf = QVBoxLayout(right)
        rf.setContentsMargins(12, 12, 12, 12)
        rf.setSpacing(10)

        info = QFormLayout()
        info.setLabelAlignment(Qt.AlignRight)
        info.setHorizontalSpacing(10)
        info.setVerticalSpacing(10)

        self.d_name = QLabel("（尚未選擇）")
        self.d_phone = QLabel("-")
        self.d_address = QLabel("-")
        self.d_name.setFont(self._bold_font())

        info.addRow("姓名", self.d_name)
        info.addRow("電話", self.d_phone)
        info.addRow("地址", self.d_address)

        rf.addLayout(info)

        self.tbl_signup_items = QTableWidget(0, 4)
        self.tbl_signup_items.setHorizontalHeaderLabels(["方案", "數量", "單價", "小計"])
        self.tbl_signup_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_signup_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signup_items.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_signup_items.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_signup_items.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_signup_items.setAlternatingRowColors(True)
        rf.addWidget(self.tbl_signup_items, 1)

        foot = QHBoxLayout()
        self.d_total = QLabel("0")
        self.d_total.setFont(self._bold_font())
        foot.addStretch(1)
        foot.addWidget(QLabel("合計"))
        foot.addWidget(self.d_total)
        rf.addLayout(foot)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        btn_edit = QPushButton("修改報名")
        btn_del = QPushButton("刪除報名")
        btn_edit.clicked.connect(lambda: self._toast("TODO: 編輯報名"))
        btn_del.clicked.connect(lambda: self._toast("TODO: 刪除報名"))
        btn_edit.setMinimumHeight(32)
        btn_del.setMinimumHeight(32)
        action_row.addWidget(btn_edit)
        action_row.addWidget(btn_del)
        rf.addLayout(action_row)

        bottom.addWidget(left, 6)
        bottom.addWidget(right, 4)

    # -----------------------------
    # Public: load data
    # -----------------------------
    def load_mock_activity(self, activity_id: str):
        self._current_activity_id = activity_id

        if activity_id == "1":
            title = "二月元帥加持"
            meta = "20260115-002 ｜ 2026/01/15 ～ 2026/01/15 ｜ 進行中"
            self._plans = [
                PlanRow("p1", "元帥加持", "加持符*1", "fixed", 300),
            ]
            self._signups = [
                SignupRow(
                    id="s1",
                    name="阿春",
                    phone="0912-000-111",
                    address="新北市",
                    items=[
                        SignupItemRow("p1", "元帥加持", 1, 300, 300, False),
                    ],
                )
            ]
        else:
            title = "安座大典"
            meta = "20260115-001 ｜ 2026/01/15 ～ 2026/01/15 ｜ 進行中"
            self._plans = [
                PlanRow("p2", "安坐平安", "蓮花*9", "fixed", 999),
                PlanRow("p3", "快快樂樂", "補運*9", "fixed", 333),
                PlanRow("p4", "加購A", "金紙組", "fixed", 200),
                PlanRow("p5", "隨喜祈福", "香油 / 隨喜", "donation", None),
            ]
            self._signups = [
                SignupRow(
                    id="s2",
                    name="小魔女",
                    phone="0909-090-090",
                    address="大樹下",
                    items=[
                        SignupItemRow("p2", "安坐平安", 1, 999, 999, False),
                        SignupItemRow("p5", "隨喜祈福", 1, 600, 600, True),
                    ],
                ),
                SignupRow(
                    id="s3",
                    name="林先生",
                    phone="0988-777-666",
                    address="桃園",
                    items=[
                        SignupItemRow("p3", "快快樂樂", 2, 333, 666, False),
                    ],
                )
            ]

        self.lbl_title.setText(title)
        self.lbl_meta.setText(meta)

        # tab1 form（demo 先帶）
        self.f_name.setText(title)

        self.f_start.setText("2026/01/15")
        self.f_end.setText("2026/01/15")
        self.f_status.setCurrentText("進行中")
        self.f_note.setText("")

        self._render_plans()
        self._render_signup_stats()
        self._render_signups_table(select_first=True)

    # -----------------------------
    # Render helpers
    # -----------------------------
    def _render_plans(self):
        self.tbl_plans.setRowCount(0)
        for r, p in enumerate(self._plans):
            self.tbl_plans.insertRow(r)
            self.tbl_plans.setItem(r, 0, QTableWidgetItem(p.name))
            self.tbl_plans.setItem(r, 1, QTableWidgetItem(p.items))
            self.tbl_plans.setItem(r, 2, QTableWidgetItem(self._fee_text(p.fee_type)))
            amt_text = "報名時填" if p.fee_type == "donation" else (str(p.amount) if p.amount is not None else "-")
            self.tbl_plans.setItem(r, 3, QTableWidgetItem(amt_text))

        self.tbl_plans.resizeRowsToContents()

    def _render_signup_stats(self):
        signup_cnt = len(self._signups)
        plan_cnt = len(self._plans)

        total = 0
        donation_total = 0
        for s in self._signups:
            for it in s.items:
                total += int(it.subtotal)
                if it.is_donation:
                    donation_total += int(it.subtotal)

        self._set_stat_value(self.stat_signup_cnt, str(signup_cnt))
        self._set_stat_value(self.stat_plan_cnt, str(plan_cnt))
        self._set_stat_value(self.stat_total, str(total))
        self._set_stat_value(self.stat_donation, str(donation_total))

    def _render_signups_table(self, select_first: bool = False):
        self.tbl_signups.setRowCount(0)
        for r, s in enumerate(self._signups):
            self.tbl_signups.insertRow(r)

            plans_text = "、".join([f"{it.plan_name}×{it.qty}" for it in s.items])
            total = sum(int(it.subtotal) for it in s.items)

            self.tbl_signups.setItem(r, 0, QTableWidgetItem(s.name))
            self.tbl_signups.setItem(r, 1, QTableWidgetItem(s.phone))
            self.tbl_signups.setItem(r, 2, QTableWidgetItem(plans_text))
            self.tbl_signups.setItem(r, 3, QTableWidgetItem(str(total)))

            # 存 id 到 UserRole（選到 row 時可以取回）
            for c in range(4):
                self.tbl_signups.item(r, c).setData(Qt.UserRole, s.id)

        self.tbl_signups.resizeRowsToContents()

        if select_first and self.tbl_signups.rowCount() > 0:
            self.tbl_signups.selectRow(0)
        else:
            self._clear_signup_detail()

    def _on_signup_selected(self):
        row = self.tbl_signups.currentRow()
        if row < 0:
            self._clear_signup_detail()
            return

        item0 = self.tbl_signups.item(row, 0)
        if not item0:
            self._clear_signup_detail()
            return

        sid = item0.data(Qt.UserRole)
        signup = next((x for x in self._signups if x.id == sid), None)
        if not signup:
            self._clear_signup_detail()
            return

        self.d_name.setText(signup.name)
        self.d_phone.setText(signup.phone)
        self.d_address.setText(signup.address)

        self.tbl_signup_items.setRowCount(0)
        total = 0
        for r, it in enumerate(signup.items):
            self.tbl_signup_items.insertRow(r)
            self.tbl_signup_items.setItem(r, 0, QTableWidgetItem(it.plan_name))
            self.tbl_signup_items.setItem(r, 1, QTableWidgetItem(str(it.qty)))

            unit_text = f"隨喜 {it.unit_price}" if it.is_donation else str(it.unit_price)
            self.tbl_signup_items.setItem(r, 2, QTableWidgetItem(unit_text))

            self.tbl_signup_items.setItem(r, 3, QTableWidgetItem(str(it.subtotal)))
            total += int(it.subtotal)

        self.tbl_signup_items.resizeRowsToContents()
        self.d_total.setText(str(total))

    def _clear_signup_detail(self):
        self.d_name.setText("（尚未選擇）")
        self.d_phone.setText("-")
        self.d_address.setText("-")
        self.tbl_signup_items.setRowCount(0)
        self.d_total.setText("0")

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
        """)

    def on_new_activity(self):
        """
        進入新增模式：清空表單、清空目前 activity_id、更新 header
        """
        self._current_activity_id = None
        self._clear_activity_form()
        self._plans = []
        self._signups = []
        self._render_plans()
        self._render_signup_stats()
        self._render_signups_table(select_first=False)

        self.lbl_title.setText("（新增活動）")
        self.lbl_meta.setText("尚未儲存")

        # 切到 tab1
        self.tabs.setCurrentIndex(0)

    def on_save_activity(self):


        ######################
        import inspect

        print("controller obj:", self.controller)
        print("controller type:", type(self.controller))
        print("controller module:", type(self.controller).__module__)
        print("controller file:", inspect.getfile(type(self.controller)))
        print("has insert_activity_new:", hasattr(self.controller, "insert_activity_new"))
        print("dir contains:", [x for x in dir(self.controller) if "activity" in x])
        #####################


        """
        儲存活動資料到 activities（新 schema）
        """
        data = self._collect_activity_form()
        if not data:
            return  # 已顯示錯誤

        try:
            new_id = self.controller.insert_activity_new(data)
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"寫入資料庫失敗：\n{e}")
            return

        self._current_activity_id = new_id

        # 更新 header 顯示
        title = data["name"]
        date_range = self._format_date_range(data["activity_start_date"], data["activity_end_date"])
        status_text = self._status_int_to_text(data["status"])
        self.lbl_title.setText(title)
        self.lbl_meta.setText(f"{new_id} ｜ {date_range} ｜ {status_text}")

        QMessageBox.information(self, "成功", "✅ 活動已新增完成")

        # ✅ 通知外層刷新左側活動清單
        self.activity_saved.emit(new_id)

    def _collect_activity_form(self) -> Optional[dict]:
        name = self.f_name.text().strip()
        start = self.f_start.text().strip()
        end = self.f_end.text().strip()
        note = self.f_note.text().strip()
        status_text = self.f_status.currentText().strip()
        status = self._status_text_to_int(status_text)

        # 必填檢查
        if not name:
            QMessageBox.warning(self, "欄位不足", "請輸入活動名稱")
            return None
        if not start:
            QMessageBox.warning(self, "欄位不足", "請輸入活動開始日期（activity_start_date）")
            return None
        if not end:
            QMessageBox.warning(self, "欄位不足", "請輸入活動結束日期（activity_end_date）")
            return None

        return {
            "name": name,
            "activity_start_date": start,
            "activity_end_date": end,
            "note": note,
            "status": status,
        }

    def _clear_activity_form(self):
        self.f_name.clear()
        self.f_start.clear()
        self.f_end.clear()
        self.f_note.clear()
        self.f_status.setCurrentText("進行中")

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