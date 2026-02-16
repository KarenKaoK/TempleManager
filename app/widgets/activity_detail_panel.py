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
from PyQt5.QtWidgets import QMessageBox, QTextEdit
from app.utils.id_utils import compute_display_status
from app.utils.date_utils import (
    is_valid_ymd_text,
    make_ymd_validator,
    normalize_ymd_text,
)
from app.dialogs.activity_edit_dialog import ActivityEditDialog
from app.dialogs.plan_edit_dialog import PlanEditDialog
from app.dialogs.activity_signup_edit_dialog import ActivitySignupEditDialog


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
    activity_deleted = pyqtSignal(str)


    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._current_activity_id: Optional[str] = None

        self._plans: List[PlanRow] = []
        self._signups: List[SignupRow] = []

        self._current_activity_id = None

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

        # Tab 2：報名狀況 / 名單
        self.tab_signup = QWidget()
        self.tabs.addTab(self.tab_signup, "② 報名狀況 / 報名名單")
        self._build_tab_signup()

        self.signup_q.textChanged.connect(self._on_signup_search_changed)

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
        self.tbl_plans.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_plans.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_plans.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_plans.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_plans.setAlternatingRowColors(True)

        rf.addWidget(self.tbl_plans, 1)


        layout.addWidget(left, 4)
        layout.addWidget(right, 6)

    def _build_tab_signup(self):
        layout = QVBoxLayout(self.tab_signup)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

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

        # 報名名單（唯一區塊）
        grp = QGroupBox("報名名單")
        g = QVBoxLayout(grp)
        g.setContentsMargins(12, 12, 12, 12)
        g.setSpacing(10)

        # 搜尋列
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.signup_q = QLineEdit()
        self.signup_q.setPlaceholderText("搜尋姓名 / 電話")
        search_row.addWidget(self.signup_q, 1)
        g.addLayout(search_row)

        # 表格：姓名、電話、方案、費用
        self.tbl_signups = QTableWidget(0, 4)
        self.tbl_signups.setHorizontalHeaderLabels(["姓名", "電話", "方案", "費用"])
        self.tbl_signups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_signups.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_signups.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_signups.setAlternatingRowColors(True)

        # ✅ 改成：雙擊直接開修改 dialog（之後你再接 dialog）
        self.tbl_signups.itemDoubleClicked.connect(lambda _it: self.on_edit_signup())

        g.addWidget(self.tbl_signups, 1)

        # 右下角按鈕：修改 / 刪除（不再需要右側明細區）
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_signup_edit = QPushButton("修改報名")
        self.btn_signup_delete = QPushButton("刪除報名")
        for b in (self.btn_signup_edit, self.btn_signup_delete):
            b.setMinimumHeight(32)

        self.btn_signup_edit.clicked.connect(self.on_edit_signup)
        self.btn_signup_delete.clicked.connect(self.on_delete_signup)

        btn_row.addWidget(self.btn_signup_edit)
        btn_row.addWidget(self.btn_signup_delete)
        g.addLayout(btn_row)

        layout.addWidget(grp, 1)



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

            self.tbl_signups.setItem(r, 0, QTableWidgetItem(s.name))
            self.tbl_signups.setItem(r, 1, QTableWidgetItem(s.phone))
            self.tbl_signups.setItem(r, 2, QTableWidgetItem(plans_text))
            self.tbl_signups.setItem(r, 3, QTableWidgetItem(str(total)))

            # 存 signup_id 到 UserRole（修改/刪除要用）
            for c in range(4):
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
            it_name = self.tbl_signups.item(row, 0)
            it_phone = self.tbl_signups.item(row, 1)
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
        # 清資料
        self._signup_rows = []
        self._signup_rows_filtered = []

        # 清搜尋框（如果你有這個 widget）
        if hasattr(self, "signup_search"):
            self.signup_search.clear()

        # 清統計卡
        self._set_stat_value(self.stat_signup_cnt, "0")
        self._set_stat_value(self.stat_total, "0")
        self._set_stat_value(self.stat_donation, "0")

        # 清表格
        self.tbl_signups.setRowCount(0)
        self.tbl_signups.clearSelection()


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
        self._signup_rows = rows
        self._signup_rows_filtered = rows

        # ===== 統計卡 =====
        signup_cnt = len(rows)
        plan_cnt = len(self._plans) if hasattr(self, "_plans") else 0
        total = sum(int(r.get("total_amount", 0) or 0) for r in rows)
        donation_total = sum(int(r.get("donation_amount", 0) or 0) for r in rows)


        self._set_stat_value(self.stat_signup_cnt, str(signup_cnt))
        self._set_stat_value(self.stat_total, str(total))
        self._set_stat_value(self.stat_donation, str(donation_total))


        # ===== 左表格 =====
        self.tbl_signups.setRowCount(0)
        for r in rows:
            row = self.tbl_signups.rowCount()
            self.tbl_signups.insertRow(row)

            self.tbl_signups.setItem(row, 0, QTableWidgetItem(r["person_name"]))
            self.tbl_signups.setItem(row, 1, QTableWidgetItem(r["person_phone"]))
            self.tbl_signups.setItem(row, 2, QTableWidgetItem(r["plan_summary"]))
            self.tbl_signups.setItem(row, 3, QTableWidgetItem(str(r["total_amount"])))

            sid = str(r.get("signup_id", ""))
            for c in range(4):
                it = self.tbl_signups.item(row, c)
                if it:
                    it.setData(Qt.UserRole, sid)


        if rows:
            self.tbl_signups.selectRow(0)
        else:
            self.tbl_signups.clearSelection()

    def _on_signup_search_changed(self, text):
        text = text.strip()
        if not text:
            self._signup_rows_filtered = self._signup_rows
        else:
            self._signup_rows_filtered = [
                r for r in self._signup_rows
                if text in r["person_name"] or text in r["person_phone"]
            ]

        self.tbl_signups.setRowCount(0)
        for r in self._signup_rows_filtered:
            row = self.tbl_signups.rowCount()
            self.tbl_signups.insertRow(row)

            self.tbl_signups.setItem(row, 0, QTableWidgetItem(r["person_name"]))
            self.tbl_signups.setItem(row, 1, QTableWidgetItem(r["person_phone"]))
            self.tbl_signups.setItem(row, 2, QTableWidgetItem(r["plan_summary"]))
            self.tbl_signups.setItem(row, 3, QTableWidgetItem(str(r["total_amount"])))

            sid = str(r.get("signup_id", ""))
            for c in range(4):
                it = self.tbl_signups.item(row, c)
                if it:
                    it.setData(Qt.UserRole, sid)



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
        start = self.f_start.text().strip()
        end = self.f_end.text().strip()
        note = self.f_note.toPlainText().strip()

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
