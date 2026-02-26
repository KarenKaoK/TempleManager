from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QMessageBox, QLabel, QLineEdit, QFormLayout, QSpinBox, QComboBox, QHeaderView, QTextEdit, QGroupBox
)


class LightingSetupDialog(QDialog):
    KIND_OPTIONS = [
        ("吉祥如意燈", "JI_XIANG"),
        ("太歲燈", "TAI_SUI"),
        ("光明燈", "BRIGHT"),
        ("祭改", "JI_GAI"),
    ]

    KIND_LABEL_MAP = {v: k for k, v in KIND_OPTIONS}

    def __init__(self, controller, parent=None, user_role: str = ""):
        super().__init__(parent)
        self.controller = controller
        self.user_role = (user_role or "").strip()
        self.setWindowTitle("安燈設定")
        self.resize(1000, 700)
        self.setMinimumSize(900, 620)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)

        hint_group = QGroupBox("年度生肖提示設定（安燈報名頁只顯示此處文字）")
        hint_layout = QVBoxLayout(hint_group)
        hint_layout.setContentsMargins(8, 6, 8, 6)
        hint_layout.setSpacing(4)
        hint_row = QHBoxLayout()
        hint_row.setSpacing(8)
        hint_row.addWidget(QLabel("年度"))
        self.hint_year_spin = QSpinBox()
        self.hint_year_spin.setRange(2000, 2100)
        self.hint_year_spin.setButtonSymbols(QSpinBox.NoButtons)
        hint_row.addWidget(self.hint_year_spin)
        self.btn_hint_year_dec = QPushButton("▼")
        self.btn_hint_year_inc = QPushButton("▲")
        self.btn_hint_year_dec.setFixedSize(22, 14)
        self.btn_hint_year_inc.setFixedSize(22, 14)
        for b in (self.btn_hint_year_inc, self.btn_hint_year_dec):
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
        self.btn_hint_year_dec.clicked.connect(self.hint_year_spin.stepDown)
        self.btn_hint_year_inc.clicked.connect(self.hint_year_spin.stepUp)
        year_btn_col = QVBoxLayout()
        year_btn_col.setContentsMargins(0, 0, 0, 0)
        year_btn_col.setSpacing(0)
        year_btn_col.addWidget(self.btn_hint_year_inc)
        year_btn_col.addWidget(self.btn_hint_year_dec)
        hint_row.addLayout(year_btn_col)
        self.btn_hint_autofill = QPushButton("自動抓取")
        self.btn_hint_save = QPushButton("儲存提示")
        hint_row.addWidget(self.btn_hint_autofill)
        hint_row.addWidget(self.btn_hint_save)
        hint_row.addStretch(1)
        hint_layout.addLayout(hint_row)

        hint_row_2col = QHBoxLayout()
        hint_row_2col.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        left_col.addWidget(QLabel("犯太歲提示"))
        self.tai_sui_hint_input = QTextEdit()
        self.tai_sui_hint_input.setFixedHeight(58)
        left_col.addWidget(self.tai_sui_hint_input)

        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        right_col.addWidget(QLabel("祭改提示"))
        self.ji_gai_hint_input = QTextEdit()
        self.ji_gai_hint_input.setFixedHeight(58)
        right_col.addWidget(self.ji_gai_hint_input)

        hint_row_2col.addLayout(left_col, 1)
        hint_row_2col.addLayout(right_col, 1)
        hint_layout.addLayout(hint_row_2col)
        root.addWidget(hint_group)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["代號", "燈別名稱", "費用", "類型", "狀態"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        row_btn = QHBoxLayout()
        self.btn_add = QPushButton("新增燈別")
        self.btn_edit = QPushButton("修改燈別")
        self.btn_toggle = QPushButton("停用/啟用")
        self.btn_close = QPushButton("關閉返回")
        row_btn.addWidget(self.btn_add)
        row_btn.addWidget(self.btn_edit)
        row_btn.addWidget(self.btn_toggle)
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

        self.btn_add.clicked.connect(self.add_item)
        self.btn_edit.clicked.connect(self.edit_item)
        self.btn_toggle.clicked.connect(self.toggle_item)
        self.btn_close.clicked.connect(self.close)
        self.table.itemSelectionChanged.connect(self._sync_toggle_text)
        self.btn_hint_autofill.clicked.connect(self._autofill_hints)
        self.btn_hint_save.clicked.connect(self._save_hints)

        self._load_hint_settings()
        self._apply_hint_edit_permissions()

    def _can_edit_hints(self) -> bool:
        return self.user_role in {"管理員", "管理者", "會計", "會計人員"}

    def _apply_hint_edit_permissions(self):
        editable = self._can_edit_hints()
        self.hint_year_spin.setEnabled(editable)
        self.btn_hint_year_dec.setEnabled(editable)
        self.btn_hint_year_inc.setEnabled(editable)
        self.btn_hint_autofill.setEnabled(editable)
        self.btn_hint_save.setEnabled(editable)
        self.tai_sui_hint_input.setReadOnly(not editable)
        self.ji_gai_hint_input.setReadOnly(not editable)
        if not editable:
            tip = "僅管理員與會計可修改提示內容"
            self.tai_sui_hint_input.setToolTip(tip)
            self.ji_gai_hint_input.setToolTip(tip)

    def _load_hint_settings(self):
        data = self.controller.get_lighting_hint_settings()
        try:
            self.hint_year_spin.setValue(int(data.get("year") or 0))
        except Exception:
            pass
        # 開啟時先依年度抓預設（自動抓取）內容；若有已儲存修改則以已儲存內容優先
        defaults = self.controller._default_lighting_hint_texts(self.hint_year_spin.value())
        saved_tai_sui = (self.controller.get_setting("lighting/hint_tai_sui_text", "") or "").strip()
        saved_ji_gai = (self.controller.get_setting("lighting/hint_ji_gai_text", "") or "").strip()
        self.tai_sui_hint_input.setPlainText(saved_tai_sui or str(defaults.get("tai_sui_text") or ""))
        self.ji_gai_hint_input.setPlainText(saved_ji_gai or str(defaults.get("ji_gai_text") or ""))

    def _autofill_hints(self):
        defaults = self.controller._default_lighting_hint_texts(self.hint_year_spin.value())
        self.tai_sui_hint_input.setPlainText(defaults["tai_sui_text"])
        self.ji_gai_hint_input.setPlainText(defaults["ji_gai_text"])

    def _save_hints(self):
        if not self._can_edit_hints():
            QMessageBox.warning(self, "權限不足", "僅管理員與會計可修改提示內容。")
            return
        self.controller.save_lighting_hint_settings(
            year=int(self.hint_year_spin.value()),
            tai_sui_text=self.tai_sui_hint_input.toPlainText(),
            ji_gai_text=self.ji_gai_hint_input.toPlainText(),
        )
        QMessageBox.information(self, "成功", "安燈提示已儲存。")

    def _kind_label(self, kind: str) -> str:
        return self.KIND_LABEL_MAP.get((kind or "").strip().upper(), "吉祥如意燈")

    def _sync_toggle_text(self):
        r = self.table.currentRow()
        if r < 0:
            self.btn_toggle.setText("停用/啟用")
            return
        status_item = self.table.item(r, 4)
        if not status_item:
            self.btn_toggle.setText("停用/啟用")
            return
        self.btn_toggle.setText("啟用" if status_item.text() == "停用" else "停用")

    def load_data(self):
        rows = self.controller.list_lighting_items(include_inactive=True)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row.get("id") or "")))
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("name") or "")))
            self.table.setItem(i, 2, QTableWidgetItem(str(int(row.get("fee") or 0))))
            self.table.setItem(i, 3, QTableWidgetItem(self._kind_label(str(row.get("kind") or ""))))
            status_text = "啟用" if int(row.get("is_active") or 0) == 1 else "停用"
            self.table.setItem(i, 4, QTableWidgetItem(status_text))
        self._sync_toggle_text()

    def _open_item_editor(self, title: str, default_name: str = "", default_fee: int = 0, default_kind: str = "JI_XIANG"):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        layout = QFormLayout(dlg)

        name_input = QLineEdit(default_name)
        fee_input = QSpinBox()
        fee_input.setRange(0, 1000000000)
        fee_input.setValue(int(default_fee or 0))

        kind_combo = QComboBox()
        for label, code in self.KIND_OPTIONS:
            kind_combo.addItem(label, code)
        idx = max(0, kind_combo.findData((default_kind or "JI_XIANG").strip().upper()))
        kind_combo.setCurrentIndex(idx)

        layout.addRow("燈別名稱：", name_input)
        layout.addRow("費用：", fee_input)
        layout.addRow("類型：", kind_combo)

        row_btn = QHBoxLayout()
        btn_ok = QPushButton("確定")
        btn_cancel = QPushButton("取消")
        row_btn.addWidget(btn_ok)
        row_btn.addWidget(btn_cancel)
        layout.addRow(row_btn)

        result = {"ok": False, "name": "", "fee": 0, "kind": "JI_XIANG"}

        def _confirm():
            name = (name_input.text() or "").strip()
            if not name:
                QMessageBox.warning(dlg, "錯誤", "燈別名稱不可空白。")
                return
            result["ok"] = True
            result["name"] = name
            result["fee"] = int(fee_input.value())
            result["kind"] = str(kind_combo.currentData() or "JI_XIANG")
            dlg.accept()

        btn_ok.clicked.connect(_confirm)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec_()
        return result

    def add_item(self):
        data = self._open_item_editor("新增燈別")
        if not data.get("ok"):
            return
        try:
            self.controller.create_lighting_item(
                name=data["name"],
                fee=data["fee"],
                kind=data["kind"],
            )
            self.load_data()
            QMessageBox.information(self, "成功", "燈別新增成功。")
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))

    def edit_item(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "錯誤", "請先選擇要修改的燈別。")
            return
        item_id = self.table.item(r, 0).text()
        rows = self.controller.list_lighting_items(include_inactive=True)
        row = next((x for x in rows if str(x.get("id")) == item_id), None)
        if not row:
            QMessageBox.warning(self, "錯誤", "找不到燈別資料。")
            return
        data = self._open_item_editor(
            "修改燈別",
            default_name=str(row.get("name") or ""),
            default_fee=int(row.get("fee") or 0),
            default_kind=str(row.get("kind") or "JI_XIANG"),
        )
        if not data.get("ok"):
            return
        try:
            self.controller.update_lighting_item(
                item_id=item_id,
                name=data["name"],
                fee=data["fee"],
                kind=data["kind"],
            )
            self.load_data()
            QMessageBox.information(self, "成功", "燈別修改成功。")
        except Exception as e:
            QMessageBox.warning(self, "失敗", str(e))

    def toggle_item(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "錯誤", "請先選擇燈別。")
            return
        item_id = self.table.item(r, 0).text()
        name = self.table.item(r, 1).text()
        action = self.btn_toggle.text()
        if QMessageBox.question(self, f"確認{action}", f"確定要{action}燈別「{name}」嗎？") != QMessageBox.StandardButton.Yes:
            return
        ok = self.controller.toggle_lighting_item_active(item_id)
        if not ok:
            QMessageBox.warning(self, "失敗", "更新燈別狀態失敗。")
            return
        self.load_data()
        QMessageBox.information(self, "成功", f"燈別{action}成功。")
