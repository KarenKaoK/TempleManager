# app/dialogs/plan_edit_dialog.py
from __future__ import annotations

from typing import Optional, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QFormLayout, QComboBox, QSpinBox, QFrame
)


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
        self.f_items = QLineEdit()
        self.f_items.setPlaceholderText("例如：蓮花*9 / 金紙組 / 香油錢…（顯示用）")

        self.f_fee_type = QComboBox()
        for label, val in self.FEE_TYPE_OPTIONS:
            self.f_fee_type.addItem(label, val)
        self.f_fee_type.currentIndexChanged.connect(self._on_fee_type_changed)

        self.f_amount = QSpinBox()
        self.f_amount.setRange(0, 10_000_000)
        self.f_amount.setSingleStep(50)
        self.f_amount.setSuffix(" 元")

        self.f_note = QTextEdit()
        self.f_note.setFixedHeight(80)

        form.addRow("方案名稱", self.f_name)
        form.addRow("方案項目", self.f_items)
        form.addRow("費用方式", self.f_fee_type)
        form.addRow("固定金額", self.f_amount)
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
        self.f_items.setText(str(plan_data.get("items", "") or ""))

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
        self.f_amount.setEnabled(is_fixed)
        if not is_fixed:
            self.f_amount.setValue(0)

    def _collect_payload(self) -> Optional[Dict]:
        name = self.f_name.text().strip()
        items = self.f_items.text().strip()
        fee_type = str(self.f_fee_type.currentData())
        amount = int(self.f_amount.value()) if fee_type == "fixed" else None
        note = self.f_note.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "欄位不足", "請輸入方案名稱")
            return None
        if not items:
            QMessageBox.warning(self, "欄位不足", "請輸入方案項目（顯示用）")
            return None
        if fee_type == "fixed" and (amount is None or amount < 0):
            QMessageBox.warning(self, "欄位不足", "固定金額必須是 0 以上")
            return None

        return {
            "name": name,
            "items": items,
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

                new_plan_id = self.controller.create_activity_plan(self.activity_id, payload)
                self._result_plan_id = new_plan_id
                QMessageBox.information(self, "新增完成", "方案已新增完成")
                self.accept()
                return

            # edit
            if not self.plan_id:
                QMessageBox.warning(self, "無法儲存", "找不到要修改的方案 ID")
                return

            # 你 controller 目前未必有 update_activity_plan（名稱可能不同）
            # 我先嘗試常見命名：update_activity_plan(plan_id, payload)
            if hasattr(self.controller, "update_activity_plan"):
                self.controller.update_activity_plan(self.plan_id, payload)
            elif hasattr(self.controller, "update_plan"):
                self.controller.update_plan(self.plan_id, payload)
            else:
                raise AttributeError("No update method found: update_activity_plan / update_plan")

            self._result_plan_id = self.plan_id
            QMessageBox.information(self, "儲存成功", "方案已更新完成")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"寫入資料庫失敗：\n{e}")
