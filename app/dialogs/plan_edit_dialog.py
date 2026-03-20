# app/dialogs/plan_edit_dialog.py
from __future__ import annotations

from typing import Optional, Dict
import json
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QFormLayout, QComboBox, QSpinBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget
)
from app.widgets.spin_with_arrows import SpinWithArrows


class PlanEditDialog(QDialog):
    """
    Activity plan create/edit dialog.

    mode:
      - "new": create a plan for an activity (controller.create_activity_plan)
      - "edit": update an existing plan (controller.update_activity_plan if exists)
    """

    # 對齊你 panel 內的 fee_type 概念：fixed / donation / other :contentReference[oaicite:1]{index=1}
    FEE_TYPE_OPTIONS = [
        ("固定金額", "fixed"),
        ("隨喜（自由填）", "donation"),
        ("其他", "other"),
    ]

    def __init__(
        self,
        controller,
        mode: str = "new",
        activity_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        plan_data: Optional[Dict] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.mode = mode
        self.activity_id = activity_id
        self.plan_id = plan_id
        self._result_plan_id: Optional[str] = None

        self.setWindowTitle("新增方案" if mode == "new" else "修改方案")
        self.setModal(True)
        self.resize(520, 360)

        self._build_ui()
        self._prefill(plan_data)

    # -----------------------------
    # Public
    # -----------------------------
    def result_plan_id(self) -> Optional[str]:
        return self._result_plan_id

    # -----------------------------
    # UI
    # -----------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header
        header = QFrame()
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(0, 0, 0, 0)

        title = QLabel("新增方案" if self.mode == "new" else "修改方案")
        title.setStyleSheet("font-size:14px; font-weight:700;")
        header_l.addWidget(title)
        header_l.addStretch(1)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setStyleSheet("color:#6B7280;")
        header_l.addWidget(self.lbl_hint)

        root.addWidget(header)

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.f_name = QLineEdit()
        self.tbl_items = QTableWidget(0, 2)
        self.tbl_items.setHorizontalHeaderLabels(["項目", "數量"])
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_items.setMinimumHeight(130)

        item_btn_row = QHBoxLayout()
        self.btn_add_item = QPushButton("+ 新增項目")
        self.btn_del_item = QPushButton("刪除項目")
        self.btn_add_item.clicked.connect(self._add_item_row)
        self.btn_del_item.clicked.connect(self._delete_selected_item_row)
        item_btn_row.addWidget(self.btn_add_item)
        item_btn_row.addWidget(self.btn_del_item)
        item_btn_row.addStretch(1)

        items_wrap = QWidget()
        items_wrap_l = QVBoxLayout(items_wrap)
        items_wrap_l.setContentsMargins(0, 0, 0, 0)
        items_wrap_l.setSpacing(6)
        items_wrap_l.addWidget(self.tbl_items)
        items_wrap_l.addLayout(item_btn_row)

        self.f_fee_type = QComboBox()
        for label, val in self.FEE_TYPE_OPTIONS:
            self.f_fee_type.addItem(label, val)
        self.f_fee_type.currentIndexChanged.connect(self._on_fee_type_changed)

        self.f_amount = QSpinBox()
        self.f_amount.setRange(0, 10_000_000)
        self.f_amount.setSingleStep(50)
        self.f_amount.setSuffix(" 元")
        self.f_amount_wrap = SpinWithArrows(self, spin_min_height=32, button_width=22, button_height=15)
        self.f_amount_wrap.spinbox.setRange(0, 10_000_000)
        self.f_amount_wrap.spinbox.setSingleStep(50)
        self.f_amount_wrap.spinbox.setSuffix(" 元")
        self.f_amount = self.f_amount_wrap.spinbox

        self.f_note = QTextEdit()
        self.f_note.setFixedHeight(80)

        form.addRow("方案名稱", self.f_name)
        form.addRow("方案項目", items_wrap)
        form.addRow("費用方式", self.f_fee_type)
        form.addRow("固定金額", self.f_amount_wrap)
        form.addRow("備註", self.f_note)

        root.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_save = QPushButton("新增方案" if self.mode == "new" else "儲存修改")

        self.btn_cancel.setMinimumHeight(34)
        self.btn_save.setMinimumHeight(34)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save_clicked)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

        # initial state
        self._add_item_row()
        self._on_fee_type_changed()

    def _prefill(self, plan_data: Optional[Dict]):
        if self.mode == "new":
            if self.activity_id:
                self.lbl_hint.setText(f"活動ID：{self.activity_id}")
            return

        if self.plan_id:
            self.lbl_hint.setText(f"方案ID：{self.plan_id}")

        if not plan_data:
            return

        self.f_name.setText(str(plan_data.get("name", "") or ""))
        self.tbl_items.setRowCount(0)
        raw_items = plan_data.get("plan_items")
        if isinstance(raw_items, list) and raw_items:
            for x in raw_items:
                self._add_item_row(str((x or {}).get("name", "")), int((x or {}).get("qty", 1) or 1))
        else:
            self._prefill_items_from_text(str(plan_data.get("items_raw") or plan_data.get("items") or ""))
        if self.tbl_items.rowCount() == 0:
            self._add_item_row()

        fee_type = plan_data.get("fee_type", "fixed")
        # fee_type might be display text
        if fee_type in ("固定金額", "fixed"):
            fee_type = "fixed"
        elif fee_type in ("隨喜", "隨喜（自由填）", "donation"):
            fee_type = "donation"
        else:
            fee_type = "other"

        idx = 0
        for i in range(self.f_fee_type.count()):
            if self.f_fee_type.itemData(i) == fee_type:
                idx = i
                break
        self.f_fee_type.setCurrentIndex(idx)

        amt = plan_data.get("amount", 0)
        try:
            amt_int = int(float(amt)) if amt is not None else 0
        except Exception:
            amt_int = 0
        self.f_amount.setValue(max(0, amt_int))

        self.f_note.setPlainText(str(plan_data.get("note", "") or ""))

    # -----------------------------
    # Logic
    # -----------------------------
    def _on_fee_type_changed(self):
        fee_type = str(self.f_fee_type.currentData())
        is_fixed = fee_type == "fixed"
        self.f_amount_wrap.setEnabled(is_fixed)
        self.f_amount.setEnabled(is_fixed)
        if not is_fixed:
            self.f_amount.setValue(0)

    def _add_item_row(self, name: str = "", qty: int = 1):
        row = self.tbl_items.rowCount()
        self.tbl_items.insertRow(row)
        self.tbl_items.setItem(row, 0, QTableWidgetItem(name))
        self.tbl_items.setItem(row, 1, QTableWidgetItem(str(max(1, int(qty or 1)))))

    def _delete_selected_item_row(self):
        row = self.tbl_items.currentRow()
        if row < 0:
            return
        self.tbl_items.removeRow(row)
        if self.tbl_items.rowCount() == 0:
            self._add_item_row()

    def _prefill_items_from_text(self, text: str):
        s = (text or "").strip()
        if not s:
            return
        parts = re.split(r"[\/、,\n]+", s)
        for p in parts:
            token = p.strip()
            if not token:
                continue
            m = re.match(r"^(.*?)(?:[xX＊*×]\s*(\d+))?$", token)
            if not m:
                continue
            name = (m.group(1) or "").strip()
            if not name:
                continue
            qty = int(m.group(2) or 1)
            self._add_item_row(name, qty)

    def _collect_plan_items(self):
        items = []
        for r in range(self.tbl_items.rowCount()):
            name_item = self.tbl_items.item(r, 0)
            qty_item = self.tbl_items.item(r, 1)
            name = (name_item.text() if name_item else "").strip()
            qty_text = (qty_item.text() if qty_item else "").strip()
            if not name:
                continue
            try:
                qty = int(qty_text or "1")
            except Exception:
                raise ValueError(f"第 {r + 1} 列數量格式錯誤，請輸入正整數")
            if qty <= 0:
                raise ValueError(f"第 {r + 1} 列數量需大於 0")
            items.append({"name": name, "qty": qty})
        return items

    def _collect_payload(self) -> Optional[Dict]:
        name = self.f_name.text().strip()
        try:
            plan_items = self._collect_plan_items()
        except ValueError as e:
            QMessageBox.warning(self, "格式錯誤", str(e))
            return None
        items = "、".join([f"{x['name']}×{x['qty']}" for x in plan_items])
        fee_type = str(self.f_fee_type.currentData())
        if fee_type == "fixed":
            self.f_amount.interpretText()
        amount = int(self.f_amount.value()) if fee_type == "fixed" else None
        note = self.f_note.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "欄位不足", "請輸入方案名稱")
            return None
        if fee_type == "fixed" and not plan_items:
            QMessageBox.warning(self, "欄位不足", "固定金額方案請至少新增一個方案項目")
            return None
        if fee_type == "fixed" and (amount is None or amount < 0):
            QMessageBox.warning(self, "欄位不足", "固定金額必須是 0 以上")
            return None

        return {
            "name": name,
            "items": items,
            "plan_items": plan_items,
            "fee_type": fee_type,
            "amount": amount,   # donation/other -> None
            "note": note,
        }

    def _on_save_clicked(self):
        payload = self._collect_payload()
        if not payload:
            return

        try:
            if self.mode == "new":
                if not self.activity_id:
                    QMessageBox.warning(self, "無法新增", "找不到活動 ID，請先選擇活動")
                    return

                if not hasattr(self.controller, "create_activity_plan"):
                    raise AttributeError("controller.create_activity_plan not found")

                # 統一用 plan_id 這個變數
                plan_id = self.controller.create_activity_plan(
                    self.activity_id,
                    payload["name"],
                    json.dumps(payload.get("plan_items") or [], ensure_ascii=False),
                    payload["fee_type"],
                    payload["amount"],
                    payload.get("note", "")
                )

                # create_activity_plan 必須 return plan_id，否則會是 None
                if not plan_id:
                    raise RuntimeError("create_activity_plan() did not return plan_id")

                self._result_plan_id = plan_id
                

                # 顯示費用方式文字
                fee_type = payload.get("fee_type", "")
                amount = payload.get("amount", None)

                if fee_type == "fixed":
                    fee_text = f"固定金額：{int(amount or 0)} 元"
                elif fee_type == "donation":
                    fee_text = "隨喜（自由填）"
                else:
                    fee_text = "其他"

                # 組合顯示內容（把新增內容一起顯示）
                msg = (
                    "方案已新增完成 n\n"
                    f"活動 ID：{self.activity_id}\n"
                    f"方案 ID：{plan_id}\n"
                    f"方案名稱：{payload.get('name', '')}\n"
                    f"方案項目：{payload.get('items', '')}\n"
                    f"費用方式：{fee_text}\n"
                )

                note = (payload.get("note") or "").strip()
                if note:
                    msg += f"備註：{note}\n"

                QMessageBox.information(self, "新增完成", msg)
                self.accept()
                return

            # -------------------------
            # EDIT
            # -------------------------
            if not self.plan_id:
                QMessageBox.warning(self, "無法儲存", "找不到要修改的方案 ID")
                return

            # update：盡量相容兩種 controller 寫法
            if hasattr(self.controller, "update_activity_plan"):
                try:
                    # 嘗試 (plan_id, payload) 的版本
                    self.controller.update_activity_plan(self.plan_id, payload)
                except TypeError:
                    # 改用拆參數
                    self.controller.update_activity_plan(
                        self.plan_id,
                        payload["name"],
                        payload["items"],
                        payload["fee_type"],
                        payload["amount"],
                        payload.get("note", "")
                    )

            elif hasattr(self.controller, "update_plan"):
                try:
                    self.controller.update_plan(self.plan_id, payload)
                except TypeError:
                    self.controller.update_plan(
                        self.plan_id,
                        payload["name"],
                        payload["items"],
                        payload["fee_type"],
                        payload["amount"],
                        payload.get("note", "")
                    )
            else:
                raise AttributeError("No update method found: update_activity_plan / update_plan")

            self._result_plan_id = self.plan_id
            QMessageBox.information(self, "儲存成功", "方案已更新完成")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"寫入資料庫失敗：\n{e}")
