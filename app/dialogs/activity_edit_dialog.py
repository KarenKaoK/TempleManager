# app/dialogs/activity_edit_dialog.py
from __future__ import annotations

from typing import Optional, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QFormLayout, QComboBox, QFrame
)


class ActivityEditDialog(QDialog):
    """
    Activity create/edit dialog.

    mode:
      - "new": create new activity (controller.insert_activity_new)
      - "edit": update existing activity (controller.update_activity)

    activity_data (optional) used to prefill fields in edit mode.
    """

    STATUS_OPTIONS = [
        ("進行中", 1),
        ("已結束", 0),
    ]

    def __init__(
        self,
        controller,
        mode: str = "new",
        activity_id: Optional[str] = None,
        activity_data: Optional[Dict] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.mode = mode
        self.activity_id = activity_id
        self._result_activity_id: Optional[str] = None

        self.setWindowTitle("新增活動" if mode == "new" else "修改活動")
        self.setModal(True)
        self.resize(520, 340)

        self._build_ui()
        self._prefill(activity_id=activity_id, activity_data=activity_data)

    # -----------------------------
    # Public
    # -----------------------------
    def result_activity_id(self) -> Optional[str]:
        """Return created/updated activity id after accept()."""
        return self._result_activity_id

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

        title = QLabel("新增活動" if self.mode == "new" else "修改活動")
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
        self.f_start = QLineEdit()
        self.f_end = QLineEdit()

        self.f_note = QTextEdit()
        self.f_note.setFixedHeight(90)

        self.f_status = QComboBox()
        for label, val in self.STATUS_OPTIONS:
            self.f_status.addItem(label, val)

        self.f_start.setPlaceholderText("例如：2026/01/15 或 2026-01-15")
        self.f_end.setPlaceholderText("例如：2026/01/15 或 2026-01-15")

        form.addRow("活動名稱", self.f_name)

        date_row = QHBoxLayout()
        date_row.setSpacing(8)
        date_row.addWidget(self.f_start, 1)
        date_row.addWidget(QLabel("～"))
        date_row.addWidget(self.f_end, 1)
        date_w = QFrame()
        date_w.setLayout(date_row)
        form.addRow("日期", date_w)

        if self.mode == "edit":
            form.addRow("狀態", self.f_status)

        form.addRow("備註", self.f_note)

        root.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_cancel = QPushButton("取消")
        self.btn_save = QPushButton("建立活動" if self.mode == "new" else "儲存修改")

        self.btn_cancel.setMinimumHeight(34)
        self.btn_save.setMinimumHeight(34)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save_clicked)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

    def _prefill(self, activity_id: Optional[str], activity_data: Optional[Dict]):
        if self.mode == "new":
            self.lbl_hint.setText("填寫後按「建立活動」")
            return

        # edit mode
        if activity_id:
            self.lbl_hint.setText(f"活動ID：{activity_id}")
        else:
            self.lbl_hint.setText("")

        if not activity_data:
            return

        self.f_name.setText(str(activity_data.get("name", "") or ""))
        self.f_start.setText(str(activity_data.get("activity_start_date", "") or ""))
        self.f_end.setText(str(activity_data.get("activity_end_date", "") or ""))
        self.f_note.setPlainText(str(activity_data.get("note", "") or ""))

        # 只在 edit 設定一次 status
        status_val = activity_data.get("status", 1)
        try:
            status_val = int(status_val)
        except Exception:
            status_val = 1

        idx = 0
        for i in range(self.f_status.count()):
            if int(self.f_status.itemData(i)) == status_val:
                idx = i
                break
        self.f_status.setCurrentIndex(idx)



    # -----------------------------
    # Save
    # -----------------------------
    def _collect_payload(self) -> Optional[Dict]:
        name = self.f_name.text().strip()
        start = self.f_start.text().strip()
        end = self.f_end.text().strip()
        note = self.f_note.toPlainText().strip()
        status = 1 if self.mode == "new" else int(self.f_status.currentData())


        if not name:
            QMessageBox.warning(self, "欄位不足", "請輸入活動名稱")
            return None
        if not start:
            QMessageBox.warning(self, "欄位不足", "請輸入活動開始日期")
            return None
        if not end:
            QMessageBox.warning(self, "欄位不足", "請輸入活動結束日期")
            return None

        return {
            "name": name,
            "activity_start_date": start,
            "activity_end_date": end,
            "note": note,
            "status": status,
        }

    def _on_save_clicked(self):
        payload = self._collect_payload()
        if not payload:
            return

        try:
            if self.mode == "new":
                if not hasattr(self.controller, "insert_activity_new"):
                    raise AttributeError("controller.insert_activity_new not found")

                new_id = self.controller.insert_activity_new(payload)
                self._result_activity_id = new_id

                # 成功提示（你原本在 panel 內做，移到 dialog 很合理）
                date_range = self._format_date_range(payload["activity_start_date"], payload["activity_end_date"])
                msg = (
                    "活動已新增完成\n\n"
                    f"活動名稱：{payload['name']}\n"
                    f"活動 ID：{new_id}\n"
                    f"活動時間：{date_range}"
                )
                QMessageBox.information(self, "活動已新增完成", msg)
                self.accept()
                return

            # edit
            if not self.activity_id:
                QMessageBox.warning(self, "無法儲存", "找不到要修改的活動 ID")
                return

            # NOTE:
            # 你目前 controller.update_activity 還是舊 schema（activity_date/location/is_active）
            # 我先照「合理期待」呼叫 update_activity(activity_id, payload)。
            # 你後續我會在 controller 幫你把 update_activity 改成新 schema。
            if not hasattr(self.controller, "update_activity"):
                raise AttributeError("controller.update_activity not found")

            self.controller.update_activity(self.activity_id, payload)
            self._result_activity_id = self.activity_id

            QMessageBox.information(self, "儲存成功", "活動已更新完成")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", f"寫入資料庫失敗：\n{e}")

    @staticmethod
    def _format_date_range(start: str, end: str) -> str:
        if start and end and start != end:
            return f"{start} ～ {end}"
        return start or end or ""
