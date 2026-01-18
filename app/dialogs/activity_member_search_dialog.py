# app/dialogs/activity_member_search_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QDateEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import QDate, Qt, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont

# Custom QDateEdit for ROC year display
class RocDateEdit(QDateEdit):
    def __init__(self, date=QDate.currentDate(), parent=None):
        super().__init__(date, parent)
        self.setCalendarPopup(True)
        # 內部使用標準西元格式，但顯示會被 textFromDateTime 覆寫
        self.setDisplayFormat("yyyy/MM/dd") 

    def textFromDateTime(self, datetime_obj):
        # datetime_obj 是 QDateTime，我們需要其 QDate 部分
        gregorian_date = datetime_obj.date()
        
        year = gregorian_date.year()
        month = gregorian_date.month()
        day = gregorian_date.day()
        
        roc_year = year - 1911
        
        # 處理民國紀元前的日期，或顯示為西元
        if roc_year < 1:
            return gregorian_date.toString("yyyy/MM/dd")
        
        return f"{roc_year:03d}/{month:02d}/{day:02d}"
import uuid
from datetime import datetime
import re

class ActivityMemberSearchDialog(QDialog):
    # 定義信號，用於通知父視窗新增成功
    signup_added = pyqtSignal(dict)
    
    def __init__(self, controller, activity_data=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.activity_data = activity_data or {}
        self.activity_items = []
        self.total_amount = 0
        self.search_results = []  # 儲存搜尋結果
        
        self.setWindowTitle("活動報名 - 人員搜尋")
        self.setMinimumSize(1400, 900)
        self.setModal(True)
        
        # 設定整體字體大小
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)
        
        self.setup_ui()
        self.load_activity_items()
        
        # 設定Enter鍵事件處理
        self.setup_key_events()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 活動名稱標題
        activity_name = self.activity_data.get('activity_name', '未選擇活動')
        title_label = QLabel(f"活動名稱: {activity_name}")
        title_label.setStyleSheet("color: red; font-size: 20px; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 主要內容區域
        main_layout = QHBoxLayout()
        
        # 左半邊：人員搜尋和資料輸入
        left_group = self.create_search_and_form_section()
        main_layout.addWidget(left_group, 2)
        
        # 右半邊：活動項目選擇
        right_group = self.create_activity_items_section()
        main_layout.addWidget(right_group, 1)
        
        layout.addLayout(main_layout)
        
        # 底部按鈕
        button_layout = self.create_buttons()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def create_search_and_form_section(self):
        group = QGroupBox("人員搜尋與資料輸入")
        group.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout = QVBoxLayout()
        
        # 搜尋區域
        search_group = QGroupBox("人員搜尋")
        search_group.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #f0f8ff;")
        search_layout = QVBoxLayout()
        
        # 搜尋輸入框
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("姓名或電話:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("請輸入姓名或聯絡電話進行搜尋")
        self.search_input.returnPressed.connect(self.search_member)
        search_input_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍 搜尋")
        self.search_btn.setStyleSheet("font-size: 14px;")
        self.search_btn.clicked.connect(self.search_member)
        search_input_layout.addWidget(self.search_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # 搜尋結果表格
        self.search_results_table = QTableWidget()
        self.search_results_table.setColumnCount(6)
        self.search_results_table.setHorizontalHeaderLabels([
            "姓名", "性別", "電話", "地址", "生日", "生肖"
        ])
        
        # 設定表格樣式
        header = self.search_results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.search_results_table.setStyleSheet("font-size: 13px;")
        self.search_results_table.setMaximumHeight(180)
        self.search_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 點擊搜尋結果時自動填入表單
        self.search_results_table.itemSelectionChanged.connect(self.on_search_result_selected)
        
        search_layout.addWidget(self.search_results_table)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # 分隔線
        separator = QLabel("─" * 50)
        separator.setAlignment(Qt.AlignCenter)
        separator.setStyleSheet("color: #ccc;")
        layout.addWidget(separator)
        
        # 報名者資料表單
        form_group = QGroupBox("報名者資料")
        form_group.setStyleSheet("font-size: 14px; font-weight: bold;")
        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        
        # 左欄
        self.registration_date = QDateEdit()
        self.registration_date.setDate(QDate.currentDate())
        self.registration_date.setCalendarPopup(True)
        form_layout.addWidget(QLabel("登記日期:"), 0, 0)
        form_layout.addWidget(self.registration_date, 0, 1)
        
        self.contact_phone = QLineEdit()
        form_layout.addWidget(QLabel("聯絡電話:"), 1, 0)
        form_layout.addWidget(self.contact_phone, 1, 1)
        
        self.gregorian_birthday = RocDateEdit()
        self.gregorian_birthday.setDate(QDate.currentDate())
        self.gregorian_birthday.dateChanged.connect(self.on_gregorian_date_changed)
        form_layout.addWidget(QLabel("國曆生日:"), 2, 0)
        form_layout.addWidget(self.gregorian_birthday, 2, 1)
        
        self.zodiac = QComboBox()
        self.zodiac.addItems(["未知", "鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"])
        form_layout.addWidget(QLabel("生肖:"), 3, 0)
        form_layout.addWidget(self.zodiac, 3, 1)
        
        self.address = QLineEdit()
        form_layout.addWidget(QLabel("地址:"), 4, 0)
        form_layout.addWidget(self.address, 4, 1)
        
        # 右欄
        self.name = QLineEdit()
        form_layout.addWidget(QLabel("姓名:"), 0, 2)
        form_layout.addWidget(self.name, 0, 3)
        
        self.gender = QComboBox()
        self.gender.addItems(["男", "女"])
        form_layout.addWidget(QLabel("性別:"), 1, 2)
        form_layout.addWidget(self.gender, 1, 3)
        
        self.lunar_birthday = QLineEdit()
        self.lunar_birthday.textChanged.connect(self.on_lunar_date_changed)
        form_layout.addWidget(QLabel("農曆生日:"), 2, 2)
        form_layout.addWidget(self.lunar_birthday, 2, 3)
        
        self.birth_time = QComboBox()
        self.birth_time.addItems(["吉", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"])
        form_layout.addWidget(QLabel("生辰:"), 3, 2)
        form_layout.addWidget(self.birth_time, 3, 3)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 備註說明
        layout.addWidget(QLabel("備註說明:"))
        self.remarks = QTextEdit()
        self.remarks.setMaximumHeight(80)
        layout.addWidget(self.remarks)
        
        group.setLayout(layout)
        return group
        
    def create_activity_items_section(self):
        group = QGroupBox("參加活動項目")
        group.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #f0f0f0;")
        layout = QVBoxLayout()
        
        # 活動項目表格
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["數量", "活動項目", "項目金額"])
        
        # 設定表格樣式
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setStyleSheet("font-size: 14px;")
        
        layout.addWidget(self.items_table)
        
        # 總金額顯示
        self.total_label = QLabel("總金額: $0")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red; margin: 10px;")
        self.total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.total_label)
        
        # 活動費用資料區塊
        fee_group = QGroupBox("活動費用資料")
        fee_group.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        fee_layout = QVBoxLayout()
        
        # 活動金額和收據號碼
        item_layout = QGridLayout()
        self.activity_amount = QLineEdit()
        self.activity_amount.setReadOnly(True)  # 只讀，由右邊計算得出
        item_layout.addWidget(QLabel("活動金額:"), 0, 0)
        item_layout.addWidget(self.activity_amount, 0, 1)
        
        self.receipt_number = QLineEdit()
        item_layout.addWidget(QLabel("收據號碼:"), 1, 0)
        item_layout.addWidget(self.receipt_number, 1, 1)
        
        fee_layout.addLayout(item_layout)
        fee_group.setLayout(fee_layout)
        layout.addWidget(fee_group)
        
        group.setLayout(layout)
        return group
        
    def create_buttons(self):
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 新增下筆按鈕
        self.add_next_btn = QPushButton("新增下筆")
        self.add_next_btn.setStyleSheet("font-size: 16px; padding: 8px;")
        self.add_next_btn.clicked.connect(self.add_next_entry)
        
        # 存入離開按鈕
        self.save_exit_btn = QPushButton("存入離開")
        self.save_exit_btn.setStyleSheet("font-size: 16px; padding: 8px;")
        self.save_exit_btn.clicked.connect(self.save_and_exit)
        
        # 關閉退出按鈕
        self.close_btn = QPushButton("關閉退出")
        self.close_btn.setStyleSheet("font-size: 16px; padding: 8px;")
        self.close_btn.clicked.connect(self.close_dialog)
        
        layout.addWidget(self.add_next_btn)
        layout.addWidget(self.save_exit_btn)
        layout.addWidget(self.close_btn)
        
        return layout
        
    def search_member(self):
        """搜尋人員資料"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "搜尋提示", "請輸入姓名或電話進行搜尋")
            return
            
        try:
            # 搜尋戶長資料
            households = self.controller.search_households(keyword)
            
            # 搜尋戶員資料
            people = self.controller.search_people(keyword)
            
            # 合併搜尋結果
            self.search_results = []
            
            # 處理戶長資料
            for household in households:
                self.search_results.append({
                    'type': '戶長',
                    'id': household.get('id'),
                    'name': household.get('head_name', ''),
                    'gender': household.get('head_gender', ''),
                    'phone': household.get('head_phone_home', '') or household.get('head_phone_mobile', ''),
                    'address': household.get('head_address', ''),
                    'birthday': household.get('head_birthday_ad', ''),
                    'zodiac': household.get('head_zodiac', ''),
                    'birth_lunar': household.get('head_birthday_lunar', ''),
                    'birth_time': household.get('head_birth_time', ''),
                    'email': household.get('head_email', ''),
                    'identity': household.get('head_identity', ''),
                    'note': household.get('head_note', '')
                })
            
            # 處理戶員資料
            for person in people:
                self.search_results.append({
                    'type': '戶員',
                    'id': person.get('id'),
                    'name': person.get('name', ''),
                    'gender': person.get('gender', ''),
                    'phone': person.get('phone_home', '') or person.get('phone_mobile', ''),
                    'address': person.get('address', ''),
                    'birthday': person.get('birthday_ad', ''),
                    'zodiac': person.get('zodiac', ''),
                    'birth_lunar': person.get('birthday_lunar', ''),
                    'birth_time': person.get('birth_time', ''),
                    'email': person.get('email', ''),
                    'identity': person.get('identity', ''),
                    'note': person.get('note', '')
                })
            
            # 更新搜尋結果表格
            self.update_search_results_table()
            
            if not self.search_results:
                QMessageBox.information(self, "搜尋結果", "找不到符合條件的人員資料")
                
        except Exception as e:
            print(f"❌ 搜尋人員時發生錯誤: {e}")
            QMessageBox.critical(self, "搜尋錯誤", f"搜尋時發生錯誤: {str(e)}")
            
    def update_search_results_table(self):
        """更新搜尋結果表格"""
        self.search_results_table.setRowCount(len(self.search_results))
        
        for row, person in enumerate(self.search_results):
            self.search_results_table.setItem(row, 0, QTableWidgetItem(person.get('name', '')))
            self.search_results_table.setItem(row, 1, QTableWidgetItem(person.get('gender', '')))
            self.search_results_table.setItem(row, 2, QTableWidgetItem(person.get('phone', '')))
            self.search_results_table.setItem(row, 3, QTableWidgetItem(person.get('address', '')))
            self.search_results_table.setItem(row, 4, QTableWidgetItem(person.get('birthday', '')))
            self.search_results_table.setItem(row, 5, QTableWidgetItem(person.get('zodiac', '')))
            
    def on_search_result_selected(self):
        """當選擇搜尋結果時，自動填入表單"""
        current_row = self.search_results_table.currentRow()
        if current_row >= 0 and current_row < len(self.search_results):
            person = self.search_results[current_row]
            
            # 填入基本資料
            self.name.setText(person.get('name', ''))
            self.contact_phone.setText(person.get('phone', ''))
            self.address.setText(person.get('address', ''))
            self.remarks.setText(person.get('note', ''))
            
            # 設定性別
            gender = person.get('gender', '')
            if gender in ['男', '女']:
                index = self.gender.findText(gender)
                if index >= 0:
                    self.gender.setCurrentIndex(index)
            
            # 設定生肖
            zodiac = person.get('zodiac', '')
            if zodiac:
                index = self.zodiac.findText(zodiac)
                if index >= 0:
                    self.zodiac.setCurrentIndex(index)
            
            # 設定生辰
            birth_time = person.get('birth_time', '')
            if birth_time:
                index = self.birth_time.findText(birth_time)
                if index >= 0:
                    self.birth_time.setCurrentIndex(index)
            
        # 處理生日
        birthday = person.get('birthday', '')
        if birthday:
            date = self.parse_roc_date(birthday)
            if date:
                self.gregorian_birthday.setDate(date)
            
            # 設定農曆生日
            lunar_birthday = person.get('birth_lunar', '')
            if lunar_birthday:
                self.lunar_birthday.setText(lunar_birthday)
            
            QMessageBox.information(self, "資料載入", f"已載入 {person.get('name', '')} 的資料")
            
    def load_activity_items(self):
        """載入活動項目到右邊表格"""
        if not self.activity_data or not self.controller:
            return
            
        # 從資料庫取得活動的詳細項目
        activity_id = self.activity_data.get('activity_id')
        if activity_id:
            try:
                # 使用 controller 取得活動項目
                activity_data, scheme_rows = self.controller.get_activity_by_id(activity_id)
                
                if scheme_rows:
                    self.items_table.setRowCount(len(scheme_rows))
                    for row, item in enumerate(scheme_rows):
                        # 數量欄位（SpinBox）
                        quantity_spin = QSpinBox()
                        quantity_spin.setMinimum(0)
                        quantity_spin.setMaximum(99)
                        quantity_spin.valueChanged.connect(self.calculate_total)
                        self.items_table.setCellWidget(row, 0, quantity_spin)
                        
                        # 活動項目名稱（使用 scheme_item）
                        item_name = item.get("scheme_item", "")
                        self.items_table.setItem(row, 1, QTableWidgetItem(item_name))
                        
                        # 項目金額
                        amount = item.get("amount", 0)
                        self.items_table.setItem(row, 2, QTableWidgetItem(f"${amount:,.0f}"))
                else:
                    # 如果沒有找到項目，顯示提示
                    self.items_table.setRowCount(1)
                    self.items_table.setItem(0, 1, QTableWidgetItem("此活動暫無項目"))
                    self.items_table.setItem(0, 2, QTableWidgetItem("$0"))
                    
            except Exception as e:
                print(f"❌ 載入活動項目時發生錯誤: {e}")
                # 發生錯誤時顯示提示
                self.items_table.setRowCount(1)
                self.items_table.setItem(0, 1, QTableWidgetItem("載入項目失敗"))
                self.items_table.setItem(0, 2, QTableWidgetItem("$0"))
                
    def calculate_total(self):
        """計算總金額"""
        total = 0
        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 0)
            amount_item = self.items_table.item(row, 2)
            
            if quantity_widget and amount_item:
                quantity = quantity_widget.value()
                amount_text = amount_item.text().replace("$", "").replace(",", "")
                try:
                    amount = int(amount_text)
                    total += quantity * amount
                except ValueError:
                    pass
                    
        self.total_amount = total
        self.total_label.setText(f"總金額: ${total:,}")
        self.activity_amount.setText(f"{total:,}")
        
    def get_signup_data(self):
        """取得報名資料"""
        # 取得選擇的活動項目
        selected_items = []
        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 0)
            item_name = self.items_table.item(row, 1)
            amount_item = self.items_table.item(row, 2)
            
            if quantity_widget and item_name and amount_item:
                quantity = quantity_widget.value()
                if quantity > 0:
                    amount_text = amount_item.text().replace("$", "").replace(",", "")
                    try:
                        amount = int(amount_text)
                        selected_items.append({
                            "item_name": item_name.text(),
                            "quantity": quantity,
                            "amount": amount,
                            "subtotal": quantity * amount
                        })
                    except ValueError:
                        pass
        
        return {
            "activity_id": self.activity_data.get('activity_id'),
            "registration_date": self.registration_date.date().toString("yyyy/MM/dd"),
            "name": self.name.text(),
            "gender": self.gender.currentText(),
            "contact_phone": self.contact_phone.text(),
            "gregorian_birthday": self.convert_to_roc_date(self.gregorian_birthday.date()),
            "lunar_birthday": self.lunar_birthday.text(),
            "zodiac": self.zodiac.currentText(),
            "birth_time": self.birth_time.currentText(),
            "address": self.address.text(),
            "activity_amount": self.total_amount,
            "receipt_number": self.receipt_number.text(),
            "remarks": self.remarks.toPlainText(),
            "selected_items": selected_items
        }
        
    # def add_next_entry(self):
    #     """新增下筆"""
    #     if self.validate_input():
    #         signup_data = self.get_signup_data()
    #         print(f"🔍 準備儲存資料: {signup_data}")
            
    #         # 儲存到資料庫
    #         if self.controller and self.controller.insert_activity_signup(signup_data):
    #             self.signup_added.emit(signup_data)
    #             self.clear_form()
    #             QMessageBox.information(self, "新增成功", f"已成功新增報名人員：{signup_data['name']}")
    #         else:
    #             QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")
    #     else:
    #         QMessageBox.warning(self, "輸入錯誤", "請填寫必要欄位（姓名、聯絡電話、選擇活動項目）11111")

    def add_next_entry(self):
        """新增下筆"""
        ok = self.validate_input()
        msg = ""  # 或你固定提示訊息
        print("====== DEBUG add_next_entry ======")
        print("validate_input ok:", ok)
        print("validate_input msg:", msg)

        # 額外列印目前表單內容
        print("name:", repr(self.name.text()))
        print("phone:", repr(self.contact_phone.text()))
        print("address:", repr(self.address.text()))
        print("total_amount:", self.total_amount)
        print("activity_amount text:", repr(self.activity_amount.text()))

        # 強制把 spinbox 正在輸入的文字 commit 成 value（很常導致 qty 讀到 0）
        for row in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(row, 0)
            if isinstance(w, QSpinBox):
                w.interpretText()

        # 列印每一列的 qty / item / amount
        for row in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(row, 0)
            item = self.items_table.item(row, 1)
            amt_item = self.items_table.item(row, 2)
            print(
                f"row {row} item:", item.text() if item else None,
                "qty:", w.value() if w else None,
                "amount_cell:", amt_item.text() if amt_item else None
            )
        print("====== END DEBUG ======")

        if not ok:
            QMessageBox.warning(self, "輸入錯誤", "請填寫必要欄位（姓名、聯絡電話、選擇活動項目） 1111")
            return

        signup_data = self.get_signup_data()
        print(f"🔍 準備儲存資料: {signup_data}")

        try:
            result = self.controller.insert_activity_signup(signup_data) if self.controller else None
            print("DEBUG insert_activity_signup result:", result)
        except Exception as e:
            print("❌ insert_activity_signup exception:", repr(e))
            QMessageBox.critical(self, "儲存失敗", f"儲存報名資料時發生例外：{e}")
            return

        if result:
            self.signup_added.emit(signup_data)
            self.clear_form()
            QMessageBox.information(self, "新增成功", f"已成功新增報名人員：{signup_data['name']}")
        else:
            QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")

            
    # def save_and_exit(self):
    #     """存入離開"""
    #     if self.validate_input():
    #         signup_data = self.get_signup_data()
    #         print(f"🔍 準備儲存資料: {signup_data}")
            
    #         # 儲存到資料庫
    #         if self.controller and self.controller.insert_activity_signup(signup_data):
    #             self.signup_added.emit(signup_data)
    #             QMessageBox.information(self, "儲存成功", f"已成功儲存報名人員：{signup_data['name']}")
    #             self.accept()
    #         else:
    #             QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")
    #     else:
    #         QMessageBox.warning(self, "輸入錯誤", "請填寫必要欄位（姓名、聯絡電話、選擇活動項目）2222")

    def save_and_exit(self):
        print("🔥 DEBUG: save_and_exit clicked", flush=True)

        ok = self.validate_input()
        print("🔥 DEBUG validate_input:", ok, flush=True)

        if not ok:
            QMessageBox.warning(self, "輸入錯誤", "請填寫必要欄位（姓名、聯絡電話、選擇活動項目）")
            return

        signup_data = self.get_signup_data()
        print("🔍 準備儲存資料:", signup_data, flush=True)

        try:
            result = self.controller.insert_activity_signup(signup_data) if self.controller else None
            print("DEBUG insert_activity_signup result:", result, flush=True)
        except Exception as e:
            print("❌ insert exception:", repr(e), flush=True)
            QMessageBox.critical(self, "儲存失敗", f"例外：{e}")
            return

        if result:
            QMessageBox.information(self, "儲存成功", f"已成功儲存報名人員：{signup_data.get('name','')}")
            self.accept()
        else:
            QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")


            
    def close_dialog(self):
        """關閉退出"""
        self.reject()
        
    def clear_form(self):
        """清空表單"""
        self.name.clear()
        self.contact_phone.clear()
        self.gregorian_birthday.setDate(QDate.currentDate())
        self.lunar_birthday.clear()
        self.address.clear()
        self.receipt_number.clear()
        self.remarks.clear()
        
        # 重置下拉選單
        self.zodiac.setCurrentIndex(0)  # 設為"未知"
        self.birth_time.setCurrentIndex(0)  # 設為"吉"
        
        # 重置數量選擇
        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 0)
            if quantity_widget:
                quantity_widget.setValue(0)
                
        self.calculate_total()
        
    def validate_input(self):
        """驗證輸入"""
        if not self.name.text().strip():
            return False
        if not self.contact_phone.text().strip():
            return False
        return True
        
    def on_gregorian_date_changed(self, date):
        """當國曆日期改變時，自動轉換為農曆並計算生肖"""
        # 簡化的農曆轉換（這裡使用簡化版本，實際應用中可能需要更精確的農曆轉換庫）
        lunar_date = self.convert_to_lunar(date)
        if lunar_date:
            self.lunar_birthday.setText(lunar_date)
            # 計算生肖
            zodiac = self.calculate_zodiac(date)
            if zodiac:
                index = self.zodiac.findText(zodiac)
                if index >= 0:
                    self.zodiac.setCurrentIndex(index)
                    
    def on_lunar_date_changed(self, text):
        """當農曆日期改變時，可以手動修改"""
        # 這裡可以添加農曆日期格式驗證
        pass
        
    def convert_to_roc_date(self, gregorian_date):
        """將西元日期轉換為民國年格式"""
        try:
            year = gregorian_date.year()
            month = gregorian_date.month()
            day = gregorian_date.day()
            roc_year = year - 1911
            return f"{roc_year:03d}/{month:02d}/{day:02d}"
        except:
            return ""
            
    def parse_roc_date(self, date_str):
        """解析民國年日期字串並轉換為QDate"""
        try:
            if not date_str:
                return None
                
            # 處理不同的日期格式
            if '/' in date_str:
                parts = date_str.split('/')
            elif '-' in date_str:
                parts = date_str.split('-')
            else:
                return None
                
            if len(parts) != 3:
                return None
                
            year_str, month, day = parts
            
            # 判斷是否為民國年格式
            if len(year_str) == 2:  # 兩位數民國年 (如 80)
                roc_year = int(year_str)
                year = roc_year + 1911
            elif len(year_str) == 3 and year_str.startswith('0'):  # 三位數民國年 (如 080)
                roc_year = int(year_str)
                year = roc_year + 1911
            elif len(year_str) == 4:  # 西元年格式
                year = int(year_str)
            else:
                return None
                
            return QDate(year, int(month), int(day))
        except:
            return None
            
    def convert_to_lunar(self, gregorian_date):
        """將國曆日期轉換為農曆日期（簡化版本）"""
        # 這裡使用簡化的轉換，實際應用中建議使用專業的農曆轉換庫
        # 例如：lunardate 或 zhdate
        try:
            year = gregorian_date.year()
            month = gregorian_date.month()
            day = gregorian_date.day()
            
            # 簡化的農曆轉換（僅供參考，實際需要更精確的算法）
            # 這裡返回一個示例格式
            return f"{year-1911:03d}/{month:02d}/{day:02d}"  # 民國年格式
        except:
            return ""
            
    def calculate_zodiac(self, date):
        """根據國曆日期計算生肖"""
        try:
            year = date.year()
            # 生肖對應表（以2024年為基準）
            zodiacs = ["龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬", "鼠", "牛", "虎", "兔"]
            # 2024年是龍年
            zodiac_index = (year - 2024) % 12
            return zodiacs[zodiac_index]
        except:
            return "未知"
            
    def setup_key_events(self):
        """設定鍵盤事件處理"""
        # 為所有輸入框設定Enter鍵事件
        input_widgets = [
            self.name, self.contact_phone, self.gregorian_birthday,
            self.lunar_birthday, self.address, self.receipt_number
        ]
        
        for widget in input_widgets:
            if hasattr(widget, 'returnPressed'):
                widget.returnPressed.connect(self.handle_enter_key)
            else:
                # 對於沒有 returnPressed 信號的控件，使用 keyPressEvent
                widget.keyPressEvent = self.create_key_press_handler(widget.keyPressEvent)
                
    def create_key_press_handler(self, original_handler):
        """創建鍵盤事件處理器"""
        def key_press_handler(event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.handle_enter_key()
            else:
                original_handler(event)
        return key_press_handler
        
    def handle_enter_key(self):
        """處理Enter鍵按下事件"""
        # 檢查是否有填寫必要欄位
        if self.validate_input():
            # 如果驗證通過，執行新增下筆
            self.add_next_entry()
        else:
            # 如果驗證失敗，顯示提示
            QMessageBox.warning(self, "輸入錯誤", "請填寫必要欄位（姓名、聯絡電話、選擇活動項目）3333")
