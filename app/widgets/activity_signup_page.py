from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QGroupBox, QSizePolicy,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QScrollArea, QGridLayout, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt

from app.widgets.activity_person_panel import ActivityPersonPanel
from app.widgets.activity_plan_panel import ActivityPlanPanel
from app.utils.id_utils import (
    compute_display_status,
    parse_date_str_to_qdate,
)


# -----------------------------
# 活動卡片（新）
# -----------------------------
class _ActivityCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, activity: dict, parent=None):
        super().__init__(parent)
        self.activity = activity or {}
        self._selected = False
        self._build_ui()
        self._apply_style()
        self._disabled = False

    def _get_signup_status(self):
        """
        回傳 (label_text, is_open, status_key)
        status_key:
        - open: 可報名（進行中）
        - not_started: 未開始（但仍可報名/可點）
        - expired: 已過期（不可點）
        """
        start_s = self.activity.get("activity_start_date")
        end_s = self.activity.get("activity_end_date")

        if not start_s or not end_s:
            dr = self.activity.get("date_range", "")
            if "~" in dr:
                start_s, end_s = [x.strip() for x in dr.split("~", 1)]

        start_q = parse_date_str_to_qdate(start_s)
        end_q = parse_date_str_to_qdate(end_s)

        if not start_q or not end_q:
            return "可報名", True, "open"

        status = compute_display_status(start_q, end_q)  # 未開始 / 進行中 / 已結束

        if status == "未開始":
            return "未開始", True, "not_started"   # ✅ 仍可點、仍是橘色系
        if status == "已結束":
            return "已過期", False, "expired"
        return "可報名", True, "open"


    def _build_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("activityCard")
        self.setFrameShape(QFrame.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        title = (self.activity.get("title") or self.activity.get("name") or "未命名活動").strip()
        code = (self.activity.get("code") or self.activity.get("id") or "").strip()
        date_range = (self.activity.get("date_range") or "").strip()

        status_text, is_open, status_key = self._get_signup_status()
        self.lbl_tag = QLabel(status_text)
        self.lbl_tag.setStyleSheet("""
            QLabel{
                padding: 2px 8px;
                border-radius: 10px;
                background: rgba(251,191,36,0.18);
                border: 1px solid rgba(251,191,36,0.35);
                color: #7a4a00;
                font-weight: 800;
                font-size: 12px;
            }
        """)

        # self.lbl_title = QLabel(f"{title}（{code}）" if code else title)
        # self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 900;")


        self.lbl_title = QLabel()
        self.lbl_title.setTextFormat(Qt.RichText)

        if code:
            self.lbl_title.setText(
                f"""
                <span style="font-size:14px; font-weight:900; color:#111;">
                    {title}
                </span>
                <span style="font-size:11px; color:#9CA3AF; margin-left:6px;">
                    （{code}）
                </span>
                """
            )
        else:
            self.lbl_title.setText(title)





        self.lbl_meta = QLabel(date_range)
        self.lbl_meta.setStyleSheet("color:#666666; font-size: 12px;")

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_row.addWidget(self.lbl_title, 1)
        title_row.addStretch(1)
        title_row.addWidget(self.lbl_tag, 0, Qt.AlignRight | Qt.AlignTop)

        root.addLayout(title_row)
        root.addWidget(self.lbl_meta)


        self.setMinimumHeight(84)

    def set_selected(self, selected: bool):
        if self._disabled:
            self._selected = False
        else:
            self._selected = bool(selected)
        self._apply_style()


    def _apply_style(self):
        status_text, is_open, status_key = self._get_signup_status()
        self.lbl_tag.setText(status_text)

        # 只有 expired 才 disabled
        self._disabled = (status_key == "expired")

        # --- tag style ---
        if status_key == "expired":
            # 灰色（不可點）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 8px;
                    border-radius: 10px;
                    background: rgba(107,114,128,0.12);
                    border: 1px solid rgba(107,114,128,0.25);
                    color: #374151;
                    font-weight: 800;
                    font-size: 12px;
                }
            """)
        elif status_key == "not_started":
            # 未開始：藍色（跟你圖一樣的感覺）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 10px;
                    border-radius: 12px;
                    background: rgba(59,130,246,0.10);   /* 淡藍底 */
                    border: 1px solid rgba(59,130,246,0.25);
                    color: #1E3A8A;                      /* 深藍字 */
                    font-weight: 800;
                    font-size: 12px;
                }
            """)
        else:
            # open：原本橘色（可報名）
            self.lbl_tag.setStyleSheet("""
                QLabel{
                    padding: 2px 8px;
                    border-radius: 10px;
                    background: rgba(251,191,36,0.18);
                    border: 1px solid rgba(251,191,36,0.35);
                    color: #7a4a00;
                    font-weight: 800;
                    font-size: 12px;
                }
            """)

        # --- card style ---
        if self._disabled:
            self.setCursor(Qt.ArrowCursor)
            self.setStyleSheet("""
                QFrame#activityCard{
                    background: rgba(249,250,251,1.0);
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                }
                QLabel{
                    color: #6B7280;
                }
            """)
            self._selected = False
            return

        # is_open == True（open / not_started 都會到這裡）
        self.setCursor(Qt.PointingHandCursor)

        if self._selected:
            self.setStyleSheet("""
                QFrame#activityCard{
                    background:#FFFFFF;
                    border: 2px solid rgba(245,158,11,0.70);
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#activityCard{
                    background:#FFFFFF;
                    border: 1px solid #E6E6E6;
                    border-radius: 12px;
                }
                QFrame#activityCard:hover{
                    border: 1px solid rgba(245,158,11,0.45);
                }
            """)



    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self._disabled:
            return
        self.clicked.emit(self.activity)



