from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QGroupBox, QComboBox, QSizePolicy,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from app.widgets.activity_person_panel import ActivityPersonPanel
from app.widgets.activity_plan_panel import ActivityPlanPanel


class _SearchResultCard(QWidget):
    """搜尋結果卡片：姓名/電話/地址 + 帶入按鈕（長相接近你圖二）"""
    def __init__(self, person: dict, on_pick, parent=None):
        super().__init__(parent)
        self.person = person
        self.on_pick = on_pick

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(4)

        name = person.get("name") or "（未命名）"
        phone = person.get("phone") or ""
        address = person.get("address") or ""

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("font-size: 16px; font-weight: 800;")

        meta = " ｜ ".join([p for p in [phone, address] if p])
        lbl_meta = QLabel(meta)
        lbl_meta.setStyleSheet("color:#666666;")

        left.addWidget(lbl_name)
        left.addWidget(lbl_meta)

        btn_pick = QPushButton("帶入")
        btn_pick.setFixedSize(90, 36)
        btn_pick.clicked.connect(self._handle_pick)

        root.addLayout(left, 1)
        root.addWidget(btn_pick, 0, Qt.AlignRight)

        self.setStyleSheet("""
            QWidget{
                background:#FFFFFF;
                border:1px solid #E6E6E6;
                border-radius:12px;
            }
        """)

    def _handle_pick(self):
        if callable(self.on_pick):
            self.on_pick(self.person)


