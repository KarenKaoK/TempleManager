from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from app.widgets.activity_list_panel import ActivityListPanel, ActivityListItem
from app.widgets.activity_detail_panel import ActivityDetailPanel


class ActivityManagePage(QWidget):
    request_close = pyqtSignal()
    request_open_signup = pyqtSignal(dict)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        upper_group = QGroupBox("")
        root.addWidget(upper_group, 1)

        upper_layout = QVBoxLayout(upper_group)
        upper_layout.setContentsMargins(10, 10, 10, 10)

        h_splitter = QSplitter(Qt.Horizontal)

        # 左：活動清單
        self.activity_list_panel = ActivityListPanel(controller=self.controller)

        h_splitter.addWidget(self.activity_list_panel)

        # 右：新版本（標題/操作 + Tabs：活動/方案、報名狀況）
        self.activity_detail_panel = ActivityDetailPanel(controller=self.controller)
        self.activity_detail_panel.request_back.connect(self.request_close.emit)
        h_splitter.addWidget(self.activity_detail_panel)

        h_splitter.setStretchFactor(0, 4)
        h_splitter.setStretchFactor(1, 6)

        upper_layout.addWidget(h_splitter, 1)

        # self._load_mock_activities()

        # 如果你的 ActivityListPanel 有 signal（例如 activity_selected），這邊接上去
        if hasattr(self.activity_list_panel, "activity_selected"):
            self.activity_list_panel.activity_selected.connect(self.on_activity_selected)
        else:
            # 沒有 signal 的話也沒關係，先用右側 mock 顯示
            pass

        # 新增/儲存活動後 → 刷新左側列表
        self.activity_detail_panel.activity_saved.connect(self.on_activity_saved)


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
                plan_count=4,
                signup_count=2,
            ),
        ]
        self.activity_list_panel.set_activities(items)

        pass 
        # 讓右側先顯示「安座大典」的 mock
        # self.activity_detail_panel.load_mock_activity(activity_id="2")

    def on_activity_selected(self, activity_id: str):
        """
        你 ActivityListPanel 的 signal 如果送 id，
        這裡就切換右側內容（先示範 mock）
        """
        pass
        # self.activity_detail_panel.load_mock_activity(activity_id=activity_id)

    def on_activity_saved(self, activity_id: str):
        # 讓左側 panel 重新抓 DB
        self.activity_list_panel.refresh(keyword="")
        # 並選到剛新增的活動
        self.activity_list_panel.set_selected(activity_id)