class ActivitySignupPage(QWidget):
    """
    活動報名頁（改成 HTML demo 流程）：
    Step 1. 上方：先選擇活動（卡片清單）
    Step 2. 下方：左人員 / 右方案（未選活動前全部鎖住）
    """
    request_back_to_manage = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller

        self.activity_data = None            # 目前選中的活動 dict
        self._activity_list = []             # 所有活動（list[dict]）
        self._activity_cards = []            # list[_ActivityCard]

        self._build_ui()
        self._load_activities()

        # 預設：鎖住報名區
        self._lock_signup_area(True)

        self._wire_person_panel()
        self._load_activities()

    # =========================
    # 左下：人員面板接線（搜尋 / 顯示結果）
    # =========================
    def _wire_person_panel(self):
        """把 ActivityPersonPanel 的搜尋事件接到 controller。"""
        if not hasattr(self, "person_panel"):
            return

        # ActivityPersonPanel 建議提供：search_requested = pyqtSignal(str)
        if hasattr(self.person_panel, "search_requested"):
            try:
                self.person_panel.search_requested.connect(self._on_person_search_requested)
            except Exception:
                pass

    def _on_person_search_requested(self, keyword: str):
        """左下搜尋：呼叫 controller.search_people_unified_dedup_name_birthday → 回填到 person_panel.show_search_results。"""
        kw = (keyword or "").strip()

        # 空字串：清空結果（如果 panel 支援）
        if not kw:
            if hasattr(self.person_panel, "show_search_results"):
                self.person_panel.show_search_results([])
            return

        try:
            people = self.controller.search_people_unified_dedup_name_birthday(kw)
        except Exception as e:
            QMessageBox.warning(self, "搜尋失敗", f"搜尋人員資料時發生錯誤：\n{e}")
            people = []

        # 兼容：確保 UI 端至少拿得到 phone_mobile
        normalized = []
        for p in (people or []):
            if not isinstance(p, dict):
                continue
            if not p.get("phone_mobile"):
                p["phone_mobile"] = p.get("phone") or p.get("phone_home") or ""
            normalized.append(p)

        if hasattr(self.person_panel, "show_search_results"):
            self.person_panel.show_search_results(normalized)
        else:
            QMessageBox.information(self, "尚未支援", "ActivityPersonPanel 尚未提供 show_search_results(people)")


    # =========================
    # 右下：存入
    # =========================
    def _on_save_clicked(self):
        # 1) activity_id：你目前右上角有「目前活動」與活動卡片
        if not self.activity_data or not self.activity_data.get("id"):
            QMessageBox.warning(self, "無法存入", "請先選擇活動")
            return
        activity_id = self.activity_data["id"]

        # 2) person：upsert 拿到 person_id
        try:
            person_payload = self.person_panel.get_person_payload()
            if not person_payload.get("name"):
                QMessageBox.warning(self, "資料不完整", "請先填寫姓名")
                return

            person_id = self.controller.upsert_person(person_payload)  # ✅ 已在 controller 寫好
        except Exception as e:
            QMessageBox.critical(self, "人員存檔失敗", str(e))
            return

        # 3) plans：由右邊面板提供（你需要在 plan panel 寫 get_selected_plans_payload）
        try:
            selected_plans = self.plan_panel.get_selected_plans_payload()
            if not selected_plans:
                QMessageBox.warning(self, "未選方案", "請至少選擇一個方案")
                return
        except Exception as e:
            QMessageBox.critical(self, "方案資料錯誤", str(e))
            return

        # 4) note：如果你右邊有「收據號碼/備註」之類，拿來當 signup note
        note = None
        if hasattr(self, "edit_receipt_no"):
            note = self.edit_receipt_no.text().strip() or None

        # 5) 寫入 DB：signup + signup_plans（controller 已處理交易）
        try:
            signup_id = self.controller.create_activity_signup(
                activity_id=activity_id,
                person_id=person_id,
                selected_plans=selected_plans,
                note=note
            )
            QMessageBox.information(self, "存入成功", f"已完成報名\n報名編號：{signup_id}")

            # 6) 依你 UX 決定：要不要清空右側、清空人員、或保留
            # self.person_panel._clear_form()
            # self.plan_panel.clear_all()

        except Exception as e:
            QMessageBox.critical(self, "存入失敗", str(e))
            return



    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # =========================
        # 上方：活動選擇（第一步）
        # =========================
        top_group = QGroupBox("")
        top_layout = QVBoxLayout(top_group)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(8)

        # 第一列：標題 + badge + 清除
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        lbl_title = QLabel("活動報名")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 900;")

        self.lbl_activity_badge = QLabel("目前活動：未選擇")
        self.lbl_activity_badge.setStyleSheet("""
            QLabel{
                padding: 6px 10px;
                border-radius: 14px;
                background: rgba(245,158,11,0.14);
                border: 1px solid rgba(245,158,11,0.35);
                color: #7a4a00;
                font-weight: 800;
                font-size: 13px;
            }
        """)

        self.btn_clear_activity = QPushButton("清除活動選擇")
        self.btn_clear_activity.clicked.connect(self._clear_selected_activity)
        self.btn_clear_activity.setFixedHeight(34)

        row1.addWidget(lbl_title)
        row1.addWidget(self.lbl_activity_badge)
        row1.addStretch(1)
        row1.addWidget(self.btn_clear_activity)

        top_layout.addLayout(row1)

        # 活動卡片區（Scroll + Grid）
        self.activity_scroll = QScrollArea()
        self.activity_scroll.setWidgetResizable(True)
        self.activity_scroll.setFrameShape(QFrame.NoFrame)

        self.activity_scroll_content = QWidget()
        self.activity_grid = QGridLayout(self.activity_scroll_content)
        self.activity_grid.setContentsMargins(0, 0, 0, 0)
        self.activity_grid.setHorizontalSpacing(10)
        self.activity_grid.setVerticalSpacing(10)

        self.activity_scroll.setWidget(self.activity_scroll_content)
        top_layout.addWidget(self.activity_scroll)

        root.addWidget(top_group, 0)

        # =========================
        # 下方：左右 splitter（第二步以後）
        # =========================
        self.signup_group = QGroupBox("")
        main_layout = QVBoxLayout(self.signup_group)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)

        # ---- 左：搜尋列 + 搜尋結果 + 人員資料 ----
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_title2 = QLabel("搜尋結果")
        lbl_title2.setStyleSheet("font-size: 16px; font-weight: 800;")

        lbl_hint2 = QLabel("點選即可帶入")
        lbl_hint2.setStyleSheet("color:#666666;")

        title_row.addWidget(lbl_title2)
        title_row.addStretch(1)
        title_row.addWidget(lbl_hint2)
  
        self.person_panel = ActivityPersonPanel()
        left_layout.addWidget(self.person_panel, 1)

        splitter.addWidget(self.person_panel)

        # ---- 右：方案面版
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        try:
            self.plan_panel = ActivityPlanPanel(controller=self.controller)
        except TypeError:
            self.plan_panel = ActivityPlanPanel()
            if hasattr(self.plan_panel, "set_controller"):
                self.plan_panel.set_controller(self.controller)

        self.plan_panel.save_clicked.connect(self._on_save_clicked)
        
        # self.plan_panel.save_exit_clicked.connect(self._on_save_exit_clicked)

        right_layout.addWidget(self.plan_panel, 1)

        splitter.addWidget(right_container)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([600, 600])

        main_layout.addWidget(splitter, 1)
        root.addWidget(self.signup_group, 1)

    # =========================
    # 活動：載入 / 卡片渲染 / 選取
    # =========================
    def _load_activities(self):
        try:
            activities = self.controller.list_activities_for_signup()
        except Exception:
            activities = []

        self._activity_list = activities or []
        self._render_activity_cards(self._activity_list)

        has_any = bool(self._activity_list)
        self.btn_clear_activity.setEnabled(has_any)

        # 沒有活動：維持 Step0 狀態
        if not has_any:
            self.set_activity({})


    def _render_activity_cards(self, activities: list):
        # 清空 grid
        while self.activity_grid.count():
            item = self.activity_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._activity_cards = []

        if not activities:
            empty = QLabel("（目前沒有可選活動）")
            empty.setStyleSheet("color:#666666; padding: 10px;")
            self.activity_grid.addWidget(empty, 0, 0, 1, 1)
            return

        # 4 欄的卡片排列（寬度不夠時 Qt 也會擠，但可接受；你也可以後續做 resizeEvent 動態欄數）
        cols = 4
        r = 0
        c = 0
        for a in activities:
            card = _ActivityCard(a)
            card.clicked.connect(self._on_activity_card_clicked)
            self._activity_cards.append(card)

            self.activity_grid.addWidget(card, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self.activity_grid.setRowStretch(r + 1, 1)

    def _on_activity_card_clicked(self, activity: dict):
        if not activity:
            return

        if activity.get("is_open") is False:
            QMessageBox.information(self, "此活動不可報名", "此活動目前狀態為「已結束」，無法新增報名。")
            return

        self.set_activity(activity)


    def _clear_selected_activity(self):
        for c in self._activity_cards:
            c.set_selected(False)

        self.set_activity({})

        # 若列表為空，順手 disable
        self.btn_clear_activity.setEnabled(bool(self._activity_list))


    # =========================
    # Lock / Unlock 報名區
    # =========================
    def _lock_signup_area(self, locked: bool):
        # locked=True → disable 整個報名工作區
        self.signup_group.setEnabled(not locked)

    def _pick_person(self, person: dict):
        if hasattr(self.person_panel, "set_person_data"):
            self.person_panel.set_person_data(person)
        else:
            QMessageBox.information(
                self, "需要接線",
                "ActivityPersonPanel 尚未提供 set_person_data(person: dict) 方法。\n"
                "請在 ActivityPersonPanel 實作後再呼叫帶入。"
            )

    # =========================
    # Public API
    # =========================
    def set_activity(self, activity_data: dict):
        """
        - activity_data={} 表示未選擇（回到 Step0）
        - activity_data 有值：選定活動 → 解鎖 → 載入方案
        """
        self.activity_data = activity_data or {}

        # 更新 badge
        if not self.activity_data:
            self.lbl_activity_badge.setText("目前活動：未選擇")
            self._lock_signup_area(True)

            # 方案區：若你 ActivityPlanPanel 支援清空，可在這裡呼叫
            if hasattr(self.plan_panel, "clear"):
                try:
                    self.plan_panel.clear()
                except Exception:
                    pass
            return

        title = (self.activity_data.get("title") or self.activity_data.get("name") or "未命名活動").strip()
        code = (self.activity_data.get("code") or self.activity_data.get("id") or "").strip()
        self.lbl_activity_badge.setText(f"目前活動：{title}（{code}）" if code else f"目前活動：{title}")

        # 卡片選取樣式同步
        selected_id = self.activity_data.get("id")
        for c in self._activity_cards:
            is_sel = (c.activity.get("id") == selected_id)
            c.set_selected(is_sel)

        # 解鎖報名區
        self._lock_signup_area(False)

        # 載入方案
        if hasattr(self.plan_panel, "load_activity"):
            try:
                self.plan_panel.load_activity(selected_id)
            except Exception as e:
                QMessageBox.warning(self, "載入方案失敗", f"載入方案時發生錯誤：\n{e}")
    
    def showEvent(self, event):
        super().showEvent(event)
        # 每次這個頁面「顯示出來」就重載活動卡片
        self.reload_activities()

    def reload_activities(self, keep_selected: bool = True):
        prev_id = self.activity_data.get("id") if (keep_selected and self.activity_data) else None

        self._load_activities()

        # 重新選回之前選的活動（如果還存在）
        if prev_id:
            for a in self._activity_list:
                if a.get("id") == prev_id:
                    self.set_activity(a)
                    break

    def _on_save_clicked(self):
        # A) activity
        if not self.activity_data or not self.activity_data.get("id"):
            QMessageBox.warning(self, "無法存入", "請先選擇活動")
            return
        activity_id = self.activity_data["id"]

        # B) person (先 upsert，拿到 person_id)
        person_payload = self.person_panel.get_person_payload()
        if not person_payload.get("name"):
            QMessageBox.warning(self, "資料不完整", "請先填寫姓名")
            return

        try:
            person_id = self.controller.upsert_person(person_payload)
        except Exception as e:
            QMessageBox.critical(self, "人員存檔失敗", str(e))
            return

        # C) plans (由 plan_panel 組好 payload)
        try:
            selected_plans = self.plan_panel.get_selected_plans_payload()
        except Exception as e:
            QMessageBox.warning(self, "方案有誤", str(e))
            return

        if not selected_plans:
            QMessageBox.warning(self, "未選方案", "請至少選擇一個方案")
            return

        # D) note / receipt
        receipt_no = self.plan_panel.get_receipt_no()  # 你可以存在 note 或另外欄位
        note = receipt_no or None

        # E) write to DB
        try:
            signup_id = self.controller.create_activity_signup(
                activity_id=activity_id,
                person_id=person_id,
                selected_plans=selected_plans,
                note=note,
            )

            # 組成功訊息（不要顯示 signup_id）
            name = (person_payload.get("name") or "").strip()
            phone = (person_payload.get("phone_mobile") or "").strip()

            selected_items = self.plan_panel.get_selected_items()  # 含 name/qty/amount
            plan_lines = []
            for it in selected_items:
                pname = it.get("name", "")
                qty = int(it.get("qty", 0) or 0)
                amt = int(it.get("amount", 0) or 0)
                plan_lines.append(f"・{pname} × {qty}（{amt} 元）")

            total_amount = self.plan_panel.get_activity_amount()

            msg = (
                "已完成報名\n\n"
                f"報名人：{name}\n"
                f"電話：{phone}\n\n"
                "報名方案：\n"
                + ("\n".join(plan_lines) if plan_lines else "（未選擇方案）")
                + "\n\n"
                f"總金額：{total_amount} 元"
            )

            QMessageBox.information(self, "存入成功", msg)
            self.plan_panel.clear_all()






        except Exception as e:
            QMessageBox.critical(self, "存入失敗", str(e))
            return
                