class ActivitySignupPage(QWidget):
    """
    活動報名頁：
    - 左：人員資料（搜尋/帶入/新增/編輯）
    - 右：先選活動 → 再選該活動的方案 + 金額計算
    """
    request_back_to_manage = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller

        self.activity_data = None           # 目前選中的活動 dict
        self._activity_list = []            # 所有活動（list[dict]）
        self._activity_index_by_id = {}     # activity_id -> combo index

        self._build_ui()
        self._load_activities_into_combo()

        # 預設顯示空的搜尋結果
        self._render_search_results([])

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # =========================
        # 頂部列：目前活動資訊
        # =========================
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.lbl_activity = QLabel("目前活動：未選擇")
        self.lbl_activity.setStyleSheet("font-size: 16px; font-weight: 700;")

        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet("color: #666666;")

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(self.lbl_activity)
        title_box.addWidget(self.lbl_meta)

        top_row.addSpacing(6)
        top_row.addLayout(title_box, 1)
        top_row.addStretch(1)

        root.addLayout(top_row)

        # =========================
        # 主區塊：左右 splitter
        # =========================
        main_group = QGroupBox("")
        main_layout = QVBoxLayout(main_group)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)

        # =========================
        # 左側：搜尋列 + 搜尋結果區塊 + 人員資料面板
        # =========================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # (A) 左上：快速搜尋列（保持你原本那一列的概念）
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        lbl_search = QLabel("快速搜尋")
        lbl_search.setMinimumWidth(70)

        self.edt_quick_search = QLineEdit()
        self.edt_quick_search.setPlaceholderText("輸入姓名或電話，例如：李阿姨 / 0912")
        self.edt_quick_search.returnPressed.connect(self._do_quick_search)

        self.btn_search = QPushButton("搜尋")
        self.btn_search.setFixedSize(72, 32)
        self.btn_search.clicked.connect(self._do_quick_search)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setFixedSize(72, 32)
        self.btn_clear.clicked.connect(self._clear_quick_search)

        search_row.addWidget(lbl_search)
        search_row.addWidget(self.edt_quick_search, 1)
        search_row.addWidget(self.btn_search)
        search_row.addWidget(self.btn_clear)

        left_layout.addLayout(search_row)

        # (B) ✅ 你要的：搜尋結果小區塊（固定在搜尋列下方）
        self.result_group = QGroupBox("")
        rg_layout = QVBoxLayout(self.result_group)
        rg_layout.setContentsMargins(12, 10, 12, 10)
        rg_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_title = QLabel("搜尋結果")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800;")

        lbl_hint = QLabel("點選即可帶入")
        lbl_hint.setStyleSheet("color:#666666;")

        title_row.addWidget(lbl_title)
        title_row.addStretch(1)
        title_row.addWidget(lbl_hint)
        rg_layout.addLayout(title_row)

        self.lst_results = QListWidget()
        self.lst_results.setSpacing(8)
        self.lst_results.setFixedHeight(120)  # ✅ 小區塊高度：像你圖二
        self.lst_results.setStyleSheet("""
            QListWidget{
                background:#FFF7ED;
                border:1px dashed #E9D5B0;
                border-radius:12px;
                padding:10px;
            }
            QListWidget::item{ border:none; }
        """)
        rg_layout.addWidget(self.lst_results)

        left_layout.addWidget(self.result_group)

        # (C) 左下：你原本的人員資料面板（不動）
        self.person_panel = ActivityPersonPanel()
        left_layout.addWidget(self.person_panel, 1)

        splitter.addWidget(left_container)

        # =========================
        # 右側：活動選擇 + 方案面板（你原本的不動）
        # =========================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        activity_group = QGroupBox("活動與方案選擇")
        ag_layout = QVBoxLayout(activity_group)
        ag_layout.setContentsMargins(10, 10, 10, 10)
        ag_layout.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel("選擇活動")
        lbl.setMinimumWidth(70)

        self.cmb_activity = QComboBox()
        self.cmb_activity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cmb_activity.currentIndexChanged.connect(self._on_activity_changed)

        row.addWidget(lbl)
        row.addWidget(self.cmb_activity, 1)
        ag_layout.addLayout(row)

        hint = QLabel("流程：先選活動 → 再選方案（可多選 + 數量）→ 自動計算")
        hint.setStyleSheet("color: #666666;")
        ag_layout.addWidget(hint)

        right_layout.addWidget(activity_group, 0)

        self.plan_panel = ActivityPlanPanel()
        right_layout.addWidget(self.plan_panel, 1)

        splitter.addWidget(right_container)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([600, 600])

        main_layout.addWidget(splitter, 1)
        root.addWidget(main_group, 1)

    # =========================
    # Quick Search
    # =========================
    def _clear_quick_search(self):
        self.edt_quick_search.setText("")
        self._render_search_results([])

    def _do_quick_search(self):
        keyword = (self.edt_quick_search.text() or "").strip()
        if not keyword:
            self._render_search_results([])
            return

        # 你需要 controller 提供：search_people_for_activity(keyword) -> list[dict]
        try:
            results = self.controller.search_people_for_activity(keyword)
        except Exception as e:
            QMessageBox.warning(self, "搜尋失敗", f"搜尋時發生錯誤：\n{e}")
            results = []

        self._render_search_results(results or [])

    def _render_search_results(self, results: list):
        """把結果顯示在『搜尋列下方的小區塊』，長相類似你圖二"""
        self.lst_results.clear()

        if not results:
            item = QListWidgetItem()
            w = QLabel("尚無搜尋結果（可輸入姓名或電話後按搜尋）")
            w.setStyleSheet("color:#8A6A3A; padding: 6px;")
            item.setSizeHint(w.sizeHint())
            self.lst_results.addItem(item)
            self.lst_results.setItemWidget(item, w)
            return

        for person in results[:10]:
            item = QListWidgetItem()
            card = _SearchResultCard(person, self._pick_person)
            item.setSizeHint(card.sizeHint())
            self.lst_results.addItem(item)
            self.lst_results.setItemWidget(item, card)

    def _pick_person(self, person: dict):
        """點『帶入』後，把資料帶進左側 person_panel"""
        # ✅ 你只要確保 ActivityPersonPanel 有這個方法
        if hasattr(self.person_panel, "set_person_data"):
            self.person_panel.set_person_data(person)
        else:
            QMessageBox.information(
                self, "需要接線",
                "ActivityPersonPanel 尚未提供 set_person_data(person: dict) 方法。\n"
                "請在 ActivityPersonPanel 實作後再呼叫帶入。"
            )

    # =========================
    # Data loading: activities
    # =========================
    def _load_activities_into_combo(self):
        self.cmb_activity.blockSignals(True)
        self.cmb_activity.clear()
        self._activity_list = []
        self._activity_index_by_id = {}

        try:
            activities = self.controller.list_activities_for_signup()
        except Exception:
            activities = []

        self._activity_list = activities or []

        if not self._activity_list:
            self.cmb_activity.addItem("（目前沒有可選活動）", None)
            self.cmb_activity.setEnabled(False)
            self.cmb_activity.blockSignals(False)
            self.set_activity({})
            return

        self.cmb_activity.setEnabled(True)

        for i, a in enumerate(self._activity_list):
            aid = a.get("id")
            title = a.get("title") or "未命名活動"
            code = a.get("code") or ""
            text = f"{title}（{code}）" if code else title
            self.cmb_activity.addItem(text, aid)
            if aid is not None:
                self._activity_index_by_id[aid] = i

        self.cmb_activity.blockSignals(False)

        # 預設選第一個
        self.cmb_activity.setCurrentIndex(0)
        self._apply_activity_by_index(0)

    def _on_activity_changed(self, index: int):
        self._apply_activity_by_index(index)

    def _apply_activity_by_index(self, index: int):
        if index < 0:
            return
        aid = self.cmb_activity.itemData(index)
        if not aid:
            self.set_activity({})
            return

        activity = None
        for a in self._activity_list:
            if a.get("id") == aid:
                activity = a
                break

        self.set_activity(activity or {})

        if hasattr(self.plan_panel, "load_activity"):
            self.plan_panel.load_activity(aid)

    # =========================
    # Public API
    # =========================
    def set_activity(self, activity_data: dict):
        self.activity_data = activity_data or {}

        title = self.activity_data.get("title") or "未選擇"
        code = self.activity_data.get("code") or ""
        date_range = self.activity_data.get("date_range") or ""
        status = self.activity_data.get("status") or ""

        self.lbl_activity.setText(f"目前活動：{title}")
        meta_parts = [p for p in [code, date_range, status] if p]
        self.lbl_meta.setText(" ｜ ".join(meta_parts))

        aid = self.activity_data.get("id")
        if aid and aid in self._activity_index_by_id:
            idx = self._activity_index_by_id[aid]
            if self.cmb_activity.currentIndex() != idx:
                self.cmb_activity.blockSignals(True)
                self.cmb_activity.setCurrentIndex(idx)
                self.cmb_activity.blockSignals(False)
