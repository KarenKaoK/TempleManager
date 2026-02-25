# DEPRECATED:
# 舊版安燈報名 QDialog。主程式入口已改為 QWidget 頁面：
# `app/widgets/lighting_signup_page.py`
# 保留此檔案僅供過渡期參考，請勿新增功能。

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QFrame, QLineEdit, QSplitter, QMessageBox, QWidget
)
from app.dialogs.lighting_household_signup_dialog import LightingHouseholdSignupDialog


class LightingSignupDialog(QDialog):
    """
    DEPRECATED: 請改用 `app.widgets.lighting_signup_page.LightingSignupPage`

    安燈報名：
    - 左側：參加人員搜尋（點選後彈整戶安燈報名）
    - 右側：已報名明細 / 燈別總額 / 繳費
    """

    def __init__(self, controller, parent=None, operator_name: str = "", user_role: str = ""):
        super().__init__(parent)
        self.controller = controller
        self.operator_name = (operator_name or "").strip()
        self.user_role = (user_role or "").strip()
        self.setWindowTitle("安燈報名")
        self.resize(1000, 700)
        self.setMinimumSize(1000, 700)
        self._build_ui()
        self.refresh_suggestions()
        self.load_active_items()
        self._reload_signup_list()

    def _build_ui(self):
        root = QVBoxLayout(self)

        title = QLabel("安燈報名")
        title.setStyleSheet("font-weight: 900;")
        root.addWidget(title)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("年度"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(date.today().year)
        self.year_spin.valueChanged.connect(lambda _v: self.refresh_suggestions())
        top_row.addWidget(self.year_spin)

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

        self.tbl_people_search = QTableWidget(0, 4)
        self.tbl_people_search.setHorizontalHeaderLabels(["姓名", "電話", "地址", "戶別"])
        self.tbl_people_search.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_people_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_people_search.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_people_search.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        left_layout.addWidget(self.tbl_people_search, 1)

        right_wrap = QWidget()
        right_layout = QVBoxLayout(right_wrap)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("已報名明細"))

        self.lighting_total_card = QFrame()
        self.lighting_total_card.setStyleSheet(
            "QFrame { background:#FFF8EE; border:1px solid #F0D9C4; border-radius:10px; }"
        )
        lighting_total_layout = QHBoxLayout(self.lighting_total_card)
        lighting_total_layout.setContentsMargins(12, 8, 12, 8)
        lighting_total_layout.setSpacing(10)
        self.lbl_lighting_item_totals = QLabel("燈別總額：0 元｜總額：0 元")
        self.lbl_lighting_item_totals.setStyleSheet("font-weight:700; color:#5A4A3F;")
        self.lbl_lighting_item_totals.setWordWrap(True)
        lighting_total_layout.addWidget(self.lbl_lighting_item_totals, 1)
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

        self.tbl_signups = QTableWidget(0, 6)
        self.tbl_signups.setHorizontalHeaderLabels(["勾選", "姓名", "電話", "燈別摘要", "金額", "繳費"])
        self.tbl_signups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_signups.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        right_layout.addWidget(self.tbl_signups, 1)

        right_btn_row = QHBoxLayout()
        self.btn_select_all_rows = QPushButton("全選繳費")
        self.btn_clear_selection_rows = QPushButton("清除")
        self.edt_payment_handler = QLineEdit()
        self.edt_payment_handler.setPlaceholderText("經手人（必填）")
        if self.operator_name:
            self.edt_payment_handler.setText(self.operator_name)
        self._apply_payment_handler_permissions()
        self.btn_pay = QPushButton("按此繳費")
        right_btn_row.addWidget(self.btn_select_all_rows)
        right_btn_row.addWidget(self.btn_clear_selection_rows)
        right_btn_row.addWidget(self.btn_pay)
        right_btn_row.addWidget(self.edt_payment_handler, 1)
        right_layout.addLayout(right_btn_row)

        body_splitter.addWidget(left_wrap)
        body_splitter.addWidget(right_wrap)
        body_splitter.setStretchFactor(0, 6)
        body_splitter.setStretchFactor(1, 5)
        root.addWidget(body_splitter, 1)

        self.btn_people_search.clicked.connect(self._search_people)
        self.btn_people_clear.clicked.connect(self._clear_people_search)
        self.tbl_people_search.cellClicked.connect(self._on_people_search_row_clicked)
        self.edt_signup_search.textChanged.connect(lambda _t: self._reload_signup_list())
        self.btn_show_all.clicked.connect(self._on_show_all_signups)
        self.btn_show_unpaid.clicked.connect(self._on_show_unpaid_signups)
        self.btn_clear_signup_search.clicked.connect(lambda: self.edt_signup_search.setText(""))
        self.btn_select_all_rows.clicked.connect(self._select_all_signup_rows)
        self.btn_clear_selection_rows.clicked.connect(self._clear_signup_row_selection)
        self.btn_pay.clicked.connect(self._on_mark_paid)

        row_btn = QHBoxLayout()
        row_btn.addStretch(1)
        self.btn_close = QPushButton("關閉返回")
        self.btn_close.clicked.connect(self.close)
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

    def _reload_all(self):
        self.refresh_suggestions()
        self.load_active_items()
        self._reload_signup_list()

    def refresh_suggestions(self):
        data = self.controller.get_lighting_hint_settings()
        self.lbl_hint_meta.setText(
            f"年度（本次報名）：{self.year_spin.value()}｜提示設定年度：{data.get('year')}｜提醒：實際是否建議報名，仍由廟方依法會/科儀規則人工判斷。"
        )
        self.txt_tai_sui_hint.setPlainText(str(data.get("tai_sui_text") or ""))
        self.txt_ji_gai_hint.setPlainText(str(data.get("ji_gai_text") or ""))

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
            self.tbl_people_search.setItem(i, 2, QTableWidgetItem(str(row.get("address") or "")))
            self.tbl_people_search.setItem(i, 3, QTableWidgetItem("戶長" if str(row.get("role_in_household") or "") == "HEAD" else "戶員"))
            self.tbl_people_search.item(i, 0).setData(Qt.UserRole, str(row.get("id") or ""))

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

    def _reload_signup_list(self, unpaid_only: bool = False):
        kw = (self.edt_signup_search.text() or "").strip() if hasattr(self, "edt_signup_search") else ""
        rows = self.controller.list_lighting_signups(self.year_spin.value(), keyword=kw, unpaid_only=unpaid_only)
        self.tbl_signups.setRowCount(len(rows))
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
            self.tbl_signups.setItem(i, 1, QTableWidgetItem(str(row.get("person_name") or "")))
            self.tbl_signups.setItem(i, 2, QTableWidgetItem(str(row.get("person_phone") or "")))
            self.tbl_signups.setItem(i, 3, QTableWidgetItem(str(row.get("lighting_summary") or "")))
            self.tbl_signups.setItem(i, 4, QTableWidgetItem(str(int(row.get("total_amount") or 0))))
            self.tbl_signups.setItem(i, 5, QTableWidgetItem("已繳費" if is_paid else "未繳費"))
        self._reload_signup_item_totals()

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
        if parts:
            self.lbl_lighting_item_totals.setText(f"{'、'.join(parts)}｜總額：{grand_total}元")
        else:
            self.lbl_lighting_item_totals.setText("燈別總額：0 元｜總額：0 元")

    def _select_all_signup_rows(self):
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def _clear_signup_row_selection(self):
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            status_item = self.tbl_signups.item(r, 5)
            is_paid = str(status_item.text() if status_item else "") == "已繳費"
            if item and not is_paid:
                item.setCheckState(Qt.Unchecked)

    def _selected_signup_ids(self):
        ids = []
        for r in range(self.tbl_signups.rowCount()):
            item = self.tbl_signups.item(r, 0)
            status_item = self.tbl_signups.item(r, 5)
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
