from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QDateEdit, QFormLayout, QFrame, QSizePolicy,
    QGridLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal


class ActivityPersonPanel(QWidget):
    search_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Header row =====
        header_row = QHBoxLayout()
        title = QLabel("參加人員資料")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")

        header_row.addWidget(title)
        header_row.addStretch(1)

        root.addLayout(header_row)

        # ===== Divider line =====
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #E6E6E6;")
        root.addWidget(line)

        # ===== Quick search row =====
        quick_row = QHBoxLayout()
        lbl_quick = QLabel("快速搜尋")
        lbl_quick.setStyleSheet("color: #666; font-weight: 600;")
        lbl_quick.setFixedWidth(70)

        self.edit_quick = QLineEdit()
        self.edit_quick.setPlaceholderText("輸入姓名或電話，例如：李阿姨 / 0912")
        self.edit_quick.setMinimumHeight(34)

        self.btn_search = QPushButton("搜尋")
        self.btn_clear = QPushButton("清空")
        for b in (self.btn_search, self.btn_clear):
            b.setMinimumHeight(34)
            b.setCursor(Qt.PointingHandCursor)

        quick_row.addWidget(lbl_quick)
        quick_row.addWidget(self.edit_quick, 1)
        quick_row.addWidget(self.btn_search)
        quick_row.addWidget(self.btn_clear)
        root.addLayout(quick_row)

        self.btn_search.clicked.connect(self._emit_search)
        self.btn_clear.clicked.connect(self._clear_form)

        # ===== 搜尋結果清單（點選後帶入資料）=====

        self.list_results = QListWidget()

        # 🔑 關鍵：限制搜尋結果高度（約 5 列）
        self.list_results.setMaximumHeight(160)
        self.list_results.setMinimumHeight(0)

        # 出現 scrollbar，而不是撐開畫面
        self.list_results.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 預設不顯示
        self.list_results.hide()

        self.list_results.itemClicked.connect(self._on_pick_person)

        root.addWidget(self.list_results)



        # ===== Form wrapper =====
        form_wrap = QFrame()
        form_wrap.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E8E8E8;
                border-radius: 10px;
            }
        """)
        form_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer = QVBoxLayout(form_wrap)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(8)

        # ===== 建立欄位元件 =====
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("例如：李阿姨")

        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["女", "男", "其他"])

        self.edit_phone = QLineEdit()
        self.edit_phone.setPlaceholderText("例如：0912-345-678")

        self.date_birth_ad = QDateEdit()
        self.date_birth_ad.setCalendarPopup(True)
        self.date_birth_ad.setDisplayFormat("yyyy/MM/dd")
        self.date_birth_ad.setDate(QDate.currentDate())

        self.edit_birth_lunar = QLineEdit()
        self.edit_birth_lunar.setPlaceholderText("例如：農曆正月十五")

        self.combo_birth_time = QComboBox()
        self.combo_birth_time.addItems([
            "吉時", "子時(23-01)", "丑時(01-03)", "寅時(03-05)", "卯時(05-07)",
            "辰時(07-09)", "巳時(09-11)", "午時(11-13)", "未時(13-15)",
            "申時(15-17)", "酉時(17-19)", "戌時(19-21)", "亥時(21-23)"
        ])

        self.combo_zodiac = QComboBox()
        self.combo_zodiac.addItems(["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"])

        # ✅ 地址/備註：先用 QLineEdit（最穩、最像單行）
        self.edit_address = QLineEdit()
        self.edit_address.setPlaceholderText("例如：新北市...")

        self.edit_note = QLineEdit()
        self.edit_note.setPlaceholderText("例如：家人一起報名、特殊需求")

        # ===== 統一樣式（一次套在 form_wrap，避免 per-widget 互相覆蓋）=====
        form_wrap.setStyleSheet(form_wrap.styleSheet() + """
            QLineEdit, QComboBox, QDateEdit {
                background: #FFFFFF;
                border: 1px solid #DADADA;
                border-radius: 8px;
                padding: 6px 10px;
                color: #222;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #F29B38;
            }
            QComboBox::drop-down, QDateEdit::drop-down {
                border: 0px;
                width: 22px;
            }
        """)

        # ✅ 高度/SizePolicy：不要 fixed，避免被 splitter 壓縮時爆炸
        FIELD_H = 36
        def _fix_field(w):
            w.setMinimumHeight(FIELD_H)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for w in (
            self.edit_name, self.edit_phone, self.date_birth_ad,
            self.combo_birth_time, self.combo_gender, self.edit_birth_lunar,
            self.combo_zodiac, self.edit_address, self.edit_note
        ):
            _fix_field(w)

        self.edit_birth_lunar.setMinimumWidth(260)
        
        MIN_W = 240
        self.edit_name.setMinimumWidth(MIN_W)
        self.edit_phone.setMinimumWidth(MIN_W)
        self.edit_address.setMinimumWidth(MIN_W)


        # ===== 主 Grid：一個 grid 放完全部（穩定，不會上下兩段打架）=====
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)   # ✅ 兩欄中間距離拉開
        grid.setVerticalSpacing(18)     # ✅ 每列不要擠

        LABEL_W = 92

        def _label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFixedWidth(LABEL_W)
            lbl.setMinimumHeight(FIELD_H)  # ✅ 跟輸入框同一個高度基準
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setStyleSheet("""
                QLabel {
                    color:#333;
                    font-weight:600;
                    background:transparent;
                    border:none;
                    padding-right: 6px;   /* ✅ 讓文字離輸入框更自然 */
                }
            """)
            return lbl


        # Row 0
        grid.addWidget(_label("姓名"), 0, 0)
        grid.addWidget(self.edit_name, 0, 1)
        grid.addWidget(_label("性別"), 0, 2)
        grid.addWidget(self.combo_gender, 0, 3)

        # Row 1
        grid.addWidget(_label("電話"), 1, 0)
        grid.addWidget(self.edit_phone, 1, 1)
        grid.addWidget(_label("生肖"), 1, 2)
        grid.addWidget(self.combo_zodiac, 1, 3)

        # Row 2
        grid.addWidget(_label("國曆生日"), 2, 0)
        grid.addWidget(self.date_birth_ad, 2, 1)
        grid.addWidget(_label("農曆生日"), 2, 2)
        grid.addWidget(self.edit_birth_lunar, 2, 3)

        # Row 3
        grid.addWidget(_label("時辰"), 3, 0)
        grid.addWidget(self.combo_birth_time, 3, 1)

        # Row 4（全寬）
        grid.addWidget(_label("地址"), 4, 0)
        grid.addWidget(self.edit_address, 4, 1, 1, 3)

        # Row 5（全寬）
        grid.addWidget(_label("備註"), 5, 0)
        grid.addWidget(self.edit_note, 5, 1, 1, 3)

        # ✅ 欄位吃空間，label 不擠
        grid.setColumnStretch(0, 0)  # label
        grid.setColumnStretch(1, 1)  # input
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)
        grid.setColumnMinimumWidth(0, LABEL_W)
        grid.setColumnMinimumWidth(2, LABEL_W)

        grid.setRowStretch(6, 1)

        outer.addLayout(grid)
        root.addWidget(form_wrap, 1)

    


    def _emit_search(self):
        keyword = self.edit_quick.text().strip()
        if keyword:
            self.search_requested.emit(keyword)

    def _clear_form(self):
        self.edit_quick.clear()
        self.edit_name.clear()
        self.edit_phone.clear()
        self.edit_birth_lunar.clear()
        self.edit_address.clear()
        self.edit_note.clear()

    def show_search_results(self, people: list[dict]):
        self.list_results.clear()
        for p in people:
            item = QListWidgetItem(f"{p['name']}（{p.get('phone_mobile','')}）")
            item.setData(Qt.UserRole, p)
            self.list_results.addItem(item)
        self.list_results.setVisible(bool(people))

    def _on_pick_person(self, item):
        data = item.data(Qt.UserRole)

        self.edit_name.setText(data.get("name", ""))
        self.edit_phone.setText(data.get("phone_mobile", ""))
        self.edit_birth_lunar.setText(data.get("birthday_lunar", ""))
        self.edit_address.setText(data.get("address", ""))
        self.edit_note.setText(data.get("note", ""))

        self.list_results.hide()

    def get_person_payload(self) -> dict:
        return {
            "name": self.edit_name.text().strip(),
            "gender": self.combo_gender.currentText(),
            "phone_mobile": self.edit_phone.text().strip(),
            "birthday_ad": self.date_birth_ad.date().toString("yyyy-MM-dd"),
            "birthday_lunar": self.edit_birth_lunar.text().strip(),
            "birth_time": self.combo_birth_time.currentText(),
            "zodiac": self.combo_zodiac.currentText(),
            "address": self.edit_address.text().strip(),
            "note": self.edit_note.text().strip(),
        }



