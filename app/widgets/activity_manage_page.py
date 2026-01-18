# app/pages/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from app.widgets.activity_list_panel import ActivityListPanel, ActivityListItem
from app.widgets.activity_detail_panel import ActivityDetailPanel


class ActivityManagePage(QWidget):
    request_close = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()


    def _build_ui(self):
        root = QVBoxLayout(self)

        # 顶部工具列
        topbar = QHBoxLayout()

        btn_back = QPushButton("返回")

        btn_back.clicked.connect(self.request_close.emit)



        topbar.addStretch(1)
        topbar.addWidget(btn_back)
        root.addLayout(topbar)

        # 上下 splitter
        v_splitter = QSplitter(Qt.Vertical)

        upper_group = QGroupBox("")
        lower_group = QGroupBox("下半部：人員資料 / 方案選擇 / 金額")

        v_splitter.addWidget(upper_group)
        v_splitter.addWidget(lower_group)
        v_splitter.setStretchFactor(0, 2)
        v_splitter.setStretchFactor(1, 6)
        v_splitter.setSizes([500, 500])

        root.addWidget(v_splitter, 1)

        # ---------- 上半部內容：左右 splitter ----------
        upper_layout = QVBoxLayout(upper_group)
        upper_layout.setContentsMargins(10, 10, 10, 10)

        h_splitter = QSplitter(Qt.Horizontal)
        self.activity_list_panel = ActivityListPanel()
        h_splitter.addWidget(self.activity_list_panel)

        self.activity_detail_panel = ActivityDetailPanel()
        h_splitter.addWidget(self.activity_detail_panel)

        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 7)

        upper_layout.addWidget(h_splitter)

        # （下半部先放 placeholder layout，避免 groupbox 空著）
        lower_layout = QVBoxLayout(lower_group)
        lower_layout.setContentsMargins(10, 10, 10, 10)
        lower_layout.addWidget(QLabel("下半部（待完成）"))
        self._load_mock_activities()

    def _load_mock_activities(self):
        items = [
            ActivityListItem(
                id="1",
                title="二月元帥加持",
                code="20260115-002",
                date_range="2026/01/15 ~ 2026/01/15",
                plan_count=1,
                signup_count=1,
            ),
            ActivityListItem(
                id="2",
                title="安座大典",
                code="20260115-001",
                date_range="2026/01/15 ~ 2026/01/15",
                plan_count=3,
                signup_count=2,
            ),
        ]
        self.activity_list_panel.set_activities(items)

