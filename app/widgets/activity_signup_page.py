from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QGroupBox, QSizePolicy,
    QLineEdit, QMessageBox, QDialog,
    QScrollArea, QGridLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import pyqtSignal, Qt

from app.dialogs.activity_household_signup_dialog import ActivityHouseholdSignupDialog
from app.dialogs.activity_signup_edit_dialog import ActivitySignupEditDialog
from app.widgets.activity_plan_panel import ActivityPlanPanel  # backward-compat for tests
from app.widgets.activity_person_panel import ActivityPersonPanel
from app.utils.id_utils import (
    compute_display_status,
    parse_date_str_to_qdate,
)


# -----------------------------
# 活動卡片（新）
# -----------------------------
class _ActivityCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, activity: dict, parent=None):
        super().__init__(parent)
        self.activity = activity or {}
        self._selected = False
        self._build_ui()
        self._apply_style()
        self._disabled = False

    def _get_signup_status(self):
        """
        回傳 (label_text, is_open, status_key)
        status_key:
        - open: 可報名（進行中）
        - not_started: 未開始（但仍可報名/可點）
        - expired: 已過期（不可點）
        """
        start_s = self.activity.get("activity_start_date")
        end_s = self.activity.get("activity_end_date")

        if not start_s or not end_s:
            dr = self.activity.get("date_range", "")
            if "~" in dr:
                start_s, end_s = [x.strip() for x in dr.split("~", 1)]

        start_q = parse_date_str_to_qdate(start_s)
        end_q = parse_date_str_to_qdate(end_s)

        if not start_q or not end_q:
            return "可報名", True, "open"

        status = compute_display_status(start_q, end_q)  # 未開始 / 進行中 / 已結束

        if status == "未開始":
            return "未開始", True, "not_started"   # ✅ 仍可點、仍是橘色系
        if status == "已結束":
            return "已過期", False, "expired"
        return "可報名", True, "open"


    def _build_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("activityCard")
        self.setFrameShape(QFrame.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        title = (self.activity.get("title") or self.activity.get("name") or "未命名活動").strip()
        code = (self.activity.get("code") or self.activity.get("id") or "").strip()
        date_range = (self.activity.get("date_range") or "").strip()

        status_text, is_open, status_key = self._get_signup_status()
        self.lbl_tag = QLabel(status_text)
        self.lbl_tag.setStyleSheet("""
            QLabel{
                padding: 2px 8px;
                border-radius: 10px;
                background: rgba(251,191,36,0.18);
                border: 1px solid rgba(251,191,36,0.35);
                color: #7a4a00;
                font-weight: 800;
            }
        """)

        # self.lbl_title = QLabel(f"{title}（{code}）" if code else title)
        # self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 900;")


        self.lbl_title = QLabel()
        self.lbl_title.setTextFormat(Qt.RichText)

        if code:
            self.lbl_title.setText(
                f"""
                <span style="font-weight:900; color:#111;">
                    {title}
                </span>
                <span style="color:#9CA3AF; margin-left:6px;">
                    （{code}）
                </span>
                """
            )
        else:
            self.lbl_title.setText(title)





        self.lbl_meta = QLabel(date_range)
        self.lbl_meta.setStyleSheet("color:#666666;")

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_row.addWidget(self.lbl_title, 1)
        title_row.addStretch(1)
        title_row.addWidget(self.lbl_tag, 0, Qt.AlignRight | Qt.AlignTop)

        root.addLayout(title_row)
        root.addWidget(self.lbl_meta)


        self.setMinimumHeight(84)

    def set_selected(self, selected: bool):
        if self._disabled:
            self._selected = False
        else:
            self._selected = bool(selected)
        self._apply_style()


    def _apply_style(self):
        status_text, is_open, status_key = self._get_signup_status()
        self.lbl_tag.setText(status_text)

        # 只有 expired 才 disabled
        self._disabled = (status_key == "expired")

        # --- tag style ---
        if status_key == "expired":
            # 灰色（不可點）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 8px;
                    border-radius: 10px;
                    background: rgba(107,114,128,0.12);
                    border: 1px solid rgba(107,114,128,0.25);
                    color: #374151;
                    font-weight: 800;
                }
            """)
        elif status_key == "not_started":
            # 未開始：藍色（跟你圖一樣的感覺）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 10px;
                    border-radius: 12px;
                    background: rgba(59,130,246,0.10);   /* 淡藍底 */
                    border: 1px solid rgba(59,130,246,0.25);
                    color: #1E3A8A;                      /* 深藍字 */
                    font-weight: 800;
                }
            """)
        else:
            # open：原本橘色（可報名）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 8px;
                    border-radius: 10px;
                    background: rgba(251,191,36,0.18);
                    border: 1px solid rgba(251,191,36,0.35);
                    color: #7a4a00;
                    font-weight: 800;
                }
            """)

        # --- card style ---
        if self._disabled:
            self.setCursor(Qt.ArrowCursor)
            self.setStyleSheet("""
                QFrame#activityCard{
                    background: rgba(249,250,251,1.0);
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                }
                QLabel{
                    color: #6B7280;
                }
            """)
            self._selected = False
            return

        # is_open == True（open / not_started 都會到這裡）
        self.setCursor(Qt.PointingHandCursor)

        if self._selected:
            self.setStyleSheet("""
                QFrame#activityCard{
                    background:#FFFFFF;
                    border: 2px solid rgba(245,158,11,0.70);
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#activityCard{
                    background:#FFFFFF;
                    border: 1px solid #E6E6E6;
                    border-radius: 12px;
                }
                QFrame#activityCard:hover{
                    border: 1px solid rgba(245,158,11,0.45);
                }
            """)



    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self._disabled:
            return
        self.clicked.emit(self.activity)



class ActivitySignupPage(QWidget):
    """
    活動報名頁（改成 HTML demo 流程）：
    Step 1. 上方：先選擇活動（卡片清單）
    Step 2. 下方：左人員 / 右方案（未選活動前全部鎖住）
    """
    request_back_to_manage = pyqtSignal()
    request_close = pyqtSignal()

    def __init__(self, controller, parent=None, operator_name: str = "", user_role: str = ""):
        super().__init__(parent)
        self.controller = controller
        self.operator_name = (operator_name or "").strip()
        self.user_role = (user_role or "").strip()
        self.activity_data = None            # 目前選中的活動 dict
        self._activity_list = []             # 所有活動（list[dict]）
        self._activity_cards = []            # list[_ActivityCard]
        self._signup_rows_all = []           # 右側已報名明細（未過濾）

        self._build_ui()
        self._load_activities()

        # 預設：鎖住報名區
        self._lock_signup_area(True)

        self._wire_person_panel()

    # =========================
    # 左下：人員面板接線（搜尋 / 顯示結果）
    # =========================
    def _wire_person_panel(self):
        """把 ActivityPersonPanel 的搜尋事件接到 controller。"""
        if not hasattr(self, "person_panel"):
            return

        # ActivityPersonPanel 建議提供：search_requested = pyqtSignal(str)
        if hasattr(self.person_panel, "search_requested"):
            try:
                self.person_panel.search_requested.connect(self._on_person_search_requested)
            except Exception:
                pass
        if hasattr(self.person_panel, "person_picked"):
            try:
                self.person_panel.person_picked.connect(self._on_person_picked)
            except Exception:
                pass

    def _on_person_search_requested(self, keyword: str):
        """左下搜尋：呼叫 controller.search_people_unified_dedup_name_birthday → 回填到 person_panel.show_search_results。"""
        kw = (keyword or "").strip()

        # 空字串：清空結果（如果 panel 支援）
        if not kw:
            if hasattr(self.person_panel, "show_search_results"):
                self.person_panel.show_search_results([])
            return

        try:
            people = self.controller.search_people_unified_dedup_name_birthday(kw)
        except Exception as e:
            QMessageBox.warning(self, "搜尋失敗", f"搜尋人員資料時發生錯誤：\n{e}")
            people = []

        # 兼容：確保 UI 端至少拿得到 phone_mobile
        normalized = []
        for p in (people or []):
            if not isinstance(p, dict):
                continue
            if not p.get("phone_mobile"):
                p["phone_mobile"] = p.get("phone") or p.get("phone_home") or ""
            normalized.append(p)

        if hasattr(self.person_panel, "show_search_results"):
            self.person_panel.show_search_results(normalized)
        else:
            QMessageBox.information(self, "尚未支援", "ActivityPersonPanel 尚未提供 show_search_results(people)")

    def _on_person_picked(self, person: dict):
        # 搜尋點到任一人：改為彈窗整戶報名（統一確認後一次存入）
        if not self.activity_data or not self.activity_data.get("id"):
            QMessageBox.information(self, "請先選活動", "請先選擇活動，再進行整戶報名")
            return

        person_id = (person or {}).get("id")
        if not person_id:
            QMessageBox.warning(self, "資料錯誤", "找不到人員 ID，無法載入整戶")
            return

        try:
            household_people = self.controller.get_household_people_by_person_id(person_id, status="ACTIVE")
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取整戶人員資料時發生錯誤：\n{e}")
            return

        if not household_people:
            household_people = [person]

        activity_id = self.activity_data.get("id")
        activity_title = (self.activity_data.get("title") or self.activity_data.get("name") or "未命名活動").strip()
        dlg = ActivityHouseholdSignupDialog(
            controller=self.controller,
            activity_id=activity_id,
            activity_title=activity_title,
            people=household_people,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        signup_requests = dlg.get_signup_requests()
        if not signup_requests:
            return

        success = []
        failed = []
        for req in signup_requests:
            p = req.get("person") or {}
            pid = (p.get("id") or "").strip()
            pname = (p.get("name") or pid).strip()
            plans = req.get("selected_plans") or []
            note = req.get("note")
            try:
                old_signup_id = (self.controller.get_activity_signup_id_by_person(activity_id, pid) or "").strip()
                if old_signup_id:
                    self.controller.delete_activity_signup(old_signup_id)
                self.controller.create_activity_signup(
                    activity_id=activity_id,
                    person_id=pid,
                    selected_plans=plans,
                    note=note,
                )
                success.append(pname)
            except Exception as e:
                failed.append(f"{pname}：{e}")

        msg = f"整戶報名完成\n成功：{len(success)} 人"
        if failed:
            msg += f"\n失敗：{len(failed)} 人\n\n" + "\n".join(failed[:8])
        QMessageBox.information(self, "報名結果", msg)
        self._refresh_signup_stats()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # =========================
        # 上方：活動選擇（第一步）
        # =========================
        top_group = QGroupBox("")
        top_layout = QVBoxLayout(top_group)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(8)

        # 第一列：標題 + badge + 清除
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        lbl_title = QLabel("活動報名")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 900;")

        self.lbl_activity_badge = QLabel("目前活動：未選擇")
        self.lbl_activity_badge.setStyleSheet("""
            QLabel{
                padding: 6px 10px;
                border-radius: 14px;
                background: rgba(245,158,11,0.14);
                border: 1px solid rgba(245,158,11,0.35);
                color: #7a4a00;
                font-weight: 800;
                font-size: 13px;
            }
        """)

        self.btn_clear_activity = QPushButton("清除活動選擇")
        self.btn_clear_activity.clicked.connect(self._clear_selected_activity)
        self.btn_clear_activity.setFixedHeight(34)

        row1.addWidget(lbl_title)
        row1.addWidget(self.lbl_activity_badge)
        row1.addStretch(1)
        row1.addWidget(self.btn_clear_activity)

        top_layout.addLayout(row1)

        # 活動卡片區（Scroll + Grid）
        self.activity_scroll = QScrollArea()
        self.activity_scroll.setWidgetResizable(True)
        self.activity_scroll.setFrameShape(QFrame.NoFrame)
        self.activity_scroll.setMinimumHeight(100)

        self.activity_scroll_content = QWidget()
        self.activity_grid = QGridLayout(self.activity_scroll_content)
        self.activity_grid.setContentsMargins(0, 0, 0, 0)
        self.activity_grid.setHorizontalSpacing(10)
        self.activity_grid.setVerticalSpacing(10)

        self.activity_scroll.setWidget(self.activity_scroll_content)
        top_layout.addWidget(self.activity_scroll)

        root.addWidget(top_group, 1)

        # =========================
        # 下方：左右 splitter（第二步以後）
        # =========================
        self.signup_group = QGroupBox("")
        main_layout = QVBoxLayout(self.signup_group)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)

        # ---- 左：搜尋列 + 搜尋結果 + 人員資料 ----
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self.person_panel = ActivityPersonPanel()
        left_layout.addWidget(self.person_panel, 1)

        splitter.addWidget(left_container)

        # ---- 右：報名統計與明細 ----
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.signup_stat_card = QFrame()
        self.signup_stat_card.setStyleSheet(
            "QFrame { background:#FFF8EE; border:1px solid #F0D9C4; border-radius:10px; }"
        )
        stat_layout = QHBoxLayout(self.signup_stat_card)
        stat_layout.setContentsMargins(12, 8, 12, 8)
        stat_layout.setSpacing(14)
        self.lbl_signup_count = QLabel("已報名：0 人")
        self.lbl_signup_amount = QLabel("報名總額：0 元")
        self.lbl_signup_donation = QLabel("隨喜金額：0 元")
        for w in (self.lbl_signup_count, self.lbl_signup_amount, self.lbl_signup_donation):
            w.setStyleSheet("font-weight:700; color:#5A4A3F;")
            stat_layout.addWidget(w)
        stat_layout.addStretch(1)
        right_layout.addWidget(self.signup_stat_card, 0)

        search_row = QHBoxLayout()
        self.edt_signup_search = QLineEdit()
        self.edt_signup_search.setPlaceholderText("搜尋姓名 / 電話")
        self.btn_signup_search_clear = QPushButton("清空")
        self.btn_signup_search_clear.setMinimumHeight(30)
        self.edt_signup_search.textChanged.connect(self._apply_signup_detail_filter)
        self.btn_signup_search_clear.clicked.connect(lambda: self.edt_signup_search.setText(""))
        search_row.addWidget(self.edt_signup_search, 1)
        search_row.addWidget(self.btn_signup_search_clear, 0)
        right_layout.addLayout(search_row)

        self.tbl_signup_detail = QTableWidget(0, 7)
        self.tbl_signup_detail.setHorizontalHeaderLabels(["勾選", "類型", "姓名", "電話", "方案摘要", "金額", "收據號"])
        self.tbl_signup_detail.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_signup_detail.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_signup_detail.verticalHeader().setVisible(False)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tbl_signup_detail.setStyleSheet(
            """
            QTableWidget::item:selected {
                background: #D9ECFF;
                color: #1F2937;
                border: 1px solid #8CB8E8;
            }
            """
        )
        self.tbl_signup_detail.itemSelectionChanged.connect(self._update_signup_action_buttons)
        self.tbl_signup_detail.itemChanged.connect(self._sync_mark_paid_enabled)
        right_layout.addWidget(self.tbl_signup_detail, 1)

        signup_btn_row = QHBoxLayout()
        signup_btn_row.addStretch(1)
        self.btn_signup_edit = QPushButton("修改報名")
        self.btn_signup_append = QPushButton("追加報名")
        self.btn_signup_delete = QPushButton("刪除報名")
        self.btn_signup_edit.setMinimumHeight(32)
        self.btn_signup_append.setMinimumHeight(32)
        self.btn_signup_delete.setMinimumHeight(32)
        self.btn_signup_edit.setEnabled(False)
        self.btn_signup_append.setEnabled(False)
        self.btn_signup_delete.setEnabled(False)
        self.btn_signup_edit.clicked.connect(self._on_edit_signup_clicked)
        self.btn_signup_append.clicked.connect(self._on_append_signup_clicked)
        self.btn_signup_delete.clicked.connect(self._on_delete_signup_clicked)
        signup_btn_row.addWidget(self.btn_signup_edit)
        signup_btn_row.addWidget(self.btn_signup_append)
        signup_btn_row.addWidget(self.btn_signup_delete)
        right_layout.addLayout(signup_btn_row)

        signup_pay_row = QHBoxLayout()
        self.btn_signup_pay_clear = QPushButton("清除")
        self.btn_signup_mark_paid = QPushButton("按此繳費")
        self.lbl_signup_payment_handler = QLabel("經手人")
        self.edt_signup_payment_handler = QLineEdit()
        self.edt_signup_payment_handler.setPlaceholderText("經手人（必填）")
        if self.operator_name:
            self.edt_signup_payment_handler.setText(self.operator_name)
        self._apply_signup_payment_handler_permissions()
        self.btn_signup_mark_paid.setEnabled(False)
        self.btn_signup_pay_clear.clicked.connect(self._clear_signup_payment_checks)
        self.btn_signup_mark_paid.clicked.connect(self._on_mark_signup_paid)
        self.edt_signup_payment_handler.textChanged.connect(self._sync_mark_paid_enabled)
        signup_pay_row.addWidget(self.btn_signup_pay_clear)
        signup_pay_row.addWidget(self.btn_signup_mark_paid)
        signup_pay_row.addWidget(self.lbl_signup_payment_handler)
        signup_pay_row.addWidget(self.edt_signup_payment_handler, 1)
        right_layout.addLayout(signup_pay_row)

        splitter.addWidget(right_container)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([420, 980])

        main_layout.addWidget(splitter, 1)
        root.addWidget(self.signup_group, 4)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch(1)
        self.btn_close_back = QPushButton("關閉返回")
        self.btn_close_back.setMinimumHeight(34)
        self.btn_close_back.clicked.connect(self.request_close.emit)
        bottom_row.addWidget(self.btn_close_back)
        root.addLayout(bottom_row)

    def set_default_payment_handler(self, username: str):
        self.operator_name = (username or "").strip()
        if not hasattr(self, "edt_signup_payment_handler"):
            return
        if (self.edt_signup_payment_handler.text() or "").strip():
            return
        if self.operator_name:
            self.edt_signup_payment_handler.setText(self.operator_name)

    def set_current_user_role(self, role: str):
        self.user_role = (role or "").strip()
        self._apply_signup_payment_handler_permissions()

    def _can_edit_signup_payment_handler(self) -> bool:
        return (self.user_role or "").strip() in {"管理員", "管理者", "會計", "會計人員"}

    def _apply_signup_payment_handler_permissions(self):
        if not hasattr(self, "edt_signup_payment_handler"):
            return
        editable = self._can_edit_signup_payment_handler()
        self.edt_signup_payment_handler.setReadOnly(not editable)
        if editable:
            self.edt_signup_payment_handler.setToolTip("")
        else:
            self.edt_signup_payment_handler.setToolTip("僅管理員與會計可修改經手人")

    def _refresh_signup_stats(self):
        if not self.activity_data or not self.activity_data.get("id"):
            self.lbl_signup_count.setText("已報名：0 人")
            self.lbl_signup_amount.setText("報名總額：0 元")
            self.lbl_signup_donation.setText("隨喜金額：0 元")
            self._signup_rows_all = []
            self.tbl_signup_detail.setRowCount(0)
            self._update_signup_action_buttons()
            self._sync_mark_paid_enabled()
            return
        try:
            rows = self.controller.get_activity_signups(self.activity_data.get("id"))
        except Exception:
            rows = []
        count = len(rows or [])
        total = sum(int((r or {}).get("total_amount", 0) or 0) for r in (rows or []))
        donation = sum(int((r or {}).get("donation_amount", 0) or 0) for r in (rows or []))
        self.lbl_signup_count.setText(f"已報名：{count} 人")
        self.lbl_signup_amount.setText(f"報名總額：{total} 元")
        self.lbl_signup_donation.setText(f"隨喜金額：{donation} 元")
        self._signup_rows_all = list(rows or [])
        self._apply_signup_detail_filter()

    def _apply_signup_detail_filter(self):
        kw = (self.edt_signup_search.text() or "").strip().lower() if hasattr(self, "edt_signup_search") else ""
        rows = self._signup_rows_all or []
        if kw:
            rows = [
                r for r in rows
                if kw in str((r or {}).get("person_name", "")).lower()
                or kw in str((r or {}).get("person_phone", "")).lower()
            ]
        self.tbl_signup_detail.setRowCount(0)
        self._signup_group_color_cache = {}
        self._signup_group_color_next_idx = 0
        kind_label_map = {"INITIAL": "初始", "APPEND": "追加"}
        for r in rows:
            row = self.tbl_signup_detail.rowCount()
            self.tbl_signup_detail.insertRow(row)
            is_paid = int((r or {}).get("is_paid", 0) or 0) == 1
            signup_kind = str((r or {}).get("signup_kind", "INITIAL") or "INITIAL").strip().upper()
            group_id = str((r or {}).get("group_id", "") or (r or {}).get("signup_id", "") or "")
            check_item = QTableWidgetItem("")
            if is_paid:
                check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                check_item.setCheckState(Qt.Checked)
            else:
                check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                check_item.setCheckState(Qt.Unchecked)
            self.tbl_signup_detail.setItem(row, 0, check_item)
            self.tbl_signup_detail.setItem(row, 1, QTableWidgetItem(kind_label_map.get(signup_kind, signup_kind)))
            name_item = QTableWidgetItem(str((r or {}).get("person_name", "") or ""))
            name_item.setData(Qt.UserRole + 2, {
                "signup_id": str((r or {}).get("signup_id", "") or ""),
                "person_id": str((r or {}).get("person_id", "") or ""),
                "is_paid": is_paid,
                "signup_kind": signup_kind,
                "group_id": group_id,
            })
            self.tbl_signup_detail.setItem(row, 2, name_item)
            self.tbl_signup_detail.setItem(row, 3, QTableWidgetItem(str((r or {}).get("person_phone", "") or "")))
            self.tbl_signup_detail.setItem(row, 4, QTableWidgetItem(str((r or {}).get("plan_summary", "") or "")))
            self.tbl_signup_detail.setItem(row, 5, QTableWidgetItem(str((r or {}).get("total_amount", 0) or 0)))
            self.tbl_signup_detail.setItem(row, 6, QTableWidgetItem(str((r or {}).get("payment_receipt_number", "") or "")))
            sid = str((r or {}).get("signup_id", "") or "")
            for c in range(7):
                it = self.tbl_signup_detail.item(row, c)
                if it:
                    it.setData(Qt.UserRole, sid)
                    it.setData(Qt.UserRole + 1, 1 if is_paid else 0)
            if is_paid:
                receipt_no = str((r or {}).get("payment_receipt_number", "") or "")
                if receipt_no:
                    self.tbl_signup_detail.item(row, 6).setToolTip(f"已繳費，收據號碼：{receipt_no}")
            self._apply_signup_group_row_style(row, group_id)
        self._update_signup_action_buttons()
        self._sync_mark_paid_enabled()

    def _get_selected_signup_id(self) -> str:
        row = self.tbl_signup_detail.currentRow()
        if row < 0:
            return ""
        it = self.tbl_signup_detail.item(row, 0)
        if not it:
            return ""
        return str(it.data(Qt.UserRole) or "").strip()

    def _selected_signup_is_paid(self) -> bool:
        row = self.tbl_signup_detail.currentRow()
        if row < 0:
            return False
        it = self.tbl_signup_detail.item(row, 0)
        if not it:
            return False
        return int(it.data(Qt.UserRole + 1) or 0) == 1

    def _get_selected_signup_meta(self) -> dict:
        row = self.tbl_signup_detail.currentRow()
        if row < 0:
            return {}
        it = self.tbl_signup_detail.item(row, 2)
        data = it.data(Qt.UserRole + 2) if it else None
        return data if isinstance(data, dict) else {}

    def _update_signup_action_buttons(self):
        meta = self._get_selected_signup_meta()
        sid = str((meta or {}).get("signup_id") or "").strip()
        is_paid = bool((meta or {}).get("is_paid"))
        self.btn_signup_edit.setEnabled(bool(sid))
        self.btn_signup_append.setEnabled(bool(sid) and is_paid)
        self.btn_signup_delete.setEnabled(bool(sid))
        self.btn_signup_edit.setToolTip("")

    def _signup_group_color(self, group_id: str):
        gid = str(group_id or "").strip()
        if not gid:
            return None
        from PyQt5.QtGui import QColor
        palette = ["#FFFFFF", "#FFF3E3"]
        if not hasattr(self, "_signup_group_color_cache"):
            self._signup_group_color_cache = {}
            self._signup_group_color_next_idx = 0
        if gid not in self._signup_group_color_cache:
            idx = int(getattr(self, "_signup_group_color_next_idx", 0)) % len(palette)
            self._signup_group_color_cache[gid] = palette[idx]
            self._signup_group_color_next_idx = int(getattr(self, "_signup_group_color_next_idx", 0)) + 1
        return QColor(self._signup_group_color_cache[gid])

    def _apply_signup_group_row_style(self, row_idx: int, group_id: str):
        color = self._signup_group_color(group_id)
        if color is None:
            return
        for c in range(self.tbl_signup_detail.columnCount()):
            it = self.tbl_signup_detail.item(row_idx, c)
            if it:
                it.setBackground(color)

    def _get_checked_signup_ids(self) -> list:
        ids = []
        for row in range(self.tbl_signup_detail.rowCount()):
            item = self.tbl_signup_detail.item(row, 0)
            if not item:
                continue
            if int(item.data(Qt.UserRole + 1) or 0) == 1:
                continue
            if item.checkState() != Qt.Checked:
                continue
            sid = str(item.data(Qt.UserRole) or "").strip()
            if sid:
                ids.append(sid)
        return ids

    def _clear_signup_payment_checks(self):
        for row in range(self.tbl_signup_detail.rowCount()):
            item = self.tbl_signup_detail.item(row, 0)
            if not item:
                continue
            if int(item.data(Qt.UserRole + 1) or 0) == 1:
                continue
            item.setCheckState(Qt.Unchecked)
        self._sync_mark_paid_enabled()

    def _sync_mark_paid_enabled(self, *_args):
        handler_ok = bool((self.edt_signup_payment_handler.text() or "").strip()) if hasattr(self, "edt_signup_payment_handler") else False
        has_checked = bool(self._get_checked_signup_ids()) if hasattr(self, "tbl_signup_detail") else False
        if hasattr(self, "btn_signup_mark_paid"):
            self.btn_signup_mark_paid.setEnabled(handler_ok and has_checked)

    def _on_mark_signup_paid(self):
        if not self.activity_data or not self.activity_data.get("id"):
            QMessageBox.information(self, "請先選擇活動", "請先選擇活動再進行繳費。")
            return
        signup_ids = self._get_checked_signup_ids()
        if not signup_ids:
            QMessageBox.information(self, "請先勾選", "請先勾選要繳費的報名明細。")
            return
        handler = (self.edt_signup_payment_handler.text() or "").strip()
        if not handler:
            QMessageBox.information(self, "欄位不足", "請先輸入經手人。")
            return
        try:
            result = self.controller.mark_activity_signups_paid(
                str(self.activity_data.get("id") or ""),
                signup_ids,
                handler=handler,
            )
        except Exception as e:
            QMessageBox.warning(self, "繳費失敗", str(e))
            return
        self._refresh_signup_stats()
        paid_count = int((result or {}).get("paid_count", 0) or 0)
        skipped_count = int((result or {}).get("skipped_count", 0) or 0)
        msg = [f"完成繳費：{paid_count} 筆"]
        if skipped_count > 0:
            msg.append(f"略過已繳費：{skipped_count} 筆")
        receipts = (result or {}).get("receipt_numbers") or []
        if receipts:
            msg.append("收據號碼：" + "、".join(str(x) for x in receipts[:10]))
        QMessageBox.information(self, "繳費完成", "\n".join(msg))

    def _on_edit_signup_clicked(self):
        sid = self._get_selected_signup_id()
        if not sid:
            QMessageBox.information(self, "請先選擇", "請先在右側已報名明細選擇一筆資料")
            return
        is_paid = self._selected_signup_is_paid()
        if is_paid:
            QMessageBox.information(
                self,
                "已繳費報名限制",
                "已繳費的報名無法修改，要增加請用追加報名，要改品項請先刪除再重新報名",
            )
            return
        payment_handler = (self.edt_signup_payment_handler.text() or "").strip() if hasattr(self, "edt_signup_payment_handler") else ""
        dlg = ActivitySignupEditDialog(
            self.controller,
            sid,
            self,
            is_paid=False,
            payment_handler=payment_handler,
        )
        if dlg.exec_() == QDialog.Accepted:
            self._refresh_signup_stats()

    def _on_append_signup_clicked(self):
        meta = self._get_selected_signup_meta()
        sid = str((meta or {}).get("signup_id") or "").strip()
        pid = str((meta or {}).get("person_id") or "").strip()
        is_paid = bool((meta or {}).get("is_paid"))
        if not sid or not pid:
            QMessageBox.information(self, "請先選擇", "請先在右側已報名明細選擇一筆資料")
            return
        if not is_paid:
            QMessageBox.information(self, "不適用", "未繳費紀錄請使用「修改報名」。")
            return
        if not self.activity_data or not self.activity_data.get("id"):
            QMessageBox.information(self, "請先選擇活動", "請先選擇活動。")
            return
        try:
            household_people = self.controller.get_household_people_by_person_id(pid, status="ACTIVE")
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取人員資料時發生錯誤：\n{e}")
            return
        person = next((p for p in (household_people or []) if str(p.get("id") or "").strip() == pid), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該報名人員資料。")
            return
        activity_id = self.activity_data.get("id")
        activity_title = (self.activity_data.get("title") or self.activity_data.get("name") or "未命名活動").strip()
        dlg = ActivityHouseholdSignupDialog(
            controller=self.controller,
            activity_id=activity_id,
            activity_title=activity_title,
            people=[person],
            prefill_existing=False,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        reqs = dlg.get_signup_requests() or []
        if not reqs:
            return
        req = reqs[0] or {}
        plans = req.get("selected_plans") or []
        note = req.get("note")
        if not plans:
            QMessageBox.information(self, "未儲存", "請至少選擇一個方案。")
            return
        ok = QMessageBox.question(
            self,
            "確認追加報名",
            "將新增一筆「追加」活動報名紀錄（原已繳費紀錄不變）。\n\n是否繼續？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ok != QMessageBox.Yes:
            return
        try:
            result = self.controller.create_activity_signup_append(activity_id, pid, plans, note=note)
        except Exception as e:
            QMessageBox.critical(self, "追加失敗", f"追加報名失敗：\n{e}")
            return
        kind_text = "追加" if str((result or {}).get("signup_kind") or "").upper() == "APPEND" else "初始"
        self._refresh_signup_stats()
        QMessageBox.information(self, "完成", f"已新增一筆「{kind_text}」報名紀錄。")

    def _on_delete_signup_clicked(self):
        sid = self._get_selected_signup_id()
        if not sid:
            QMessageBox.information(self, "請先選擇", "請先在右側已報名明細選擇一筆資料")
            return
        is_paid = self._selected_signup_is_paid()
        row = self.tbl_signup_detail.currentRow()
        name = self.tbl_signup_detail.item(row, 2).text() if row >= 0 and self.tbl_signup_detail.item(row, 2) else ""
        phone = self.tbl_signup_detail.item(row, 3).text() if row >= 0 and self.tbl_signup_detail.item(row, 3) else ""
        msg = ("此筆已繳費，將刪除當前選取報名紀錄，並將收支交易標記為作廢。\n\n" if is_paid else "") + f"確定要刪除這筆報名？\n\n姓名：{name}\n電話：{phone}"
        ok = QMessageBox.question(self, "確認刪除報名", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        try:
            deleted = self.controller.delete_activity_signup_with_void_transactions(sid)
        except Exception as e:
            QMessageBox.critical(self, "刪除失敗", f"刪除報名失敗：\n{e}")
            return
        if not deleted:
            QMessageBox.warning(self, "刪除失敗", "此筆報名不存在或已被刪除")
            return
        self._refresh_signup_stats()
        QMessageBox.information(self, "已刪除", "報名資料已刪除")

    # =========================
    # 活動：載入 / 卡片渲染 / 選取
    # =========================
    def _load_activities(self):
        try:
            activities = self.controller.list_activities_for_signup()
        except Exception:
            activities = []

        self._activity_list = activities or []
        self._render_activity_cards(self._activity_list)

        has_any = bool(self._activity_list)
        self.btn_clear_activity.setEnabled(has_any)

        # 沒有活動：維持 Step0 狀態
        if not has_any:
            self.set_activity({})


    def _render_activity_cards(self, activities: list):
        # 清空 grid
        while self.activity_grid.count():
            item = self.activity_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._activity_cards = []

        if not activities:
            empty = QLabel("（目前沒有可選活動）")
            empty.setStyleSheet("color:#666666; padding: 10px;")
            self.activity_grid.addWidget(empty, 0, 0, 1, 1)
            return

        # 4 欄的卡片排列（寬度不夠時 Qt 也會擠，但可接受；你也可以後續做 resizeEvent 動態欄數）
        cols = 4
        r = 0
        c = 0
        for a in activities:
            card = _ActivityCard(a)
            card.clicked.connect(self._on_activity_card_clicked)
            self._activity_cards.append(card)

            self.activity_grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self.activity_grid.setRowStretch(r + 1, 1)

    def _on_activity_card_clicked(self, activity: dict):
        if not activity:
            return

        if activity.get("is_open") is False:
            QMessageBox.information(self, "此活動不可報名", "此活動目前狀態為「已結束」，無法新增報名。")
            return

        self.set_activity(activity)


    def _clear_selected_activity(self):
        for c in self._activity_cards:
            c.set_selected(False)

        self.set_activity({})

        # 若列表為空，順手 disable
        self.btn_clear_activity.setEnabled(bool(self._activity_list))


    # =========================
    # Lock / Unlock 報名區
    # =========================
    def _lock_signup_area(self, locked: bool):
        # locked=True → disable 整個報名工作區
        self.signup_group.setEnabled(not locked)

    def _pick_person(self, person: dict):
        if hasattr(self.person_panel, "set_person_data"):
            self.person_panel.set_person_data(person)
        else:
            QMessageBox.information(
                self, "需要接線",
                "ActivityPersonPanel 尚未提供 set_person_data(person: dict) 方法。\n"
                "請在 ActivityPersonPanel 實作後再呼叫帶入。"
            )

    # =========================
    # Public API
    # =========================
    def set_activity(self, activity_data: dict):
        """
        - activity_data={} 表示未選擇（回到 Step0）
        - activity_data 有值：選定活動 → 解鎖 → 載入方案
        """
        self.activity_data = activity_data or {}

        # 更新 badge
        if not self.activity_data:
            self.lbl_activity_badge.setText("目前活動：未選擇")
            self._lock_signup_area(True)
            self._refresh_signup_stats()
            return

        title = (self.activity_data.get("title") or self.activity_data.get("name") or "未命名活動").strip()
        code = (self.activity_data.get("code") or self.activity_data.get("id") or "").strip()
        self.lbl_activity_badge.setText(f"目前活動：{title}（{code}）" if code else f"目前活動：{title}")

        # 卡片選取樣式同步
        selected_id = self.activity_data.get("id")
        for c in self._activity_cards:
            is_sel = (c.activity.get("id") == selected_id)
            c.set_selected(is_sel)

        # 解鎖報名區
        self._lock_signup_area(False)
        self._refresh_signup_stats()
    
    def showEvent(self, event):
        super().showEvent(event)
        # 每次這個頁面「顯示出來」就重載活動卡片
        self.reload_activities()

    def reload_activities(self, keep_selected: bool = True):
        prev_id = self.activity_data.get("id") if (keep_selected and self.activity_data) else None

        self._load_activities()

        # 重新選回之前選的活動（如果還存在）
        if prev_id:
            for a in self._activity_list:
                if a.get("id") == prev_id:
                    self.set_activity(a)
                    break

    def _on_save_clicked(self):
        QMessageBox.information(self, "提示", "主頁已取消方案編輯，請由整戶彈窗統一存入。")
                
  
