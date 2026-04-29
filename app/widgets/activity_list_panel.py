# app/widgets/activity_list_panel.py
from dataclasses import dataclass
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QCheckBox, QMessageBox
)
from datetime import datetime, date
from app.utils.date_utils import make_ymd_validator, is_valid_ymd_text, roc_to_ad_string, ad_to_roc_string

@dataclass
class ActivityListItem:
    id: str
    title: str
    code: str
    date_range: str
    status: str = "—"
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
        self.lbl_status.setProperty("status", self.item.status)

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

                QLabel#activityStatus {
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 10px;
            border: 1px solid #E6D8C7;
            background: #FFF7EE;
            color: #8A6A3B;
        }

        /* 未開始：偏灰/藍灰（冷色、提醒還沒開始） */
        QLabel#activityStatus[status="未開始"] {
            border: 1px solid #D7DDE6;
            background: #F4F6F9;
            color: #5A6B7A;
        }

        /* 進行中：偏橘金（目前的主色） */
        QLabel#activityStatus[status="進行中"] {
            border: 1px solid #F0B060;
            background: #FFF7EE;
            color: #8A6A3B;
        }

        /* 已結束：偏灰棕（降低存在感） */
        QLabel#activityStatus[status="已結束"] {
            border: 1px solid #E3D7C8;
            background: #F7F2EA;
            color: #8A7B6A;
        }

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

    ✅ 本版本：可選擇直接注入 controller，讓此 panel 自己查 DB / 搜尋。
    """
    activity_selected = pyqtSignal(str)   # emit activity_id
    search_requested = pyqtSignal(str)    # emit keyword（保留給外層，如果你未來想改回純 UI）

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller  # ✅ 新增：注入 AppController

        self._items: List[ActivityListItem] = []
        self._cards: List[ActivityCard] = []
        self._selected_id: Optional[str] = None
        self._period_filter: str = "all"  # all / week / month / next_month
        self._build_ui()

        # ✅ 初始化載入活動清單
        if self.controller is not None:
            self.refresh(keyword="")

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
        self.search_edit.setPlaceholderText("搜尋活動（名稱/日期）")
        self.search_edit.returnPressed.connect(self._on_search)

        self.btn_search = QPushButton("搜尋")
        self.btn_search.clicked.connect(self._on_search)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._on_clear)

        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.btn_search, 0)
        search_row.addWidget(self.btn_clear, 0)
        root.addLayout(search_row)

        # 篩選列：本週/本月 + 顯示已結束
        filter_row = QHBoxLayout()
        self.btn_all = QPushButton("全部")
        self.btn_week = QPushButton("本週")
        self.btn_month = QPushButton("本月")
        self.btn_next_month = QPushButton("下個月")
        self.btn_all.setCheckable(True)
        self.btn_week.setCheckable(True)
        self.btn_month.setCheckable(True)
        self.btn_next_month.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(self._on_all_filter_clicked)
        self.btn_week.clicked.connect(self._on_week_filter_clicked)
        self.btn_month.clicked.connect(self._on_month_filter_clicked)
        self.btn_next_month.clicked.connect(self._on_next_month_filter_clicked)

        self.chk_show_ended = QCheckBox("顯示已結束")
        self.chk_show_ended.setChecked(False)
        self.chk_show_ended.stateChanged.connect(lambda _: self._refresh_by_filters())

        filter_row.addWidget(self.btn_all, 0)
        filter_row.addWidget(self.btn_week, 0)
        filter_row.addWidget(self.btn_month, 0)
        filter_row.addWidget(self.btn_next_month, 0)
        filter_row.addStretch(1)
        filter_row.addWidget(self.chk_show_ended, 0)
        root.addLayout(filter_row)

        # 自訂日期區間
        range_row = QHBoxLayout()
        self.range_start = QLineEdit()
        self.range_end = QLineEdit()
        ymd_validator = make_ymd_validator(self)
        self.range_start.setValidator(ymd_validator)
        self.range_end.setValidator(ymd_validator)
        self.range_start.setPlaceholderText("起日 YYY/MM/DD(民國)")
        self.range_end.setPlaceholderText("迄日 YYY/MM/DD(民國)")

        self.btn_apply_range = QPushButton("查詢")
        self.btn_apply_range.clicked.connect(self._on_apply_range)

        range_row.addWidget(QLabel("起日"), 0)
        range_row.addWidget(self.range_start, 1)
        range_row.addWidget(QLabel("迄日"), 0)
        range_row.addWidget(self.range_end, 1)
        range_row.addWidget(self.btn_apply_range, 0)
        root.addLayout(range_row)

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
        elif not self._items:
            # 清空選取
            self._selected_id = None
            self.activity_selected.emit("") 

    def set_selected(self, activity_id: str):
        self._selected_id = activity_id
        for c in self._cards:
            c.set_selected(c.item.id == activity_id)
        self.activity_selected.emit(activity_id)

    def refresh(self, keyword: str = ""):
        """
        ✅ 對外提供：刷新清單（用 controller 查 DB）
        """
        if self.controller is None:
            # 沒有 controller 就只 emit，讓外層自己接
            self.search_requested.emit(keyword)
            return

        rows = self._fetch_activities(keyword)
        items = [self._map_activity_row_to_item(r) for r in rows]
        self.set_activities(items, auto_select_first=True)

    def refresh_current_filters(self):
        keyword = self.search_edit.text().strip() if hasattr(self, "search_edit") else ""
        self.refresh(keyword)

    # ---------- internal ----------
    def _fetch_activities(self, keyword: str):
        """
        透過 controller 查活動資料（新 schema）
        """
        start_date = self._normalized_date(self.range_start.text().strip()) if hasattr(self, "range_start") else None
        end_date = self._normalized_date(self.range_end.text().strip()) if hasattr(self, "range_end") else None
        kw = (keyword or "").strip()
        rows = self.controller.get_activities_for_manage(
            keyword=kw,
            period_filter=self._period_filter,
            include_ended=self.chk_show_ended.isChecked(),
            start_date=start_date,
            end_date=end_date,
        )
        return sorted(rows, key=self._activity_nearness_key)

    def _map_activity_row_to_item(self, row: dict) -> ActivityListItem:
        """
        New schema row(dict) -> ActivityListItem
        activities 欄位：
          id, name, activity_start_date, activity_end_date, note, status
        """
        activity_id = row.get("id", "")
        title = row.get("name", "") or ""

        start_date = ad_to_roc_string(row.get("activity_start_date", "") or "")
        end_date = ad_to_roc_string(row.get("activity_end_date", "") or "")

        # 卡片上顯示日期區間
        if start_date and end_date and end_date != start_date:
            date_range = f"{start_date} ~ {end_date}"
        else:
            date_range = start_date or end_date or ""

        status_text = self.compute_display_status(
            start_date,
            end_date,
            row.get("status", 1),
        )


        # code：你新表沒有活動編號，我先用 id 前 8 碼（之後想要正式編號再加欄位）
        code = (activity_id[:8] if activity_id else "—")

        return ActivityListItem(
            id=activity_id,
            title=title,
            code=code,
            date_range=date_range,
            status=status_text,
            plan_count=0,
            signup_count=0
        )

    def _rebuild_cards(self):
        # clear old (remove all)
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
        if not self._validate_range_inputs():
            return
        keyword = self.search_edit.text().strip()
        if self.controller is not None:
            self.refresh(keyword)
            return
        self.search_requested.emit(keyword)

    def _on_clear(self):
        self.search_edit.clear()
        self._period_filter = "all"
        self.btn_all.setChecked(True)
        self.btn_week.setChecked(False)
        self.btn_month.setChecked(False)
        self.btn_next_month.setChecked(False)
        self.chk_show_ended.setChecked(False)
        self.range_start.clear()
        self.range_end.clear()

        if self.controller is not None:
            self.refresh("")
            return

        self.search_requested.emit("")

    def _refresh_by_filters(self):
        keyword = self.search_edit.text().strip()
        self.refresh(keyword)

    def _normalized_date(self, text: str) -> Optional[str]:
        t = (text or "").strip()
        if not t:
            return None
        t_ad = roc_to_ad_string(t, separator="-")
        if not is_valid_ymd_text(t_ad):
            return None
        return t_ad

    def _validate_range_inputs(self) -> bool:
        s = self.range_start.text().strip()
        e = self.range_end.text().strip()
        s_ad = roc_to_ad_string(s, separator="/") if s else ""
        e_ad = roc_to_ad_string(e, separator="/") if e else ""
        if s and not is_valid_ymd_text(s_ad):
            QMessageBox.warning(self, "格式錯誤", "起日請使用 YYY/MM/DD(民國)")
            return False
        if e and not is_valid_ymd_text(e_ad):
            QMessageBox.warning(self, "格式錯誤", "迄日請使用 YYY/MM/DD(民國)")
            return False
        if s_ad and e_ad:
            try:
                ds = datetime.strptime(s_ad.replace("-", "/"), "%Y/%m/%d").date()
                de = datetime.strptime(e_ad.replace("-", "/"), "%Y/%m/%d").date()
                if ds > de:
                    QMessageBox.warning(self, "區間錯誤", "起日不可大於迄日")
                    return False
            except Exception:
                QMessageBox.warning(self, "格式錯誤", "日期請使用 YYY/MM/DD(民國)")
                return False
        return True

    def _on_apply_range(self):
        if not self._validate_range_inputs():
            return
        self._refresh_by_filters()

    def _on_all_filter_clicked(self):
        self._period_filter = "all"
        self.btn_all.setChecked(True)
        self.btn_week.setChecked(False)
        self.btn_month.setChecked(False)
        self.btn_next_month.setChecked(False)
        self._refresh_by_filters()

    def _on_week_filter_clicked(self):
        self._period_filter = "week" if self.btn_week.isChecked() else "all"
        if self.btn_week.isChecked():
            self.btn_all.setChecked(False)
            self.btn_month.setChecked(False)
            self.btn_next_month.setChecked(False)
        else:
            self.btn_all.setChecked(True)
        self._refresh_by_filters()

    def _on_month_filter_clicked(self):
        self._period_filter = "month" if self.btn_month.isChecked() else "all"
        if self.btn_month.isChecked():
            self.btn_all.setChecked(False)
            self.btn_week.setChecked(False)
            self.btn_next_month.setChecked(False)
        else:
            self.btn_all.setChecked(True)
        self._refresh_by_filters()

    def _on_next_month_filter_clicked(self):
        self._period_filter = "next_month" if self.btn_next_month.isChecked() else "all"
        if self.btn_next_month.isChecked():
            self.btn_all.setChecked(False)
            self.btn_week.setChecked(False)
            self.btn_month.setChecked(False)
        else:
            self.btn_all.setChecked(True)
        self._refresh_by_filters()

    def _parse_date_any(self, s: str) -> Optional[date]:
        if not s:
            return None
        s = str(s).strip()
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    def _parse_datetime_any(self, s: str) -> Optional[datetime]:
        if not s:
            return None
        text = str(s).strip()
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                pass
        return None

    def _activity_nearness_key(self, row: dict):
        """
        依「距今天近」排序：
        1) 與今天天數差絕對值由小到大（近到遠）
        2) 同距離時，優先未來/今日，再來過去
        3) 再用活動起日、建立時間做穩定排序
        """
        start_dt = self._parse_date_any(row.get("activity_start_date", ""))
        created_dt = self._parse_datetime_any(row.get("created_at", ""))
        if start_dt is None:
            return (10**9, 1, date.max, datetime.max)

        today = date.today()
        delta = (start_dt - today).days
        return (
            abs(delta),
            0 if delta >= 0 else 1,
            start_dt,
            created_dt or datetime.min,
        )

    def compute_display_status(self, start: str, end: str, status_int) -> str:
        # 若 DB 明確標 0：視為已結束/停用（手動結束）
        try:
            if int(status_int) == 0:
                return "已結束"
        except Exception:
            pass

        d0 = self._parse_date_any(start)
        d1 = self._parse_date_any(end)
        today = date.today()

        if d0 and today < d0:
            return "未開始"
        if d1 and today > d1:
            return "已結束"
        return "進行中"
