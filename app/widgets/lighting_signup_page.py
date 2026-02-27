from datetime import date

from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFrame, QLineEdit, QSplitter, QMessageBox, QDialog
)

from app.dialogs.lighting_household_signup_dialog import LightingHouseholdSignupDialog
from app.utils.print_helper import PrintHelper


class LightingSignupPage(QWidget):
    request_close = pyqtSignal()

    """
    安燈報名頁面（QWidget）：
    - 左側：參加人員搜尋（點選後彈整戶安燈報名）
    - 右側：已報名明細 / 燈別總額 / 繳費
    """

    def __init__(self, controller, parent=None, operator_name: str = "", user_role: str = ""):
        super().__init__(parent)
        self.controller = controller
        self.operator_name = (operator_name or "").strip()
        self.user_role = (user_role or "").strip()
        self._build_ui()
        self.refresh_suggestions()
        self.load_active_items()
        self._reload_signup_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("安燈報名")
        title.setStyleSheet("font-weight: 900;")
        root.addWidget(title)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("年度"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.year_spin.setValue(date.today().year)
        self.year_spin.valueChanged.connect(lambda _v: self.refresh_suggestions())
        top_row.addWidget(self.year_spin)
        self.btn_year_dec = QPushButton("▼")
        self.btn_year_inc = QPushButton("▲")
        self.btn_year_dec.setFixedSize(22, 14)
        self.btn_year_inc.setFixedSize(22, 14)
        for b in (self.btn_year_inc, self.btn_year_dec):
            b.setStyleSheet(
                """
                QPushButton {
                    background: #F4ECE3;
                    border: 1px solid #D8C2AA;
                    border-radius: 0px;
                    padding: 0px;
                    color: #5A3D29;
                    font-weight: 800;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #EEDFCC;
                    border: 1px solid #CFAE8D;
                }
                QPushButton:pressed {
                    background: #E6D0B6;
                }
                """
            )
        self.btn_year_dec.clicked.connect(self.year_spin.stepDown)
        self.btn_year_inc.clicked.connect(self.year_spin.stepUp)
        year_btn_col = QVBoxLayout()
        year_btn_col.setContentsMargins(0, 0, 0, 0)
        year_btn_col.setSpacing(0)
        year_btn_col.addWidget(self.btn_year_inc)
        year_btn_col.addWidget(self.btn_year_dec)
        top_row.addLayout(year_btn_col)

        self.btn_refresh = QPushButton("重新載入設定")
        self.btn_refresh.clicked.connect(self._reload_all)
        top_row.addWidget(self.btn_refresh)
        top_row.addStretch(1)

        self.lbl_operator = QLabel(f"目前經手人預設：{self.operator_name or '（未取得）'}")
        self.lbl_operator.setStyleSheet("color:#6B7280;")
        top_row.addWidget(self.lbl_operator)
        root.addLayout(top_row)

        hint_frame = QFrame()
        hint_layout = QVBoxLayout(hint_frame)
        hint_layout.setContentsMargins(8, 8, 8, 8)
        hint_layout.setSpacing(6)

        self.lbl_hint_meta = QLabel("")
        self.lbl_hint_meta.setWordWrap(True)
        self.lbl_hint_meta.setStyleSheet("color:#6B7280;")
        hint_layout.addWidget(self.lbl_hint_meta)

        hint_row_2col = QHBoxLayout()
        hint_row_2col.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("犯太歲提示"))
        self.txt_tai_sui_hint = QTextEdit()
        self.txt_tai_sui_hint.setReadOnly(True)
        self.txt_tai_sui_hint.setMaximumHeight(56)
        left_col.addWidget(self.txt_tai_sui_hint)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("祭改提示"))
        self.txt_ji_gai_hint = QTextEdit()
        self.txt_ji_gai_hint.setReadOnly(True)
        self.txt_ji_gai_hint.setMaximumHeight(56)
        right_col.addWidget(self.txt_ji_gai_hint)

        hint_row_2col.addLayout(left_col, 1)
        hint_row_2col.addLayout(right_col, 1)
        hint_layout.addLayout(hint_row_2col)
        root.addWidget(hint_frame)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setChildrenCollapsible(False)

        left_wrap = QWidget()
        left_layout = QVBoxLayout(left_wrap)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("參加人員資料（搜尋後點選任一人，彈出整戶安燈報名）"))

        search_row = QHBoxLayout()
        self.edt_people_search = QLineEdit()
        self.edt_people_search.setPlaceholderText("輸入姓名或電話")
        self.btn_people_search = QPushButton("搜尋")
        self.btn_people_clear = QPushButton("清空")
        search_row.addWidget(self.edt_people_search, 1)
        search_row.addWidget(self.btn_people_search)
        search_row.addWidget(self.btn_people_clear)
        left_layout.addLayout(search_row)

        self.tbl_people_search = QTableWidget(0, 7)
        self.tbl_people_search.setHorizontalHeaderLabels(["姓名", "電話", "國曆生日", "農曆生日", "生肖", "地址", "戶別"])
        self.tbl_people_search.setWordWrap(True)
        self.tbl_people_search.setTextElideMode(Qt.ElideNone)
        self.tbl_people_search.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_people_search.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tbl_people_search.horizontalHeader().setStretchLastSection(False)
        for c in range(self.tbl_people_search.columnCount()):
            self.tbl_people_search.horizontalHeader().setSectionResizeMode(c, QHeaderView.Interactive)
        self.tbl_people_search.setColumnWidth(0, 90)   # 姓名
        self.tbl_people_search.setColumnWidth(1, 120)  # 電話
        self.tbl_people_search.setColumnWidth(2, 110)  # 國曆生日
        self.tbl_people_search.setColumnWidth(3, 110)  # 農曆生日
        self.tbl_people_search.setColumnWidth(4, 70)   # 生肖
        self.tbl_people_search.setColumnWidth(5, 260)  # 地址
        self.tbl_people_search.setColumnWidth(6, 70)   # 戶別
        left_layout.addWidget(self.tbl_people_search, 1)

        right_wrap = QWidget()
        right_layout = QVBoxLayout(right_wrap)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("報名明細"))

        self.lighting_total_card = QFrame()
        self.lighting_total_card.setStyleSheet(
            "QFrame { background:#FFF8EE; border:1px solid #F0D9C4; border-radius:10px; }"
        )
        lighting_total_layout = QHBoxLayout(self.lighting_total_card)
        lighting_total_layout.setContentsMargins(12, 8, 12, 8)
        lighting_total_layout.setSpacing(10)
        lighting_total_col = QVBoxLayout()
        lighting_total_col.setContentsMargins(0, 0, 0, 0)
        lighting_total_col.setSpacing(4)
        self.lbl_lighting_grand_total = QLabel("總額：0 元")
        self.lbl_lighting_item_totals = QLabel("各燈別總額：0 元")
        self.lbl_lighting_grand_total.setStyleSheet("font-weight:700; color:#5A4A3F;")
        self.lbl_lighting_item_totals.setStyleSheet("font-weight:700; color:#5A4A3F;")
        self.lbl_lighting_item_totals.setWordWrap(True)
        lighting_total_col.addWidget(self.lbl_lighting_grand_total)
        lighting_total_col.addWidget(self.lbl_lighting_item_totals)
        lighting_total_layout.addLayout(lighting_total_col, 1)
        right_layout.addWidget(self.lighting_total_card, 0)

        right_search_row = QHBoxLayout()
        self.edt_signup_search = QLineEdit()
        self.edt_signup_search.setPlaceholderText("搜尋姓名 / 電話")
        self.edt_signup_search.setMaximumWidth(260)
        self.btn_show_all = QPushButton("全部")
        self.btn_show_unpaid = QPushButton("篩選未繳費")
        self.btn_clear_signup_search = QPushButton("清空")
        right_search_row.addWidget(QLabel("搜尋"))
        right_search_row.addWidget(self.edt_signup_search)
        right_search_row.addWidget(self.btn_show_all)
        right_search_row.addWidget(self.btn_show_unpaid)
        right_search_row.addWidget(self.btn_clear_signup_search)
        right_search_row.addStretch(1)
        right_layout.addLayout(right_search_row)

        self.tbl_signups = QTableWidget(0, 8)
        self.tbl_signups.setHorizontalHeaderLabels(["勾選", "類型", "收據號", "姓名", "電話", "燈別摘要", "金額", "繳費"])
        self.tbl_signups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tbl_signups.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_signups.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_signups.setStyleSheet(
            """
            QTableWidget::item:selected {
                background: #D9ECFF;
                color: #1F2937;
                border: 1px solid #8CB8E8;
            }
            """
        )
        self.tbl_signups.viewport().installEventFilter(self)
        right_layout.addWidget(self.tbl_signups, 1)

        detail_btn_row = QHBoxLayout()
        detail_btn_row.addStretch(1)
        self.btn_edit_signup = QPushButton("修改報名")
        self.btn_append_signup = QPushButton("追加報名")
        self.btn_delete_signup = QPushButton("刪除報名")
        self.btn_print_signup_list = QPushButton("列印名單")
        self.btn_edit_signup.setEnabled(False)
        self.btn_append_signup.setEnabled(False)
        self.btn_delete_signup.setEnabled(False)
        detail_btn_row.addWidget(self.btn_edit_signup)
        detail_btn_row.addWidget(self.btn_append_signup)
        detail_btn_row.addWidget(self.btn_delete_signup)
        detail_btn_row.addWidget(self.btn_print_signup_list)
        right_layout.addLayout(detail_btn_row)

        right_btn_row = QHBoxLayout()
        self.btn_clear_selection_rows = QPushButton("清除")
        self.edt_payment_handler = QLineEdit()
        self.edt_payment_handler.setPlaceholderText("經手人（必填）")
        if self.operator_name:
            self.edt_payment_handler.setText(self.operator_name)
        self._apply_payment_handler_permissions()
        self.btn_pay = QPushButton("按此繳費")
        right_btn_row.addWidget(self.btn_clear_selection_rows)
        right_btn_row.addWidget(self.btn_pay)
        right_btn_row.addWidget(QLabel("經手人"))
        right_btn_row.addWidget(self.edt_payment_handler, 1)
        right_layout.addLayout(right_btn_row)

        body_splitter.addWidget(left_wrap)
        body_splitter.addWidget(right_wrap)
        body_splitter.setStretchFactor(0, 5)
        body_splitter.setStretchFactor(1, 6)
        root.addWidget(body_splitter, 1)

        self.btn_people_search.clicked.connect(self._search_people)
        self.btn_people_clear.clicked.connect(self._clear_people_search)
        self.tbl_people_search.cellClicked.connect(self._on_people_search_row_clicked)
        self.edt_signup_search.textChanged.connect(lambda _t: self._reload_signup_list())
        self.btn_show_all.clicked.connect(self._on_show_all_signups)
        self.btn_show_unpaid.clicked.connect(self._on_show_unpaid_signups)
        self.btn_clear_signup_search.clicked.connect(lambda: self.edt_signup_search.setText(""))
        self.tbl_signups.itemSelectionChanged.connect(self._update_signup_action_buttons)
        self.btn_edit_signup.clicked.connect(self._on_edit_signup)
        self.btn_append_signup.clicked.connect(self._on_append_signup)
        self.btn_delete_signup.clicked.connect(self._on_delete_signup)
        self.btn_print_signup_list.clicked.connect(self._on_print_signup_list_by_item)
        self.btn_clear_selection_rows.clicked.connect(self._clear_signup_row_selection)
        self.btn_pay.clicked.connect(self._on_mark_paid)

        row_btn = QHBoxLayout()
        row_btn.addStretch(1)
        self.btn_close = QPushButton("關閉返回")
        self.btn_close.setMinimumHeight(34)
        self.btn_close.clicked.connect(self.request_close.emit)
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

    def _reload_all(self):
        self.refresh_suggestions()
        self.load_active_items()
        self._reload_signup_list()

    def refresh_suggestions(self):
        selected_year = int(self.year_spin.value())
        data = self.controller.get_lighting_hint_settings()
        saved_year_text = str(data.get("year") or "").strip()
        try:
            saved_year = int(saved_year_text)
        except Exception:
            saved_year = None

        # 年度一致：顯示安燈設定已儲存內容
        # 年度不一致：改用該年度自動抓取內容，避免顯示錯誤年度提示
        if saved_year == selected_year:
            show_tai_sui = str(data.get("tai_sui_text") or "")
            show_ji_gai = str(data.get("ji_gai_text") or "")
        else:
            defaults = self.controller._default_lighting_hint_texts(selected_year)
            show_tai_sui = str(defaults.get("tai_sui_text") or "")
            show_ji_gai = str(defaults.get("ji_gai_text") or "")
        self.lbl_hint_meta.setText(
            f"年度（本次報名）：{selected_year} 年"
        )
        self.txt_tai_sui_hint.setPlainText(show_tai_sui)
        self.txt_ji_gai_hint.setPlainText(show_ji_gai)

    def load_active_items(self):
        self._active_lighting_items = self.controller.list_lighting_items(include_inactive=False)

    def _can_edit_payment_handler(self) -> bool:
        return (self.user_role or "").strip() in {"管理員", "管理者", "會計", "會計人員"}

    def _apply_payment_handler_permissions(self):
        editable = self._can_edit_payment_handler()
        self.edt_payment_handler.setReadOnly(not editable)
        if editable:
            self.edt_payment_handler.setToolTip("")
        else:
            self.edt_payment_handler.setToolTip("僅管理員與會計可修改經手人")

    def _search_people(self):
        keyword = (self.edt_people_search.text() or "").strip()
        if not keyword:
            self.tbl_people_search.setRowCount(0)
            return
        rows = self.controller.search_people_unified(keyword)
        self.tbl_people_search.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.tbl_people_search.setItem(i, 0, QTableWidgetItem(str(row.get("name") or "")))
            self.tbl_people_search.setItem(i, 1, QTableWidgetItem(str(row.get("phone_mobile") or "")))
            self.tbl_people_search.setItem(i, 2, QTableWidgetItem(str(row.get("birthday_ad") or "")))
            self.tbl_people_search.setItem(i, 3, QTableWidgetItem(str(row.get("birthday_lunar") or "")))
            self.tbl_people_search.setItem(i, 4, QTableWidgetItem(str(row.get("zodiac") or "")))
            self.tbl_people_search.setItem(i, 5, QTableWidgetItem(str(row.get("address") or "")))
            self.tbl_people_search.setItem(i, 6, QTableWidgetItem("戶長" if str(row.get("role_in_household") or "") == "HEAD" else "戶員"))
            self.tbl_people_search.item(i, 0).setData(Qt.UserRole, str(row.get("id") or ""))
        self.tbl_people_search.resizeRowsToContents()

    def _on_people_search_row_clicked(self, row: int, _col: int):
        item = self.tbl_people_search.item(row, 0)
        person_id = str(item.data(Qt.UserRole) or "").strip() if item else ""
        if not person_id:
            QMessageBox.warning(self, "資料錯誤", "找不到人員 ID，無法載入整戶")
            return

        try:
            household_people = self.controller.get_household_people_by_person_id(person_id, status="ACTIVE")
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取整戶人員資料時發生錯誤：\n{e}")
            return

        if not household_people:
            QMessageBox.information(self, "查無資料", "找不到該人員整戶資料")
            return

        active_items = list(getattr(self, "_active_lighting_items", []) or [])
        if not active_items:
            QMessageBox.information(self, "無可用燈別", "目前沒有啟用中的可報名燈別")
            return

        person_ids = [str(p.get("id") or "").strip() for p in household_people if str(p.get("id") or "").strip()]
        try:
            selected_map = self.controller.get_lighting_signup_selected_item_ids(self.year_spin.value(), person_ids)
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取既有安燈勾選資料時發生錯誤：\n{e}")
            return

        dlg = LightingHouseholdSignupDialog(
            people=household_people,
            lighting_items=active_items,
            selected_by_person_id=selected_map,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        requests = dlg.get_signup_requests()
        if not requests:
            return

        success = []
        skipped = []
        failed = []
        for req in requests:
            person = req.get("person") or {}
            pid = str(person.get("id") or "").strip()
            pname = str(person.get("name") or pid).strip() or pid
            item_ids = req.get("lighting_item_ids") or []
            if not pid:
                failed.append("（無姓名）: 缺少 person_id")
                continue
            if not item_ids:
                skipped.append(pname)
                continue
            try:
                self.controller.upsert_lighting_signup(self.year_spin.value(), pid, item_ids)
                success.append(pname)
            except Exception as e:
                failed.append(f"{pname}：{e}")

        msg = f"整戶安燈報名完成\n成功：{len(success)} 人"
        if skipped:
            msg += f"\n未勾選（略過）：{len(skipped)} 人"
        if failed:
            msg += f"\n失敗：{len(failed)} 人\n\n" + "\n".join(failed[:8])
        QMessageBox.information(self, "報名結果", msg)
        self._reload_signup_list()

    def _clear_people_search(self):
        self.edt_people_search.setText("")
        self.tbl_people_search.setRowCount(0)

    def _on_show_all_signups(self):
        self._reload_signup_list(unpaid_only=False)

    def _on_show_unpaid_signups(self):
        self._reload_signup_list(unpaid_only=True)

    def eventFilter(self, obj, event):
        tbl = getattr(self, "tbl_signups", None)
        if tbl is not None and obj is tbl.viewport() and event.type() == QEvent.MouseButtonPress:
            idx = tbl.indexAt(event.pos())
            if not idx.isValid():
                tbl.clearSelection()
                tbl.setCurrentCell(-1, -1)
                self._update_signup_action_buttons()
        return super().eventFilter(obj, event)

    def _reload_signup_list(self, unpaid_only: bool = False):
        kw = (self.edt_signup_search.text() or "").strip() if hasattr(self, "edt_signup_search") else ""
        rows = self.controller.list_lighting_signups(self.year_spin.value(), keyword=kw, unpaid_only=unpaid_only)
        self.tbl_signups.setRowCount(len(rows))
        self._signup_group_color_cache = {}
        self._signup_group_color_next_idx = 0
        kind_label_map = {"INITIAL": "初始", "APPEND": "追加"}
        for i, row in enumerate(rows):
            is_paid = int(row.get("is_paid") or 0) == 1
            check_item = QTableWidgetItem("")
            if is_paid:
                check_item.setFlags(Qt.ItemIsEnabled)
                check_item.setCheckState(Qt.Checked)
            else:
                check_item.setFlags((check_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled))
                check_item.setCheckState(Qt.Unchecked)
            check_item.setData(Qt.UserRole, str(row.get("signup_id") or ""))
            self.tbl_signups.setItem(i, 0, check_item)
            signup_kind = str(row.get("signup_kind") or "INITIAL").strip().upper() or "INITIAL"
            group_id = str(row.get("group_id") or row.get("signup_id") or "").strip()
            self.tbl_signups.setItem(i, 1, QTableWidgetItem(kind_label_map.get(signup_kind, signup_kind)))
            receipt_no = str(row.get("payment_receipt_number") or "").strip()
            self.tbl_signups.setItem(i, 2, QTableWidgetItem(receipt_no))
            name_item = QTableWidgetItem(str(row.get("person_name") or ""))
            name_item.setData(Qt.UserRole, {
                "signup_id": str(row.get("signup_id") or ""),
                "person_id": str(row.get("person_id") or ""),
                "is_paid": is_paid,
                "total_amount": int(row.get("total_amount") or 0),
                "signup_kind": signup_kind,
                "group_id": group_id,
            })
            self.tbl_signups.setItem(i, 3, name_item)
            self.tbl_signups.setItem(i, 4, QTableWidgetItem(str(row.get("person_phone") or "")))
            self.tbl_signups.setItem(i, 5, QTableWidgetItem(str(row.get("lighting_summary") or "")))
            self.tbl_signups.setItem(i, 6, QTableWidgetItem(str(int(row.get("total_amount") or 0))))
            self.tbl_signups.setItem(i, 7, QTableWidgetItem("已繳費" if is_paid else "未繳費"))
            if is_paid and receipt_no:
                self.tbl_signups.item(i, 0).setToolTip(f"已繳費，收據號碼：{receipt_no}")
                self.tbl_signups.item(i, 7).setToolTip(f"收據號碼：{receipt_no}")
            self._apply_signup_group_row_style(i, group_id)
        self._reload_signup_item_totals()
        self._update_signup_action_buttons()

    def _reload_signup_item_totals(self):
        kw = (self.edt_signup_search.text() or "").strip() if hasattr(self, "edt_signup_search") else ""
        rows = self.controller.get_lighting_signup_item_totals(self.year_spin.value(), keyword=kw)
        parts = []
        grand_total = 0
        for row in rows:
            name = str(row.get("lighting_item_name") or "").strip() or "未命名燈別"
            amount = int(row.get("total_amount") or 0)
            grand_total += amount
            parts.append(f"{name}：{amount}元")
        self.lbl_lighting_grand_total.setText(f"總額：{grand_total} 元")
        self.lbl_lighting_item_totals.setText(
            f"各燈別總額：{'、'.join(parts)}" if parts else "各燈別總額：0 元"
        )

    def _get_current_signup_row_meta(self) -> dict:
        row = self.tbl_signups.currentRow()
        if row < 0:
            return {}
        item = self.tbl_signups.item(row, 3)
        data = item.data(Qt.UserRole) if item else None
        return data if isinstance(data, dict) else {}

    def _update_signup_action_buttons(self):
        meta = self._get_current_signup_row_meta()
        has_row = bool(str((meta or {}).get("signup_id") or "").strip())
        is_paid = bool((meta or {}).get("is_paid"))
        self.btn_edit_signup.setEnabled(has_row)
        self.btn_append_signup.setEnabled(has_row and is_paid)
        self.btn_delete_signup.setEnabled(has_row)
        self.btn_edit_signup.setToolTip("")

    def _signup_group_color(self, group_id: str):
        gid = str(group_id or "").strip()
        if not gid:
            return None
        from PyQt5.QtGui import QColor
        # 只使用兩種底色：白色 + 主題色
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
        for c in range(self.tbl_signups.columnCount()):
            item = self.tbl_signups.item(row_idx, c)
            if item:
                item.setBackground(color)

    def _on_edit_signup(self):
        meta = self._get_current_signup_row_meta()
        signup_id = str((meta or {}).get("signup_id") or "").strip()
        person_id = str((meta or {}).get("person_id") or "").strip()
        is_paid = bool((meta or {}).get("is_paid"))
        if not signup_id or not person_id:
            QMessageBox.information(self, "請先選取", "請先在已報名明細選取一筆資料。")
            return
        if is_paid:
            QMessageBox.information(
                self,
                "已繳費報名限制",
                "已繳費的報名無法修改，要增加請用追加報名，要改品項請先刪除再重新報名",
            )
            return

        try:
            household_people = self.controller.get_household_people_by_person_id(person_id, status="ACTIVE")
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取人員資料時發生錯誤：\n{e}")
            return
        person = next((p for p in (household_people or []) if str(p.get("id") or "").strip() == person_id), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該報名人員資料。")
            return

        active_items = list(getattr(self, "_active_lighting_items", []) or [])
        if not active_items:
            QMessageBox.information(self, "無可用燈別", "目前沒有啟用中的可報名燈別")
            return
        try:
            selected_map = self.controller.get_lighting_signup_selected_item_ids(self.year_spin.value(), [person_id])
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取既有安燈勾選資料時發生錯誤：\n{e}")
            return

        dlg = LightingHouseholdSignupDialog(
            people=[person],
            lighting_items=active_items,
            selected_by_person_id=selected_map,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        requests = dlg.get_signup_requests() or []
        if not requests:
            return
        req = requests[0] or {}
        item_ids = req.get("lighting_item_ids") or []
        if not item_ids:
            QMessageBox.information(self, "未儲存", "請至少勾選一個燈別；若要刪除請使用「刪除報名」。")
            return
        try:
            self.controller.update_lighting_signup_items_by_signup_id(
                signup_id,
                item_ids,
                allow_paid_update=False,
            )
        except Exception as e:
            QMessageBox.warning(self, "修改失敗", str(e))
            return
        QMessageBox.information(self, "完成", "修改報名完成。")
        self._reload_signup_list()

    def _on_append_signup(self):
        meta = self._get_current_signup_row_meta()
        signup_id = str((meta or {}).get("signup_id") or "").strip()
        person_id = str((meta or {}).get("person_id") or "").strip()
        is_paid = bool((meta or {}).get("is_paid"))
        if not signup_id or not person_id:
            QMessageBox.information(self, "請先選取", "請先在已報名明細選取一筆資料。")
            return
        if not is_paid:
            QMessageBox.information(self, "不適用", "未繳費紀錄請使用「修改報名」。")
            return

        try:
            household_people = self.controller.get_household_people_by_person_id(person_id, status="ACTIVE")
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取人員資料時發生錯誤：\n{e}")
            return
        person = next((p for p in (household_people or []) if str(p.get("id") or "").strip() == person_id), None)
        if not person:
            QMessageBox.warning(self, "資料錯誤", "找不到該報名人員資料。")
            return

        active_items = list(getattr(self, "_active_lighting_items", []) or [])
        if not active_items:
            QMessageBox.information(self, "無可用燈別", "目前沒有啟用中的可報名燈別")
            return

        dlg = LightingHouseholdSignupDialog(
            people=[person],
            lighting_items=active_items,
            selected_by_person_id={person_id: []},
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return
        requests = dlg.get_signup_requests() or []
        if not requests:
            return
        req = requests[0] or {}
        item_ids = req.get("lighting_item_ids") or []
        if not item_ids:
            QMessageBox.information(self, "未儲存", "請至少勾選一個燈別。")
            return

        ans = QMessageBox.question(
            self,
            "確認追加報名",
            "將新增一筆「追加」安燈報名紀錄（原已繳費紀錄不變）。\n\n是否繼續？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        try:
            result = self.controller.create_lighting_signup_append(
                self.year_spin.value(),
                person_id,
                item_ids,
            )
        except Exception as e:
            QMessageBox.warning(self, "追加失敗", str(e))
            return
        kind_text = "追加" if str((result or {}).get("signup_kind") or "").upper() == "APPEND" else "初始"
        QMessageBox.information(self, "完成", f"已新增一筆「{kind_text}」報名紀錄。")
        self._reload_signup_list()

    def _on_delete_signup(self):
        meta = self._get_current_signup_row_meta()
        signup_id = str((meta or {}).get("signup_id") or "").strip()
        is_paid = bool((meta or {}).get("is_paid"))
        row = self.tbl_signups.currentRow()
        name_item = self.tbl_signups.item(row, 3) if row >= 0 else None
        person_name = str(name_item.text() if name_item else "").strip()
        if not signup_id:
            QMessageBox.information(self, "請先選取", "請先在已報名明細選取一筆資料。")
            return
        ans = QMessageBox.question(
            self,
            "確認刪除",
            ("此筆已繳費，將刪除當前選取報名紀錄，並將收支交易標記為作廢。\n\n" if is_paid else "")
            + f"確定要刪除報名「{person_name or signup_id}」嗎？"
        )
        if ans != QMessageBox.Yes:
            return
        try:
            ok = self.controller.delete_lighting_signup(self.year_spin.value(), signup_id)
        except Exception as e:
            QMessageBox.warning(self, "刪除失敗", str(e))
            return
        if not ok:
            QMessageBox.warning(self, "刪除失敗", "找不到該筆安燈報名資料。")
            return
        QMessageBox.information(self, "完成", "刪除報名完成。")
        self._reload_signup_list()

    def _on_print_signup_list_by_item(self):
        year_value = int(self.year_spin.value())
        keyword = (self.edt_signup_search.text() or "").strip()
        rows = self.controller.list_lighting_signup_rows_by_item(year_value, keyword=keyword)
        if not rows:
            QMessageBox.information(self, "無資料", "目前沒有可列印的安燈報名資料。")
            return

        item_rows = self.controller.list_lighting_items(include_inactive=True)
        item_names = [str((x or {}).get("name") or "").strip() for x in (item_rows or [])]
        item_names = [x for x in item_names if x]

        headers = ["燈別", "姓名", "電話", "金額", "繳費", "收據號"]
        report_rows = []
        for row in rows:
            item_name = str(row.get("lighting_item_name") or "").strip()
            person_name = str(row.get("person_name") or "").strip()
            person_phone = str(row.get("person_phone") or "").strip()
            amount = int(row.get("item_amount") or 0)
            is_paid = int(row.get("is_paid") or 0) == 1
            receipt = str(row.get("payment_receipt_number") or "").strip()

            report_rows.append([
                item_name,
                person_name,
                person_phone,
                str(amount),
                "已繳費" if is_paid else "未繳費",
                receipt,
            ])

        PrintHelper.print_table_report_with_item_filter(
            f"{year_value}安燈報名名單",
            headers,
            report_rows,
            item_names=item_names,
            item_name_col=0,
            landscape=True,
        )

    def _select_all_signup_rows(self):
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def _clear_signup_row_selection(self):
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            status_item = self.tbl_signups.item(r, 7)
            is_paid = str(status_item.text() if status_item else "") == "已繳費"
            if item and not is_paid:
                item.setCheckState(Qt.Unchecked)

    def _selected_signup_ids(self):
        ids = []
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            status_item = self.tbl_signups.item(r, 7)
            is_paid = str(status_item.text() if status_item else "") == "已繳費"
            if item and (not is_paid) and item.checkState() == Qt.Checked:
                sid = str(item.data(Qt.UserRole) or "").strip()
                if sid:
                    ids.append(sid)
        return ids

    def _on_mark_paid(self):
        signup_ids = self._selected_signup_ids()
        if not signup_ids:
            QMessageBox.warning(self, "錯誤", "請先勾選要繳費的報名名單。")
            return
        handler = (self.edt_payment_handler.text() or "").strip()
        if not handler:
            QMessageBox.warning(self, "錯誤", "經手人為必填。")
            return
        result = self.controller.mark_lighting_signups_paid(self.year_spin.value(), signup_ids, handler=handler)
        QMessageBox.information(
            self,
            "繳費完成",
            f"成功 {int(result.get('paid_count') or 0)} 筆，略過 {int(result.get('skipped_count') or 0)} 筆。",
        )
        self._reload_signup_list()
