# app/widgets/activity_list_panel.py
from dataclasses import dataclass
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame
)


@dataclass
class ActivityListItem:
    id: str
    title: str
    code: str
    date_range: str
    status: str = "進行中"
    plan_count: int = 0
    signup_count: int = 0


class ActivityCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, item: ActivityListItem, parent=None):
        super().__init__(parent)
        self.item = item
        self._selected = False
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("activityCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(6)

        # 第一行：標題 + 狀態
        row1 = QHBoxLayout()
        self.lbl_title = QLabel(self.item.title)
        self.lbl_title.setObjectName("activityTitle")

        self.lbl_status = QLabel(self.item.status)
        self.lbl_status.setObjectName("activityStatus")

        row1.addWidget(self.lbl_title, 1)
        row1.addWidget(self.lbl_status, 0, Qt.AlignRight)
        root.addLayout(row1)

        # 第二行：編號 + 日期
        self.lbl_meta = QLabel(f"{self.item.code}  |  {self.item.date_range}")
        self.lbl_meta.setObjectName("activityMeta")
        root.addWidget(self.lbl_meta)

        # 第三行：方案/報名數
        self.lbl_counts = QLabel(f"方案 {self.item.plan_count}  |  報名 {self.item.signup_count}")
        self.lbl_counts.setObjectName("activityCounts")
        root.addWidget(self.lbl_counts)

        self._apply_style()

    def _apply_style(self):
        # 先用 inline stylesheet，之後你如果有全域 QSS，可以移出去
        base = """
        QFrame#activityCard {
            border: 1px solid #E6D8C7;
            border-radius: 12px;
            background: #FFFFFF;
        }
        QFrame#activityCard:hover {
            border: 1px solid #F0B060;
            background: #FFF7EE;
        }
        QLabel#activityTitle { font-size: 16px; font-weight: 700; color: #2B2B2B; }
        QLabel#activityStatus { font-size: 12px; color: #8A6A3B; padding: 2px 10px;
                                border: 1px solid #E6D8C7; border-radius: 10px; background: #FFF7EE; }
        QLabel#activityMeta { font-size: 12px; color: #666666; }
        QLabel#activityCounts { font-size: 12px; color: #666666; }
        """
        selected = """
        QFrame#activityCard {
            border: 2px solid #F29B38;
            border-radius: 12px;
            background: #FFF3E3;
        }
        """
        self.setStyleSheet(base + (selected if self._selected else ""))

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item.id)
        super().mousePressEvent(event)


class ActivityListPanel(QWidget):
    """
    左側活動清單面板：
    - 搜尋列（關鍵字：編號/名稱）
    - 活動卡片列表（可點選）
    """
    activity_selected = pyqtSignal(str)   # emit activity_id
    search_requested = pyqtSignal(str)    # emit keyword

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[ActivityListItem] = []
        self._cards: List[ActivityCard] = []
        self._selected_id: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        lbl = QLabel("活動清單")
        lbl.setObjectName("panelTitle")
        header.addWidget(lbl)
        header.addStretch(1)
        root.addLayout(header)

        # 搜尋列
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜尋活動（編號/名稱）")
        self.search_edit.returnPressed.connect(self._on_search)

        self.btn_search = QPushButton("搜尋")
        self.btn_search.clicked.connect(self._on_search)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._on_clear)

        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.btn_search, 0)
        search_row.addWidget(self.btn_clear, 0)
        root.addLayout(search_row)

        # Scroll area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, 1)

        # Style
        self.setStyleSheet("""
            QLabel#panelTitle { font-size: 16px; font-weight: 800; }
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #E6D8C7;
                border-radius: 12px;
                background: #FFFFFF;
            }
            QPushButton {
                padding: 9px 14px;
                border: 1px solid #E6D8C7;
                border-radius: 12px;
                background: #FFFFFF;
            }
            QPushButton:hover { border: 1px solid #F0B060; background: #FFF7EE; }
        """)

    # ---------- public API ----------
    def set_activities(self, items: List[ActivityListItem], auto_select_first: bool = True):
        self._items = items or []
        self._rebuild_cards()

        if auto_select_first and self._items:
            self.set_selected(self._items[0].id)

    def set_selected(self, activity_id: str):
        self._selected_id = activity_id
        for c in self._cards:
            c.set_selected(c.item.id == activity_id)
        self.activity_selected.emit(activity_id)

    # ---------- internal ----------
    def _rebuild_cards(self):
        # clear old (remove all except stretch)
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self._cards = []
        for it in self._items:
            card = ActivityCard(it)
            card.clicked.connect(self.set_selected)
            self._cards.append(card)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

    def _on_search(self):
        keyword = self.search_edit.text().strip()
        self.search_requested.emit(keyword)

    def _on_clear(self):
        self.search_edit.clear()
        self.search_requested.emit("")
