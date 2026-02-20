from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from app.widgets.spin_with_arrows import SpinWithArrows


class ActivityHouseholdSignupDialog(QDialog):
    """
    整戶活動報名（新版）
    - 上半：每位成員後面直接顯示所有方案，直接輸入數量
    - 下半：方案說明、總金額
    - 最後統一一次存入
    """

    def __init__(
        self,
        controller,
        activity_id: str,
        activity_title: str,
        people: List[Dict[str, Any]],
        parent=None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.activity_id = (activity_id or "").strip()
        self.activity_title = activity_title or ""
        self.people = people or []

        self._plans: List[Dict[str, Any]] = []
        self._signup_requests: List[Dict[str, Any]] = []
        self._qty_widgets: Dict[tuple[int, int], QSpinBox] = {}
        self._prefill_by_person_id: Dict[str, Dict[str, Any]] = {}

        self.setWindowTitle("整戶活動報名")
        self.resize(1320, 820)

        self._load_plans()
        self._load_existing_signups()
        self._build_ui()
        self._load_people()
        self._refresh_total()

    def _person_id_of(self, person: Dict[str, Any]) -> str:
        if not isinstance(person, dict):
            return ""
        return str(person.get("id") or person.get("person_id") or "").strip()

    def _load_plans(self):
        try:
            plans = self.controller.get_activity_plans(self.activity_id, active_only=True)
        except Exception:
            plans = []
        self._plans = plans or []

    def _load_existing_signups(self):
        self._prefill_by_person_id = {}
        for p in self.people:
            pid = self._person_id_of(p)
            if not pid:
                continue
            try:
                signup_id = self.controller.get_activity_signup_id_by_person(self.activity_id, pid)
            except Exception:
                signup_id = None
            if not signup_id:
                continue
            try:
                data = self.controller.get_activity_signup_for_edit(signup_id)
            except Exception:
                data = None
            if not data:
                continue
            self._prefill_by_person_id[pid] = data

    def _role_text(self, p: Dict[str, Any]) -> str:
        role = (p.get("role_in_household") or "").strip().upper()
        if role == "HEAD":
            return "戶長"
        if role == "MEMBER":
            return "戶員"
        return ""

    def _unit_price_for(self, plan: Dict[str, Any]) -> int:
        price_type = str(plan.get("price_type") or "").upper()
        if price_type == "FIXED":
            return int(plan.get("fixed_price") or plan.get("amount") or 0)
        if price_type == "FREE":
            suggested = int(plan.get("suggested_price") or 0)
            min_price = int(plan.get("min_price") or 0)
            return max(suggested, min_price, 0)
        return int(plan.get("amount") or 0)

    def _plan_header(self, plan: Dict[str, Any]) -> str:
        name = str(plan.get("name") or "未命名方案")
        price_type = str(plan.get("price_type") or "").upper()
        if price_type == "FIXED":
            return f"{name}\n${self._unit_price_for(plan)}"
        if price_type == "FREE":
            return f"{name}\n金額"
        return name

    def _plan_desc_line(self, plan: Dict[str, Any]) -> str:
        name = str(plan.get("name") or "未命名方案")
        items = str(plan.get("items") or "").strip()
        price_type = str(plan.get("price_type") or "").upper()
        if price_type == "FIXED":
            price_text = f"單價 {self._unit_price_for(plan)} 元"
        else:
            min_price = int(plan.get("min_price") or 0)
            suggested = int(plan.get("suggested_price") or 0)
            price_text = f"隨喜（最低 {min_price} 元，建議 {suggested} 元）"
        if items:
            return f"{name}：{items}｜{price_text}"
        return f"{name}：{price_text}"

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        lbl_title = QLabel(f"活動：{self.activity_title}")
        lbl_title.setStyleSheet("font-size:16px; font-weight:800;")
        root.addWidget(lbl_title)

        lbl_hint = QLabel("上半部請勾選成員並填各方案數量；下半部確認方案說明與總金額後一次存入")
        lbl_hint.setStyleSheet("color:#666;")
        root.addWidget(lbl_hint)

        # ===== 上半：成員 x 方案數量 =====
        self.tbl = QTableWidget(0, 2 + len(self._plans))
        headers = ["報名", "成員"] + [self._plan_header(p) for p in self._plans]
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(58)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setWordWrap(True)
        self.tbl.itemChanged.connect(self._on_table_item_changed)

        self.tbl.setColumnWidth(0, 64)
        self.tbl.setColumnWidth(1, 320)
        for i in range(len(self._plans)):
            self.tbl.setColumnWidth(2 + i, 140)

        root.addWidget(self.tbl, 4)

        # ===== 下半：方案說明 + 總金額 =====
        lower = QFrame()
        lower.setStyleSheet("QFrame { background:#FFF8EE; border:1px solid #F0D9C4; border-radius:10px; }")
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(12, 10, 12, 10)
        lower_layout.setSpacing(8)

        lbl_desc_title = QLabel("方案說明")
        lbl_desc_title.setStyleSheet("font-weight:800; color:#5A4A3F;")
        lower_layout.addWidget(lbl_desc_title)

        self.lbl_plan_desc = QLabel("")
        self.lbl_plan_desc.setWordWrap(True)
        self.lbl_plan_desc.setStyleSheet("color:#5A4A3F;")
        lower_layout.addWidget(self.lbl_plan_desc)

        row2 = QGridLayout()
        row2.setHorizontalSpacing(16)
        row2.setVerticalSpacing(8)

        self.lbl_total = QLabel("總金額：0 元")
        self.lbl_total.setStyleSheet("font-size:18px; font-weight:900; color:#B42318;")
        row2.addWidget(self.lbl_total, 0, 0)

        self.lbl_count = QLabel("已勾選：0 人")
        self.lbl_count.setStyleSheet("font-weight:700; color:#5A4A3F;")
        row2.addWidget(self.lbl_count, 0, 1)

        row2.setColumnStretch(2, 1)
        lower_layout.addLayout(row2)
        root.addWidget(lower, 2)

        # buttons
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_ok = QPushButton("確認新增報名")
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_confirm)
        bottom.addWidget(btn_cancel)
        bottom.addWidget(btn_ok)
        root.addLayout(bottom)

        desc_lines = [self._plan_desc_line(p) for p in self._plans]
        self.lbl_plan_desc.setText("\n".join(desc_lines) if desc_lines else "（此活動目前沒有可用方案）")

    def _on_qty_changed(self, row: int):
        has_qty = False
        for col in range(len(self._plans)):
            spin = self._qty_widgets.get((row, col))
            if spin and spin.value() > 0:
                has_qty = True
                break

        chk = self.tbl.item(row, 0)
        if chk is not None:
            if has_qty and chk.checkState() != Qt.Checked:
                chk.setCheckState(Qt.Checked)
            if not has_qty and chk.checkState() == Qt.Checked:
                chk.setCheckState(Qt.Unchecked)

        self._refresh_total()

    def _load_people(self):
        self.tbl.setRowCount(0)
        self._qty_widgets.clear()

        for r, person in enumerate(self.people):
            self.tbl.insertRow(r)

            check_item = QTableWidgetItem("")
            check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            check_item.setCheckState(Qt.Unchecked)
            self.tbl.setItem(r, 0, check_item)

            role = self._role_text(person)
            name = str(person.get("name") or "").strip()
            phone = str(person.get("phone_mobile") or person.get("phone_home") or "").strip()
            pid = self._person_id_of(person)
            has_signed = pid in self._prefill_by_person_id
            signed_text = "【已報名】" if has_signed else "【未報名】"
            member_text = f"{name}（{role}）{signed_text}\n{phone}" if role else f"{name}{signed_text}\n{phone}"
            member_item = QTableWidgetItem(member_text.strip())
            member_item.setData(Qt.UserRole, dict(person))
            self.tbl.setItem(r, 1, member_item)

            for c, _plan in enumerate(self._plans):
                price_type = str((_plan or {}).get("price_type") or "").upper()
                editor = SpinWithArrows(self.tbl, spin_min_height=30, button_width=22, button_height=14)
                spin = editor.spinbox
                if price_type == "FREE":
                    # 隨喜：直接輸入金額
                    spin.setRange(0, 9999999)
                    spin.setSingleStep(100)
                else:
                    spin.setRange(0, 99)
                    spin.setSingleStep(1)
                spin.setValue(0)
                spin.setFocusPolicy(Qt.StrongFocus)

                spin.valueChanged.connect(lambda _v, rr=r: self._on_qty_changed(rr))
                self.tbl.setCellWidget(r, 2 + c, editor)
                self._qty_widgets[(r, c)] = spin

            # 載入既有報名（顯示狀態與既有數量，避免重複報名誤判）
            prefill = self._prefill_by_person_id.get(pid) or {}
            if prefill:
                item_rows = prefill.get("items") or []
                qty_by_plan_id = {}
                for it in item_rows:
                    plan_id = str(it.get("plan_id") or "").strip()
                    if not plan_id:
                        continue
                    price_type = str(it.get("price_type") or "").upper()
                    if price_type == "FREE":
                        qty_by_plan_id[plan_id] = int(it.get("line_total") or 0)
                    else:
                        qty_by_plan_id[plan_id] = int(it.get("qty") or 0)
                for c, plan in enumerate(self._plans):
                    plan_id = str(plan.get("id") or "").strip()
                    qty = int(qty_by_plan_id.get(plan_id) or 0)
                    if qty > 0:
                        spin = self._qty_widgets.get((r, c))
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(qty)
                            spin.blockSignals(False)

    def _on_table_item_changed(self, _item: QTableWidgetItem):
        self._refresh_total()

    def _collect_selected_plans_for_row(self, row: int) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        selected_plans: List[Dict[str, Any]] = []
        selected_items: List[Dict[str, Any]] = []
        total_amount = 0

        for c, plan in enumerate(self._plans):
            spin = self._qty_widgets.get((row, c))
            raw_value = int(spin.value()) if spin else 0
            if raw_value <= 0:
                continue

            unit = self._unit_price_for(plan)
            price_type = str(plan.get("price_type") or "").upper()
            if price_type == "FREE":
                # 隨喜欄位就是金額本身（非份數）
                line_amount = raw_value
                qty = 1
                amount_override = line_amount
            else:
                qty = raw_value
                line_amount = unit * qty
                amount_override = None

            selected_plans.append(
                {
                    "plan_id": str(plan.get("id") or ""),
                    "qty": qty,
                    "amount_override": amount_override,
                }
            )

            selected_items.append(
                {
                    "name": str(plan.get("name") or ""),
                    "qty": qty,
                    "amount": line_amount,
                }
            )
            total_amount += line_amount

        return selected_plans, selected_items, total_amount

    def _refresh_total(self):
        checked_count = 0
        total = 0

        for r in range(self.tbl.rowCount()):
            chk = self.tbl.item(r, 0)
            if not chk or chk.checkState() != Qt.Checked:
                continue
            checked_count += 1
            _plans, _items, row_total = self._collect_selected_plans_for_row(r)
            total += row_total

        self.lbl_count.setText(f"已勾選：{checked_count} 人")
        self.lbl_total.setText(f"總金額：{total} 元")

    def _on_confirm(self):
        selected_rows: List[int] = []
        for r in range(self.tbl.rowCount()):
            chk = self.tbl.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                selected_rows.append(r)

        if not selected_rows:
            QMessageBox.warning(self, "未勾選", "請先勾選至少一位人員")
            return

        requests: List[Dict[str, Any]] = []
        missing: List[str] = []

        for r in selected_rows:
            person_item = self.tbl.item(r, 1)
            person = person_item.data(Qt.UserRole) if person_item else {}
            pid = self._person_id_of(person)
            pname = str((person or {}).get("name") or f"第{r+1}列")

            if not pid:
                missing.append(f"{pname}（缺少 ID）")
                continue

            selected_plans, selected_items, total_amount = self._collect_selected_plans_for_row(r)
            if not selected_plans:
                missing.append(pname)
                continue

            requests.append(
                {
                    "person": dict(person),
                    "selected_plans": selected_plans,
                    "selected_items": selected_items,
                    "total_amount": int(total_amount),
                }
            )

        if missing:
            QMessageBox.warning(self, "方案未設定", "以下人員尚未設定方案：\n" + "\n".join(missing))
            return

        self._signup_requests = requests
        self.accept()

    def get_signup_requests(self) -> List[Dict[str, Any]]:
        return list(self._signup_requests)
