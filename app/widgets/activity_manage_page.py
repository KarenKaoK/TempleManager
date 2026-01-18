# app/pages/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt

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
        title = QLabel("活動管理")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        btn_back = QPushButton("返回")
        btn_back.clicked.connect(self.request_close.emit)

        topbar.addWidget(title)
        topbar.addStretch(1)
        topbar.addWidget(btn_back)
        root.addLayout(topbar)

        # 主要區域：先用 splitter 占位（之後再換成你的新 layout）
        splitter = QSplitter(Qt.Vertical)

        upper = QGroupBox("上半部：活動清單 / 活動詳情")
        lower = QGroupBox("下半部：人員資料 / 方案選擇 / 金額")

        splitter.addWidget(upper)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        root.addWidget(splitter)
