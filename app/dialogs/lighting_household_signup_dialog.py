from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialogButtonBox,
)


class LightingHouseholdSignupDialog(QDialog):
    """
    整戶安燈報名：
    - 每列一位人員
    - 右側燈別欄位可複選
    """

    def __init__(self, people, lighting_items, selected_by_person_id=None, parent=None):
        super().__init__(parent)
        self.people = list(people or [])
        self.lighting_items = list(lighting_items or [])
        self.selected_by_person_id = dict(selected_by_person_id or {})
        self.setWindowTitle("整戶安燈報名")
        self.resize(920, 520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("請勾選整戶各人員要報名的燈別（可複選）。"))

        fixed_cols = 4
        self.tbl = QTableWidget(0, fixed_cols + len(self.lighting_items))
        headers = ["姓名", "電話", "戶別", "生肖"]
        for item in self.lighting_items:
            name = str(item.get("name") or "")
            fee = int(item.get("fee") or 0)
            headers.append(f"{name}\n{fee}")
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        for c in range(fixed_cols, self.tbl.columnCount()):
            self.tbl.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)

        self.tbl.setRowCount(len(self.people))
        for r, p in enumerate(self.people):
            person_id = str(p.get("id") or "")
            name_item = QTableWidgetItem(str(p.get("name") or ""))
            name_item.setData(Qt.UserRole, person_id)
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(str(p.get("phone_mobile") or p.get("phone_home") or "")))
            role = str(p.get("role_in_household") or "").upper()
            self.tbl.setItem(r, 2, QTableWidgetItem("戶長" if role == "HEAD" else "戶員"))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(p.get("zodiac") or "")))

            selected = set(self.selected_by_person_id.get(person_id) or [])
            for idx, item in enumerate(self.lighting_items):
                col = fixed_cols + idx
                lighting_item_id = str(item.get("id") or "")
                cell = QTableWidgetItem("")
                cell.setFlags((cell.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled))
                cell.setCheckState(Qt.Checked if lighting_item_id in selected else Qt.Unchecked)
                cell.setData(Qt.UserRole, lighting_item_id)
                self.tbl.setItem(r, col, cell)

        root.addWidget(self.tbl, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_signup_requests(self):
        results = []
        fixed_cols = 4
        for r in range(self.tbl.rowCount()):
            name_item = self.tbl.item(r, 0)
            person_id = str(name_item.data(Qt.UserRole) or "").strip() if name_item else ""
            if not person_id:
                continue

            person = next((p for p in self.people if str(p.get("id") or "") == person_id), None) or {"id": person_id}
            item_ids = []
            for c in range(fixed_cols, self.tbl.columnCount()):
                cell = self.tbl.item(r, c)
                if cell and cell.checkState() == Qt.Checked:
                    iid = str(cell.data(Qt.UserRole) or "").strip()
                    if iid:
                        item_ids.append(iid)
            results.append({
                "person": person,
                "lighting_item_ids": item_ids,
            })
        return results
