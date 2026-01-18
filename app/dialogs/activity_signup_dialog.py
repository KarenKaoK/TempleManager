# app/dialogs/activity_signup_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QDateEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import QDate, Qt, pyqtSignal
from PyQt5.QtGui import QFont
import uuid
from datetime import datetime
import re

class ActivitySignupDialog(QDialog):
    # 定義信號，用於通知父視窗新增成功
    signup_added = pyqtSignal(dict)
    
    def __init__(self, controller, activity_data=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.activity_data = activity_data or {}
        self.activity_items = []
        self.total_amount = 0
        
        self.setWindowTitle("活動報名")
        self.setMinimumSize(1000, 700)
        self.setModal(True)
        
        self.setup_ui()
        self.load_activity_items()
        
        # 設定Enter鍵事件處理
        self.setup_key_events()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 活動名稱標題
        activity_name = self.activity_data.get('activity_name', '未選擇活動')
        title_label = QLabel(f"活動名稱: {activity_name}")
        title_label.setStyleSheet("color: red; font-size: 18px; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 主要內容區域
        main_layout = QHBoxLayout()
        
        # 左半邊：報名者資料輸入
        left_group = self.create_participant_form()
        main_layout.addWidget(left_group, 2)
        
        # 右半邊：活動項目選擇
        right_group = self.create_activity_items_section()
        main_layout.addWidget(right_group, 1)
        
        layout.addLayout(main_layout)
        
        # 底部按鈕
        button_layout = self.create_buttons()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def create_participant_form(self):
        group = QGroupBox("報名者資料")
        group.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout = QVBoxLayout()
        
        # 表單佈局
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
        
        self.gregorian_birthday = QDateEdit()
        self.gregorian_birthday.setCalendarPopup(True)
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
        
        layout.addLayout(form_layout)
        
        # 備註說明
        layout.addWidget(QLabel("備註說明:"))
        self.remarks = QTextEdit()
        self.remarks.setMaximumHeight(100)
        layout.addWidget(self.remarks)
        
        group.setLayout(layout)
        return group
        
    def create_activity_items_section(self):
        group = QGroupBox("參加活動項目")
        group.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #f0f0f0;")
        layout = QVBoxLayout()
        
        # 活動項目表格
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["數量", "活動項目", "項目金額"])
        
        # 設定表格樣式
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setStyleSheet("font-size: 12px;")
        
        layout.addWidget(self.items_table)
        
        # 總金額顯示
        self.total_label = QLabel("總金額: $0")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red; margin: 10px;")
        self.total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.total_label)
        
        # 活動費用資料區塊
        fee_group = QGroupBox("活動費用資料")
        fee_group.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
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
        self.add_next_btn.setStyleSheet("font-size: 14px;")
        self.add_next_btn.clicked.connect(self.add_next_entry)
        
        # 存入離開按鈕
        self.save_exit_btn = QPushButton("存入離開")
        self.save_exit_btn.setStyleSheet("font-size: 14px;")
        self.save_exit_btn.clicked.connect(self.save_and_exit)
        
        # 關閉退出按鈕
        self.close_btn = QPushButton("關閉退出")
        self.close_btn.setStyleSheet("font-size: 14px;")
        self.close_btn.clicked.connect(self.close_dialog)
        
        layout.addWidget(self.add_next_btn)
        layout.addWidget(self.save_exit_btn)
        layout.addWidget(self.close_btn)
        
        return layout
        
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
            "gregorian_birthday": self.gregorian_birthday.date().toString("yyyy/MM/dd"),
            "lunar_birthday": self.lunar_birthday.text(),
            "zodiac": self.zodiac.currentText(),
            "birth_time": self.birth_time.currentText(),
            "address": self.address.text(),
            "activity_amount": self.total_amount,
            "receipt_number": self.receipt_number.text(),
            "remarks": self.remarks.toPlainText(),
            "selected_items": selected_items
        }
        
    def add_next_entry(self):
        ok, msg = self.validate_input()
        print("DEBUG add_next_entry validate:", ok, msg)

        if ok:
            signup_data = self.get_signup_data()
            print(f"🔍 準備儲存資料: {signup_data}")

            if self.controller and self.controller.insert_activity_signup(signup_data):
                self.signup_added.emit(signup_data)
                self.clear_form()
                QMessageBox.information(self, "新增成功", f"已成功新增報名人員：{signup_data['name']}")
            else:
                QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")
        else:
            QMessageBox.warning(self, "輸入錯誤", msg or "請填寫必要欄位")

            
    def save_and_exit(self):
        print("🔥 DEBUG: save_and_exit triggered, focus=", type(self.focusWidget()).__name__)
        print("====== DEBUG save_and_exit ======")
        print("name:", repr(self.name.text()))
        print("phone:", repr(self.contact_phone.text()))
        print("address:", repr(self.address.text()))
        print("total_amount:", self.total_amount)
        print("activity_amount text:", repr(self.activity_amount.text()))

        for row in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(row, 0)
            amt_item = self.items_table.item(row, 2)
            item = self.items_table.item(row, 1)
            print(
                f"row {row} item:", item.text() if item else None,
                "qty:", w.value() if w else None,
                "amount_cell:", amt_item.text() if amt_item else None
            )

        ok, msg = self.validate_input()
        print("validate_input:", ok, msg)
        print("====== END DEBUG ======")

        if ok:
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
                QMessageBox.information(self, "儲存成功", f"已成功儲存報名人員：{signup_data['name']}")
                self.accept()
            else:
                QMessageBox.critical(self, "儲存失敗", "儲存報名資料時發生錯誤，請檢查資料庫連接")
        else:
            QMessageBox.warning(self, "輸入錯誤", msg or "請填寫必要欄位")


            
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
        """
        驗證輸入：
        - 必填：姓名、聯絡電話、地址
        - 必須至少選一個活動項目（數量 > 0）
        - 隨喜隨緣：不檢查金額（允許 total_amount == 0）
        - 固定金額：也不必特別檢查 total_amount（因為它會跟著選項計算）
        """
        name = self.name.text().strip()
        phone = self.contact_phone.text().strip()
        address = self.address.text().strip()

        if not name:
            return False, "姓名未填"
        if not phone:
            return False, "聯絡電話未填"
        if not address:
            return False, "地址未填"

        # 至少選一個活動項目（數量 > 0）
        has_selected_item = False
        debug_rows = []
        for row in range(self.items_table.rowCount()):
            qty_widget = self.items_table.cellWidget(row, 0)
            qty = qty_widget.value() if qty_widget else 0

            item = self.items_table.item(row, 1)
            item_name = item.text() if item else ""

            debug_rows.append((row, item_name, qty))

            if qty > 0:
                has_selected_item = True

        if not has_selected_item:
            return False, f"尚未選擇活動項目（全部數量都是 0） rows={debug_rows}"

        # ✅ 隨喜隨緣：不需要檢查金額（允許 0）
        # ✅ 固定金額：也不額外檢查 total_amount（避免編輯器未 commit 時誤判）
        return True, ""



        
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
        print("🔥 DEBUG: handle_enter_key triggered, focus=", type(self.focusWidget()).__name__)
        ok, msg = self.validate_input()
        print("🔥 DEBUG: handle_enter_key validate:", ok, msg)
        if ok:
            self.add_next_entry()
        else:
            QMessageBox.warning(self, "輸入錯誤", msg or "請填寫必要欄位（姓名、聯絡電話、地址、選擇活動項目）")
