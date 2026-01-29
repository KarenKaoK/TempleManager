from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QMessageBox, QFrame
)


class ActivitySignupEditDialog(QDialog):
    """
    修改報名 Dialog
    - 顯示基本資料（唯讀）
    - 只能修改方案 qty（FIXED）
    """
    def __init__(self, controller, signup_id: str, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.signup_id = signup_id
        self._data = None
        self._row_plan_id = {}  # row -> plan_id
        self.setWindowTitle("修改報名")
        self.setMinimumWidth(900)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== 基本資料（唯讀） =====
        top = QFrame()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(12, 12, 12, 12)
        top_lay.setSpacing(8)

        self.le_name = QLineEdit(); self.le_name.setReadOnly(True)
        self.le_phone = QLineEdit(); self.le_phone.setReadOnly(True)
        self.le_addr = QLineEdit(); self.le_addr.setReadOnly(True)
        self.le_gender = QLineEdit(); self.le_gender.setReadOnly(True)
        self.le_bday_ad = QLineEdit(); self.le_bday_ad.setReadOnly(True)
        self.le_bday_lunar = QLineEdit(); self.le_bday_lunar.setReadOnly(True)

        self.le_zodiac = QLineEdit(); self.le_zodiac.setReadOnly(True)
        self.le_birth_time = QLineEdit(); self.le_birth_time.setReadOnly(True)


        for le in (self.le_name, self.le_phone, self.le_addr):
            le.setStyleSheet("QLineEdit{ background:#F9FAFB; }")

        def row(label, widget):
            r = QHBoxLayout()
            lb = QLabel(label)
            lb.setFixedWidth(70)
            r.addWidget(lb)
            r.addWidget(widget, 1)
            return r

        top_lay.addLayout(row("姓名", self.le_name))
        top_lay.addLayout(row("電話", self.le_phone))
        top_lay.addLayout(row("地址", self.le_addr))
        top_lay.addLayout(row("性別", self.le_gender))
        top_lay.addLayout(row("生肖", self.le_zodiac))
        top_lay.addLayout(row("生日(國曆)", self.le_bday_ad))
        top_lay.addLayout(row("生日(農曆)", self.le_bday_lunar))
        top_lay.addLayout(row("時辰", self.le_birth_time))

        root.addWidget(top)

        # ===== 方案表格 =====
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["方案", "單價", "數量", "小計"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(self.tbl.SelectRows)
        self.tbl.setEditTriggers(self.tbl.NoEditTriggers)

        root.addWidget(self.tbl, 1)

        # ===== 合計 & buttons =====
        bottom = QHBoxLayout()
        self.lbl_total = QLabel("合計：0")
        self.lbl_total.setStyleSheet("font-weight:700;")
        bottom.addWidget(self.lbl_total)
        bottom.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_save = QPushButton("儲存")
        self.btn_save.setDefault(True)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_save)
        root.addLayout(bottom)

    def _load(self):
        data = self.controller.get_activity_signup_for_edit(self.signup_id)
        if not data:
            QMessageBox.warning(self, "載入失敗", "找不到報名資料")
            self.reject()
            return

        self._data = data
        p = data["person"]
        self.le_name.setText(p.get("name", ""))
        self.le_phone.setText(p.get("phone", ""))
        self.le_addr.setText(p.get("address", ""))
        self.le_gender.setText(p.get("gender", ""))
        self.le_bday_ad.setText(p.get("birthday_ad", ""))
        self.le_bday_lunar.setText(p.get("birthday_lunar", ""))
        self.le_zodiac.setText(p.get("zodiac", ""))
        self.le_birth_time.setText(p.get("birth_time", ""))


        self.tbl.setRowCount(0)
        self._row_plan_id.clear()

        for r, it in enumerate(data["items"]):
            self.tbl.insertRow(r)

            plan_id = it["plan_id"]
            plan_name = it.get("plan_name", "")
            price_type = it.get("price_type", "")
            qty = int(it.get("qty", 0) or 0)
            unit_price = int(it.get("unit_price_snapshot", 0) or 0)
            line_total = int(it.get("line_total", 0) or 0)

            self._row_plan_id[r] = plan_id

            self.tbl.setItem(r, 0, QTableWidgetItem(plan_name))

            
            if price_type == "FREE":
                self.tbl.setItem(r, 1, QTableWidgetItem("隨喜"))

                # ✅ qty：0/1（未報名=0）
                sp_qty = QSpinBox()
                sp_qty.setRange(0, 1)
                sp_qty.setValue(1 if qty > 0 else 0)
                self.tbl.setCellWidget(r, 2, sp_qty)

                # ✅ 金額：只有 qty=1 才可改；qty=0 時金額=0 並 disabled
                sp_amt = QSpinBox()
                sp_amt.setRange(0, 999999999)

                # 已報名：用 line_total；未報名：先帶 0（或你要帶 suggested_price 也可以）
                sp_amt.setValue(int(line_total or 0) if qty > 0 else 0)
                sp_amt.setEnabled(qty > 0)
                self.tbl.setCellWidget(r, 3, sp_amt)

                def _toggle_amt_enabled(_):
                    enabled = sp_qty.value() == 1
                    sp_amt.setEnabled(enabled)
                    if not enabled:
                        sp_amt.setValue(0)
                    self._recalc_total()

                sp_qty.valueChanged.connect(_toggle_amt_enabled)
                sp_amt.valueChanged.connect(self._recalc_total)

            else:
                self.tbl.setItem(r, 1, QTableWidgetItem(str(unit_price)))

                sp = QSpinBox()
                sp.setRange(0, 999)
                sp.setValue(qty)
                sp.valueChanged.connect(self._recalc_total)
                self.tbl.setCellWidget(r, 2, sp)

                self.tbl.setItem(r, 3, QTableWidgetItem(str(line_total)))

        self.tbl.resizeRowsToContents()
        self._recalc_total()

    def _recalc_total(self):
        total = 0
        for r in range(self.tbl.rowCount()):
            unit_item = self.tbl.item(r, 1)
            subtotal_item = self.tbl.item(r, 3)
            sp = self.tbl.cellWidget(r, 2)

            # donation
            if unit_item and unit_item.text() == "隨喜":
                w = self.tbl.cellWidget(r, 3)  # 這格現在是 QSpinBox
                subtotal = int(w.value()) if w else 0
                total += subtotal
                continue


            unit = int(unit_item.text() or 0) if unit_item else 0
            qty = int(sp.value()) if sp else 0
            subtotal = unit * qty

            if subtotal_item:
                subtotal_item.setText(str(subtotal))
            total += subtotal

        self.lbl_total.setText(f"合計：{total}")

    def _on_save(self):
        qty_map = {}
        free_amount_map = {}

        for r in range(self.tbl.rowCount()):
            plan_id = self._row_plan_id.get(r)
            if not plan_id:
                continue

            unit_item = self.tbl.item(r, 1)

            # 隨喜方案：改金額
            if unit_item and unit_item.text() == "隨喜":
                sp_qty = self.tbl.cellWidget(r, 2)   # 0/1
                sp_amt = self.tbl.cellWidget(r, 3)   # amount spin

                q = int(sp_qty.value()) if sp_qty else 0
                qty_map[plan_id] = q             

                if q == 1:
                    free_amount_map[plan_id] = int(sp_amt.value()) if sp_amt else 0
                continue


            # 固定金額方案：改數量
            sp_qty = self.tbl.cellWidget(r, 2)
            if sp_qty and sp_qty.isEnabled():
                qty_map[plan_id] = int(sp_qty.value())

        try:
            ok = self.controller.update_activity_signup_items(
                self.signup_id,
                qty_map,
                free_amount_map
            )

            if not ok:
                QMessageBox.warning(self, "儲存失敗", "報名資料未更新")
                return

            QMessageBox.information(self, "儲存完成", "報名資料已更新")
            self.accept()   # ✅ 關閉 dialog，回到上一層

        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", str(e))


