# app/widgets/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTableWidget, QDialog, QTableWidgetItem,QHeaderView,QMessageBox
)
from PyQt5.QtCore import Qt,QEvent
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.dialogs.activity_dialog import NewActivityDialog

class ActivityManagePage(QWidget):
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        layout = QVBoxLayout()

        # 🔷 活動管理區塊
        activity_group = QGroupBox("活動項目管理")
        activity_group.setStyleSheet("font-size: 18px; font-weight: bold;")
        activity_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("活動搜尋："))
        self.activity_search_input = QLineEdit()
        search_layout.addWidget(self.activity_search_input)

        self.search_activity_btn = QPushButton("🔍 搜尋")
        self.add_activity_btn = QPushButton("➕ 新增活動")
        self.edit_activity_btn = QPushButton("🖊 修改活動")
        self.delete_activity_btn = QPushButton("❌ 刪除活動")
        self.close_activity_btn = QPushButton("⛔ 關閉活動")

        for btn in [
            self.search_activity_btn, self.add_activity_btn,
            self.edit_activity_btn, self.delete_activity_btn,
            self.close_activity_btn
        ]:
            btn.setStyleSheet("font-size: 14px;")
            search_layout.addWidget(btn)

        activity_layout.addLayout(search_layout)

        self.activity_table = AutoResizingTableWidget()
        self.activity_table.setColumnCount(8)
        self.activity_table.setHorizontalHeaderLabels([
            "活動編號", "活動名稱", "起始日期", "結束日期",
            "方案名稱", "方案項目", "金額", "狀態"
        ])

        self.activity_table.setStyleSheet("font-size: 14px;")
        activity_layout.addWidget(self.activity_table)

        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)

        # 🔶 報名人員區塊
        signup_group = QGroupBox("活動報名人員")
        signup_group.setStyleSheet("font-size: 18px; font-weight: bold;")
        signup_layout = QVBoxLayout()

        signup_search_layout = QHBoxLayout()
        signup_search_layout.addWidget(QLabel("參加人員姓名搜尋："))
        self.signup_search_input = QLineEdit()
        signup_search_layout.addWidget(self.signup_search_input)

        self.search_signup_btn = QPushButton("🔍 搜尋")
        self.add_signup_btn = QPushButton("➕ 新增人員")
        self.edit_signup_btn = QPushButton("🖊 修改人員")
        self.delete_signup_btn = QPushButton("❌ 刪除人員")
        self.print_signup_btn = QPushButton("🖨️ 資料列印")

        for btn in [
            self.search_signup_btn, self.add_signup_btn,
            self.edit_signup_btn, self.delete_signup_btn,
            self.print_signup_btn
        ]:
            btn.setStyleSheet("font-size: 14px;")
            signup_search_layout.addWidget(btn)

        signup_layout.addLayout(signup_search_layout)

        self.signup_table = AutoResizingTableWidget()
        self.signup_table.setColumnCount(16)
        self.signup_table.setHorizontalHeaderLabels([
            "序", "姓名", "性別", "國曆生日", "農曆生日",
            "年份", "生肖", "年齡", "生辰", "聯絡電話", "手機號碼",
            "身份", "身份證字號", "聯絡地址", "備註說明","報名日期"
        ])
        self.signup_table.setStyleSheet("font-size: 14px;")
        signup_layout.addWidget(self.signup_table)

        signup_group.setLayout(signup_layout)
        layout.addWidget(signup_group)

        self.add_activity_btn.clicked.connect(self.open_new_activity_dialog)
        self.setLayout(layout)

        self.search_activity_btn.clicked.connect(self.handle_search_activity)

        self.load_activities_to_table()
        self.activity_table.resizeRowsToContents()
        self.activity_table.resizeColumnsToContents()
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        self.activity_table.viewport().installEventFilter(self)
        

        self.edit_activity_btn.clicked.connect(self.handle_edit_activity)
        self.delete_activity_btn.clicked.connect(self.handle_delete_activity)



                
    def open_new_activity_dialog(self):
        
        dialog = NewActivityDialog(self.controller)
        if dialog.exec_() == QDialog.Accepted:
            print("✅ 活動新增成功")
            self.load_activities_to_table()  
   
    def load_activities_to_table(self):
        activities = self.controller.get_all_activities()
        self.load_results_to_table(activities)


    def load_results_to_table(self, results):
        self.activity_table.setRowCount(0)

        for row_index, activity in enumerate(results):
            self.activity_table.insertRow(row_index)
            for col_index, value in enumerate(activity):
                if col_index == 7:  # is_closed
                    value = "已關閉" if value == 1 else "進行中"
                elif col_index == 6:  # amount
                    try:
                        value = '\n'.join([f"{int(float(a)):,}" for a in str(value).split('\n')])
                    except:
                        pass
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignTop)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.activity_table.setItem(row_index, col_index, item)

        self.activity_table.resizeRowsToContents()
        self.activity_table.resizeColumnsToContents()


    def handle_search_activity(self):
        keyword = self.activity_search_input.text().strip()
        if not keyword:
            self.load_activities_to_table()
            return

        results = self.controller.search_activities(keyword)
        self.load_results_to_table(results)

    def handle_edit_activity(self):
        selected_row = self.activity_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "請選擇活動", "請先在上方表格中選取一筆活動進行修改。")
            return

        activity_id = self.activity_table.item(selected_row, 0).text()
        activity_data, scheme_rows = self.controller.get_activity_by_id(activity_id)

        dialog = NewActivityDialog(self.controller, mode="edit", activity_data=activity_data, scheme_rows=scheme_rows)
        if dialog.exec_() == QDialog.Accepted:
            self.load_activities_to_table()


    def eventFilter(self, source, event):
        if (source == self.activity_table.viewport() and event.type() == QEvent.MouseButtonPress):
            index = self.activity_table.indexAt(event.pos())
            if not index.isValid():  # 點空白區域
                self.activity_table.setCurrentItem(None)  # ✅ 清除 currentRow 的狀態
                self.activity_table.clearSelection()      # ✅ 清除視覺選取
        return super().eventFilter(source, event)

    
    def handle_delete_activity(self):
        selected_row = self.activity_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "請選擇活動", "請先在上方表格中選取要刪除的活動。")
            return

        activity_id = self.activity_table.item(selected_row, 0).text()
        activity_name = self.activity_table.item(selected_row, 1).text()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("確認刪除")
        msg.setText(f"確定要刪除活動「{activity_name}」嗎？此操作無法復原。")

        yes_btn = msg.addButton("是", QMessageBox.YesRole)
        no_btn  = msg.addButton("否", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)          # 預設選擇「否」
        msg.exec_()

        if msg.clickedButton() == yes_btn:
            success = self.controller.delete_activity(activity_id)
            if success:
                QMessageBox.information(self, "刪除成功", f"活動「{activity_name}」已刪除。")
                self.load_activities_to_table()
            else:
                QMessageBox.critical(self, "刪除失敗", "刪除活動時發生錯誤。")


