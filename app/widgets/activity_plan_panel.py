# app/widgets/activity_plan_panel.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QCheckBox, QSpinBox, QLineEdit, QSizePolicy, QMessageBox
)


# -------------------------
# Data model
# -------------------------

@dataclass
class PlanItem:
    plan_id: str
    name: str
    desc: str = ""                 # e.g. "蓮花*9 | 固定金額"
    fee_type: str = "fixed"        # "fixed" | "donation"
    unit_price: int = 0            # fixed default price; donation can be 0
    default_qty: int = 1
    min_qty: int = 0
    max_qty: int = 99


def _money(n: int) -> str:
    # 999 -> "999" (你若想加逗號可改成 format(n, ","))
    return str(int(n)) if n is not None else "0"


# -------------------------
# UI: Each plan row
# -------------------------

class PlanRowWidget(QFrame):
    changed = pyqtSignal()  # any change: checkbox/qty/price

    def __init__(self, plan: PlanItem, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.plan = plan

        self.setObjectName("planRow")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        # Left: checkbox + texts
        left = QHBoxLayout()
        left.setSpacing(10)

        self.chk = QCheckBox()
        self.chk.stateChanged.connect(self._on_any_changed)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self.lbl_name = QLabel(plan.name)
        self.lbl_name.setObjectName("planName")

        self.lbl_desc = QLabel(plan.desc)
        self.lbl_desc.setObjectName("planDesc")

        text_col.addWidget(self.lbl_name)
        if plan.desc:
            text_col.addWidget(self.lbl_desc)

        left.addWidget(self.chk, 0, Qt.AlignTop)
        left.addLayout(text_col, 1)
        root.addLayout(left, 1)

        # Middle: unit price display / donation input
        mid = QVBoxLayout()
        mid.setSpacing(4)

        self.lbl_unit_tag = QLabel("單價")
        self.lbl_unit_tag.setObjectName("unitTag")

        if plan.fee_type == "donation":
            # donation: editable unit price
            self.edt_unit = QLineEdit()
            self.edt_unit.setObjectName("donationUnitEdit")
            self.edt_unit.setPlaceholderText("隨喜金額")
            self.edt_unit.setValidator(QIntValidator(0, 99999999, self))
            self.edt_unit.setText(_money(plan.unit_price))
            self.edt_unit.textChanged.connect(self._on_any_changed)
            self._set_donation_edit_enabled(False)
            mid.addWidget(self.lbl_unit_tag, 0, Qt.AlignRight)
            mid.addWidget(self.edt_unit, 0, Qt.AlignRight)
            self.lbl_unit_price = None
        else:
            # fixed: big bold number
            self.lbl_unit_price = QLabel(_money(plan.unit_price))
            self.lbl_unit_price.setObjectName("unitPrice")
            self.edt_unit = None
            mid.addWidget(self.lbl_unit_tag, 0, Qt.AlignRight)
            mid.addWidget(self.lbl_unit_price, 0, Qt.AlignRight)

        root.addLayout(mid, 0)

        # Right: qty controls (- 1 +)
        right = QHBoxLayout()
        right.setSpacing(8)

        self.btn_minus = QPushButton("–")
        self.btn_minus.setObjectName("qtyBtn")
        self.btn_minus.clicked.connect(self._dec_qty)

        self.spin_qty = QSpinBox()
        self.spin_qty.setObjectName("qtySpin")
        self.spin_qty.setRange(plan.min_qty, plan.max_qty)
        self.spin_qty.setValue(plan.default_qty)
        self.spin_qty.valueChanged.connect(self._on_any_changed)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("qtyBtn")
        self.btn_plus.clicked.connect(self._inc_qty)

        right.addWidget(self.btn_minus)
        right.addWidget(self.spin_qty)
        right.addWidget(self.btn_plus)

        root.addLayout(right, 0)
        root.setAlignment(right, Qt.AlignRight)     

        # initial disable for qty buttons until checked?（跟你圖一致：可不禁用也行）
        self._set_controls_enabled(False)

        self.chk.stateChanged.connect(self._on_checked_changed)

    # ---- state helpers ----

    def _set_controls_enabled(self, enabled: bool):
        self.btn_minus.setEnabled(enabled)
        self.btn_plus.setEnabled(enabled)
        self.spin_qty.setEnabled(enabled)

        if self.plan.fee_type == "donation" and self.edt_unit is not None:
            self._set_donation_edit_enabled(enabled)

    def _set_donation_edit_enabled(self, enabled: bool):
        self.edt_unit.setEnabled(enabled)
        # 讓 disabled 狀態看起來更像「灰掉」但仍可讀
        self.edt_unit.setProperty("disabledLike", not enabled)
        self.edt_unit.style().unpolish(self.edt_unit)
        self.edt_unit.style().polish(self.edt_unit)

    def _on_checked_changed(self):
        enabled = self.chk.isChecked()
        self._set_controls_enabled(enabled)
        self.changed.emit()

    def _on_any_changed(self, *_):
        self.changed.emit()

    def _inc_qty(self):
        self.spin_qty.setValue(self.spin_qty.value() + 1)

    def _dec_qty(self):
        self.spin_qty.setValue(max(self.spin_qty.minimum(), self.spin_qty.value() - 1))

    # ---- public getters ----

    def is_selected(self) -> bool:
        return self.chk.isChecked()

    def qty(self) -> int:
        return int(self.spin_qty.value())

    def unit_price(self) -> int:
        if self.plan.fee_type == "donation" and self.edt_unit is not None:
            txt = (self.edt_unit.text() or "").strip()
            return int(txt) if txt.isdigit() else 0
        return int(self.plan.unit_price)

    def amount(self) -> int:
        if not self.is_selected():
            return 0
        return self.unit_price() * self.qty()

    def selection_payload(self) -> Dict[str, Any]:
        """回傳一筆你後面寫入 DB/收入表 會用到的資訊"""
        return {
            "plan_id": self.plan.plan_id,
            "name": self.plan.name,
            "fee_type": self.plan.fee_type,
            "unit_price": self.unit_price(),
            "qty": self.qty(),
            "amount": self.amount(),
        }


# -------------------------
# Main Panel
# -------------------------

class ActivityPlanPanel(QWidget):
    """
    右下角：方案選擇（可多選 + 數量）/ 即時計算
    """

    amount_changed = pyqtSignal(int)      # total amount changed
    save_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()

    def __init__(self, controller=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("activityPlanPanel")

        self.controller = controller 
        self.activity_id: Optional[str] = None

        self._rows: List[PlanRowWidget] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)

        self.lbl_title = QLabel("方案選擇（可多選 + 數量）")
        self.lbl_title.setObjectName("panelTitle")

        header.addWidget(self.lbl_title, 1)
        # header.addWidget(self.btn_calc, 0, Qt.AlignRight)
        root.addLayout(header)

        # Scroll area for plan rows
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("planScroll")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_body = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_body)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch(1)

        self.scroll.setWidget(self.scroll_body)
        root.addWidget(self.scroll, 1)

        # Total card
        self.total_card = QFrame()
        self.total_card.setObjectName("totalCard")
        total_layout = QHBoxLayout(self.total_card)
        total_layout.setContentsMargins(14, 12, 14, 12)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        self.lbl_total_title = QLabel("總金額")
        self.lbl_total_title.setObjectName("totalTitle")

        self.lbl_total_sub = QLabel("已選 0 項，合計 0 份")
        self.lbl_total_sub.setObjectName("totalSub")

        left_col.addWidget(self.lbl_total_title)
        left_col.addWidget(self.lbl_total_sub)

        self.lbl_total_amount = QLabel("$0")
        self.lbl_total_amount.setObjectName("totalAmount")

        total_layout.addLayout(left_col, 1)
        total_layout.addWidget(self.lbl_total_amount, 0, Qt.AlignRight | Qt.AlignVCenter)

        root.addWidget(self.total_card, 0)

        # Receipt + activity amount
        form = QFrame()
        form.setObjectName("formCard")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        # 收據號碼
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_receipt = QLabel("收據號碼")
        lbl_receipt.setObjectName("formLabel")
        self.edt_receipt = QLineEdit()
        self.edt_receipt.setObjectName("formEdit")
        self.edt_receipt.setPlaceholderText("可選填")

        row1.addWidget(lbl_receipt, 0)
        row1.addWidget(self.edt_receipt, 1)
        form_layout.addLayout(row1)

        # 活動金額
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        lbl_amount = QLabel("活動金額")
        lbl_amount.setObjectName("formLabel")
        self.edt_amount = QLineEdit()
        self.edt_amount.setObjectName("formEdit")
        self.edt_amount.setValidator(QIntValidator(0, 99999999, self))
        self.edt_amount.setText("0")
        self.edt_amount.textChanged.connect(self._on_manual_amount_changed)

        row2.addWidget(lbl_amount, 0)
        row2.addWidget(self.edt_amount, 1)
        form_layout.addLayout(row2)

        root.addWidget(form, 0)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)

        self.btn_save = QPushButton("存入")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.save_clicked.emit)

        self.btn_clear = QPushButton("清空全部")
        self.btn_clear.setObjectName("primaryButton")
        self.btn_clear.clicked.connect(self.clear_all)

        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_clear)
        root.addLayout(btns)

        # Default style (你後續可搬進全域 QSS)
        self.setStyleSheet(self._default_qss())

    # -------------------------
    # Public API
    # -------------------------

    def set_controller(self, controller):
        self.controller = controller

    def clear_plans(self):
        """清空方案列表 + 金額歸零（切換活動時用）"""
        self.activity_id = None
        self.set_plans([])  # 會自動 recalculate → 金額變 0
        self.edt_receipt.clear()
        self.edt_amount.setText("0")

    def load_activity(self, activity_id: str):
        """
        給 ActivitySignupPage 呼叫：
        1) controller.get_activity_plans(activity_id) 取得 DB 方案
        2) dict -> PlanItem
        3) set_plans() 更新 UI
        """
        if not self.controller:
            QMessageBox.warning(self, "載入失敗", "ActivityPlanPanel 尚未設定 controller")
            return

        self.activity_id = activity_id

        try:
            plans_raw = self.controller.get_activity_plans(activity_id, active_only=True)
        except TypeError:
            # 有些 controller 沒有 active_only 參數就退而求其次
            plans_raw = self.controller.get_activity_plans(activity_id)
        except Exception as e:
            QMessageBox.warning(self, "載入失敗", f"讀取活動方案時發生錯誤：\n{e}")
            self.set_plans([])
            return

        plan_items: List[PlanItem] = []
        for p in (plans_raw or []):
            plan_items.append(self._to_plan_item(p))

        self.set_plans(plan_items)

    def _to_plan_item(self, p: Dict[str, Any]) -> PlanItem:
        """
        將 controller.get_activity_plans() 回來的 dict 轉成你 UI 用的 PlanItem
        你 controller 現在常見欄位：id, name, items/description, fee_type, amount, price_type, fixed_price...
        這裡做容錯，避免欄位名不同就炸。
        """
        plan_id = str(p.get("id") or p.get("plan_id") or "")
        name = str(p.get("name") or "")

        # desc：優先用 items/description，沒有就空字串
        desc = str(p.get("items") or p.get("description") or "")

        # fee_type：你目前 UI 只支援 fixed / donation
        # controller 若回傳 price_type=FREE 或 fee_type=donation 都當 donation
        fee_type = (p.get("fee_type") or "").lower().strip()
        price_type = (p.get("price_type") or "").upper().strip()

        if price_type == "FREE" or fee_type == "donation":
            ui_fee_type = "donation"
        else:
            ui_fee_type = "fixed"

        # unit_price：fixed 用固定金額；donation 用 suggested_price 或 amount(若有)；沒有就 0
        def _to_int(x, default=0):
            try:
                if x is None:
                    return default
                return int(float(x))
            except Exception:
                return default

        if ui_fee_type == "fixed":
            unit_price = _to_int(p.get("fixed_price"), None)
            if unit_price is None:
                unit_price = _to_int(p.get("amount"), 0)
        else:
            unit_price = _to_int(p.get("suggested_price"), None)
            if unit_price is None:
                unit_price = _to_int(p.get("amount"), 0)

        # qty：目前你預設 1，min_qty 建議 0（未勾選時也合理），max_qty 99
        return PlanItem(
            plan_id=plan_id,
            name=name,
            desc=desc,
            fee_type=ui_fee_type,
            unit_price=unit_price,
            default_qty=1,
            min_qty=0,
            max_qty=99,
        )

    def set_plans(self, plans: List[PlanItem]):
        """重新載入方案清單"""
        # clear existing rows
        for r in self._rows:
            r.setParent(None)
        self._rows.clear()

        # remove stretch at end
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # rebuild
        for p in plans:
            row = PlanRowWidget(p)
            row.changed.connect(self.recalculate)
            self.scroll_layout.addWidget(row)
            self._rows.append(row)

        self.scroll_layout.addStretch(1)
        self.recalculate()

    def get_selected_items(self) -> List[Dict[str, Any]]:
        """給你寫入 DB 用"""
        return [r.selection_payload() for r in self._rows if r.is_selected()]

    def get_receipt_no(self) -> str:
        return (self.edt_receipt.text() or "").strip()

    def get_activity_amount(self) -> int:
        txt = (self.edt_amount.text() or "").strip()
        return int(txt) if txt.isdigit() else 0

    def clear_all(self):
        for r in self._rows:
            r.chk.setChecked(False)
            r.spin_qty.setValue(r.plan.default_qty)
            if r.plan.fee_type == "donation" and r.edt_unit is not None:
                r.edt_unit.setText(_money(r.plan.unit_price))
        self.edt_receipt.clear()
        self.edt_amount.setText("0")
        self.recalculate()
        self.clear_clicked.emit()

    def get_selected_plans_payload(self) -> List[Dict[str, Any]]:
        """
        給 controller.create_activity_signup() 用的格式：
        [
        {"plan_id": "...", "qty": 1, "amount_override": None},   # fixed
        {"plan_id": "...", "qty": 1, "amount_override": 333},    # donation/free
        ]
        """
        payload: List[Dict[str, Any]] = []
        for r in self._rows:
            if not r.is_selected():
                continue

            plan_id = r.plan.plan_id
            qty = r.qty()

            if qty <= 0:
                continue

            if r.plan.fee_type == "donation":
                # donation：使用者可輸入單價（隨喜金額）
                unit = r.unit_price()
                if unit <= 0:
                    raise ValueError(f"方案「{r.plan.name}」為隨喜金額，請輸入大於 0 的金額")
                amount_override = unit
            else:
                # fixed：用 DB 的固定價，不需要 override
                amount_override = None

            payload.append({
                "plan_id": plan_id,
                "qty": qty,
                "amount_override": amount_override,
            })

        return payload

    # -------------------------
    # Calculation
    # -------------------------

    def recalculate(self):
        selected_rows = [r for r in self._rows if r.is_selected()]
        selected_count = len(selected_rows)
        total_qty = sum(r.qty() for r in selected_rows)
        total_amount = sum(r.amount() for r in selected_rows)

        self.lbl_total_sub.setText(f"已選 {selected_count} 項，合計 {total_qty} 份")
        self.lbl_total_amount.setText(f"${_money(total_amount)}")

        # 自動把活動金額帶成總金額（但若使用者手動改過，你也可以改成不要覆蓋）
        self._set_amount_silently(total_amount)

        self.amount_changed.emit(total_amount)

    def _set_amount_silently(self, value: int):
        # 避免 textChanged 造成回圈
        self.edt_amount.blockSignals(True)
        self.edt_amount.setText(_money(value))
        self.edt_amount.blockSignals(False)

    def _on_manual_amount_changed(self, *_):
        # 使用者手動改活動金額時：你若要同步回總金額顯示，可在此處理
        pass

    # -------------------------
    # QSS
    # -------------------------

    def _default_qss(self) -> str:
        # 偏你圖的淡橙/米色系，之後可以整合到全域 theme
        return """
        QWidget#activityPlanPanel {
            background: #FFFFFF;
        }
        QLabel#panelTitle {
            font-size: 16px;
            font-weight: 700;
            color: #2B2B2B;
        }
        QPushButton#pillButton {
            padding: 6px 14px;
            border-radius: 14px;
            border: 1px solid #F0C9A2;
            background: #FFF7EF;
            color: #A85B00;
            font-weight: 700;
        }
        QPushButton#pillButton:hover { background: #FFEBD6; }

        QScrollArea#planScroll {
            border: none;
            background: transparent;
        }

        QFrame#planRow {
            border: 1px solid #F3E1CF;
            border-radius: 14px;
            background: #FFFCF8;
        }
        QLabel#planName {
            font-size: 15px;
            font-weight: 800;
            color: #2B2B2B;
        }
        QLabel#planDesc {
            font-size: 12px;
            color: #8A7E74;
        }
        QLabel#unitTag {
            font-size: 12px;
            color: #8A7E74;
        }
        QLabel#unitPrice {
            font-size: 18px;
            font-weight: 900;
            color: #2B2B2B;
        }
        QLineEdit#donationUnitEdit {
            min-width: 90px;
            padding: 6px 10px;
            border-radius: 12px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            font-size: 14px;
            font-weight: 800;
            qproperty-alignment: 'AlignRight';
        }
        QLineEdit#donationUnitEdit[disabledLike="true"] {
            background: #F6F6F6;
            color: #9C9C9C;
        }

        QPushButton#qtyBtn {
            min-width: 34px;
            min-height: 34px;
            border-radius: 12px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            font-size: 16px;
            font-weight: 900;
        }
        QPushButton#qtyBtn:disabled {
            background: #F6F6F6;
            color: #BDBDBD;
        }
        QSpinBox#qtySpin {
            min-width: 48px;
            min-height: 34px;
            border-radius: 12px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            font-size: 14px;
            font-weight: 800;
        }
        QSpinBox::up-button, QSpinBox::down-button { width: 0px; }

        QFrame#totalCard {
            border-radius: 14px;
            background: #FFF7EF;
            border: 1px solid #F3E1CF;
        }
        QLabel#totalTitle {
            font-size: 15px;
            font-weight: 900;
            color: #2B2B2B;
        }
        QLabel#totalSub {
            font-size: 12px;
            color: #8A7E74;
        }
        QLabel#totalAmount {
            font-size: 22px;
            font-weight: 1000;
            color: #D63B2E;
        }

        QFrame#formCard {
            border-radius: 14px;
            background: #FFFFFF;
            border: 1px solid #F3E1CF;
        }
        QLabel#formLabel {
            min-width: 72px;
            font-size: 13px;
            font-weight: 800;
            color: #5A4A3F;
        }
        QLineEdit#formEdit {
            padding: 8px 10px;
            border-radius: 12px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            font-size: 13px;
        }

        QPushButton#primaryButton {
            padding: 10px 18px;
            border-radius: 14px;
            border: none;
            background: #F59E0B;
            color: #1F1F1F;
            font-weight: 900;
        }
        QPushButton#primaryButton:hover { background: #F8B84A; }

        QPushButton#secondaryButton {
            padding: 10px 18px;
            border-radius: 14px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            color: #2B2B2B;
            font-weight: 900;
        }
        QPushButton#secondaryButton:hover { background: #FFF3E6; }

        QPushButton#ghostButton {
            padding: 10px 18px;
            border-radius: 14px;
            border: 1px solid #F0D9C4;
            background: #FFFFFF;
            color: #9A3A2B;
            font-weight: 900;
        }
        QPushButton#ghostButton:hover { background: #FFF3E6; }

        QLabel#tipText {
            font-size: 12px;
            color: #3B7A3B;
        }
        """
    


# -------------------------
# (Optional) Quick demo
# -------------------------
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    w = ActivityPlanPanel()
    w.set_plans([
        PlanItem("p1", "安坐平安", "蓮花*9 | 固定金額", "fixed", 999, default_qty=1),
        PlanItem("p2", "快快樂樂", "補運*9 | 固定金額", "fixed", 333, default_qty=1),
        PlanItem("p3", "加購A", "金紙組 | 固定金額", "fixed", 200, default_qty=1),
        PlanItem("p4", "隨喜隨緣", "自由填寫 | 隨喜金額", "donation", 0, default_qty=1),
    ])
    w.resize(520, 800)
    w.show()
    app.exec_()
