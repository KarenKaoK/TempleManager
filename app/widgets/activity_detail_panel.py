# app/widgets/activity_detail_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt


class ActivityDetailPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== 活動基本資訊 =====
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.lbl_title = QLabel("安座大典")  # 先用預設文字，之後會動態改
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: 700;")

        title_row.addWidget(self.lbl_title, 1)   # 1 = 讓標題吃剩餘空間
        title_row.addStretch(1)

        self.btn_add_activity = QPushButton("+ 新增活動")
        self.btn_edit_activity = QPushButton("✎ 修改活動")
        self.btn_delete_activity = QPushButton("✕ 刪除活動")

        title_row.addWidget(self.btn_add_activity)
        title_row.addWidget(self.btn_edit_activity)
        title_row.addWidget(self.btn_delete_activity)

        root.addLayout(title_row)


        meta = QLabel("20260115-001 ｜ 2026/01/15 ～ 2026/01/15 ｜ 進行中")
        meta.setStyleSheet("color: #666666;")

        root.addWidget(meta)

        # ===== Tabs（先做外觀）=====
        tab_row = QHBoxLayout()
        btn_plan = QPushButton("方案")
        btn_signup = QPushButton("已報名")
        btn_note = QPushButton("備註")

        for btn in (btn_plan, btn_signup, btn_note):
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 14px;
                    border-radius: 14px;
                }
                QPushButton:checked {
                    background: #F29B38;
                    color: white;
                }
            """)

        btn_plan.setChecked(True)

        tab_row.addWidget(btn_plan)
        tab_row.addWidget(btn_signup)
        tab_row.addWidget(btn_note)
        tab_row.addStretch(1)

        root.addLayout(tab_row)

        # ===== 方案操作列 =====
        action_row = QHBoxLayout()
        btn_add = QPushButton("+ 新增方案")
        btn_edit = QPushButton("✎ 修改方案")
        btn_delete = QPushButton("✕ 刪除方案")

        action_row.addWidget(btn_add)
        action_row.addWidget(btn_edit)
        action_row.addWidget(btn_delete)
        action_row.addStretch(1)

        root.addLayout(action_row)

        # ===== 方案表格 =====
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["方案名稱", "方案項目", "費用方式", "金額"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        root.addWidget(self.table, 1)

        # ===== 假資料（讓畫面有感覺）=====
        self._load_mock_plans()

    def _load_mock_plans(self):
        data = [
            ("安坐平安", "蓮花*9", "固定金額", "999"),
            ("快快樂樂", "補運*9", "固定金額", "333"),
            ("加購A", "金紙組", "固定金額", "200"),
        ]
        self.table.setRowCount(len(data))
        for row, items in enumerate(data):
            for col, value in enumerate(items):
                self.table.setItem(row, col, QTableWidgetItem(value))



