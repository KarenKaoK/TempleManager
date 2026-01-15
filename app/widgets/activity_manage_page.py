# app/widgets/activity_manage_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QGroupBox, QTableWidget, QDialog, QTableWidgetItem,QHeaderView,QMessageBox
)
from PyQt5.QtCore import Qt,QEvent, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from app.widgets.auto_resizing_table import AutoResizingTableWidget
from app.dialogs.activity_dialog import NewActivityDialog, FEE_TYPE_OPTIONS
from app.dialogs.activity_signup_dialog import ActivitySignupDialog
from app.dialogs.activity_member_search_dialog import ActivityMemberSearchDialog
from app.dialogs.edit_activity_signup_dialog import EditActivitySignupDialog

class ActivityManagePage(QWidget):

    request_close = pyqtSignal()

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
        self.close_activity_btn.clicked.connect(self._on_close_clicked)

        for btn in [
            self.search_activity_btn, self.add_activity_btn,
            self.edit_activity_btn, self.delete_activity_btn,
            self.close_activity_btn
        ]:
            btn.setStyleSheet("font-size: 14px;")
            search_layout.addWidget(btn)

        activity_layout.addLayout(search_layout)

        self.activity_table = AutoResizingTableWidget()
        self.activity_table.setColumnCount(9)
        self.activity_table.setHorizontalHeaderLabels([
            "活動編號", "活動名稱", "起始日期", "結束日期",
            "方案名稱", "方案項目", "費用方式", "金額", "狀態"
        ])

        self.activity_table.setStyleSheet("font-size: 14px;")
        
        # 設定表格欄位自動調整寬度
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 讓所有欄位平均分散
        
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
        self.signup_table.setColumnCount(15)
        self.signup_table.setHorizontalHeaderLabels([
            "序號", "登記日期", "信眾姓名", "聯絡電話", "性別",
            "國曆生日", "農曆生日", "生肖", "生辰", "活動名稱",
            "活動項目", "活動金額", "收據號碼", "聯絡地址", "備註"
        ])
        self.signup_table.setStyleSheet("font-size: 14px;")
        
        # 設定表格欄位自動調整寬度
        signup_header = self.signup_table.horizontalHeader()
        # 設定不同欄位的調整模式
        signup_header.setSectionResizeMode(0, QHeaderView.Fixed)  # 序號固定寬度
        signup_header.setSectionResizeMode(1, QHeaderView.Fixed)  # 登記日期固定寬度
        signup_header.setSectionResizeMode(2, QHeaderView.Fixed)  # 姓名固定寬度
        signup_header.setSectionResizeMode(3, QHeaderView.Fixed)  # 聯絡電話固定寬度
        signup_header.setSectionResizeMode(4, QHeaderView.Fixed)  # 性別固定寬度
        signup_header.setSectionResizeMode(5, QHeaderView.Fixed)  # 國曆生日固定寬度
        signup_header.setSectionResizeMode(6, QHeaderView.Fixed)  # 農曆生日固定寬度
        signup_header.setSectionResizeMode(7, QHeaderView.Fixed)  # 生肖固定寬度
        signup_header.setSectionResizeMode(8, QHeaderView.Fixed)  # 生辰固定寬度
        signup_header.setSectionResizeMode(9, QHeaderView.Fixed)  # 活動名稱固定寬度
        signup_header.setSectionResizeMode(10, QHeaderView.Stretch)  # 活動項目可拉伸
        signup_header.setSectionResizeMode(11, QHeaderView.Fixed)  # 活動金額固定寬度
        signup_header.setSectionResizeMode(12, QHeaderView.Fixed)  # 收據號碼固定寬度
        signup_header.setSectionResizeMode(13, QHeaderView.Stretch)  # 聯絡地址可拉伸
        signup_header.setSectionResizeMode(14, QHeaderView.Stretch)  # 備註可拉伸
        
        # 設定固定寬度
        self.signup_table.setColumnWidth(0, 50)   # 序號
        self.signup_table.setColumnWidth(1, 100)  # 登記日期
        self.signup_table.setColumnWidth(2, 80)   # 姓名
        self.signup_table.setColumnWidth(3, 100)  # 聯絡電話
        self.signup_table.setColumnWidth(4, 50)   # 性別
        self.signup_table.setColumnWidth(5, 100)  # 國曆生日
        self.signup_table.setColumnWidth(6, 100)  # 農曆生日
        self.signup_table.setColumnWidth(7, 50)   # 生肖
        self.signup_table.setColumnWidth(8, 50)   # 生辰
        self.signup_table.setColumnWidth(9, 100)  # 活動名稱
        self.signup_table.setColumnWidth(11, 100) # 活動金額
        self.signup_table.setColumnWidth(12, 100) # 收據號碼
        
        signup_layout.addWidget(self.signup_table)

        signup_group.setLayout(signup_layout)
        layout.addWidget(signup_group)

        self.add_activity_btn.clicked.connect(self.open_new_activity_dialog)
        self.setLayout(layout)

        self.search_activity_btn.clicked.connect(self.handle_search_activity)

        self.load_activities_to_table()
        self.activity_table.resizeRowsToContents()
        self.activity_table.viewport().installEventFilter(self)
        
        # 設定活動表格選擇事件
        self.activity_table.itemSelectionChanged.connect(self.on_activity_selection_changed)
        

        self.edit_activity_btn.clicked.connect(self.handle_edit_activity)
        self.delete_activity_btn.clicked.connect(self.handle_delete_activity)
        
        # 報名人員按鈕事件
        self.add_signup_btn.clicked.connect(self.handle_add_signup)
        self.edit_signup_btn.clicked.connect(self.handle_edit_signup)
        self.delete_signup_btn.clicked.connect(self.handle_delete_signup)
        self.search_signup_btn.clicked.connect(self.handle_search_signup)
        self.print_signup_btn.clicked.connect(self.handle_print_signup)
        
        # 報名人員表格選擇事件不再影響按鈕狀態（統一風格）

    def _on_close_clicked(self):
        self.request_close.emit()

                
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

        def _is_numberlike(v) -> bool:
            try:
                if v is None:
                    return False
                s = str(v).strip()
                if s == "":
                    return False
                float(s)
                return True
            except Exception:
                return False

        def _format_amount_multiline(v):
            # 保留你原本的多行金額顯示（每行加千分位、去 .0）
            try:
                parts = [p for p in str(v).split("\n") if str(p).strip() != ""]
                return "\n".join([f"{int(float(p)):,}" for p in parts])
            except Exception:
                return "" if v is None else str(v)

        for row_index, activity in enumerate(results):
            self.activity_table.insertRow(row_index)

            # -------------------------
            # 1) 推斷回傳順序（只針對後三欄：fee_type/amount/is_closed）
            # -------------------------
            # 你 UI 期待欄位：
            # 0 活動編號, 1 活動名稱, 2 起始, 3 結束, 4 方案名稱, 5 方案項目, 6 費用方式, 7 金額, 8 狀態
            #
            # 目前你畫面顯示錯，常見原因是 controller 回傳順序變成：
            # 6 amount, 7 is_closed, 8 fee_type   (或其他排列)
            #
            # 我們用內容特徵去判斷：
            # - fee_type：通常是 FEE_TYPE_OPTIONS 其中之一（或空字串）
            # - is_closed：通常是 0/1/True/False
            # - amount：通常是數字（或多行數字字串）
            #

            def _is_closed_like(v) -> bool:
                s = str(v).strip()
                return s in ("0", "1", "True", "False", "true", "false")

            def _is_fee_type_like(v) -> bool:
                s = str(v).strip()
                return s in FEE_TYPE_OPTIONS or s == ""

            # 預設：假設 controller 已經是正確順序：6 fee_type, 7 amount, 8 is_closed
            src_fee_idx, src_amt_idx, src_closed_idx = 6, 7, 8

            if len(activity) >= 9:
                v6, v7, v8 = activity[6], activity[7], activity[8]

                # Case A：6 是 amount、7 是 is_closed、8 是 fee_type（你現在畫面最像這種）
                if _is_numberlike(v6) and _is_closed_like(v7) and _is_fee_type_like(v8):
                    src_amt_idx, src_closed_idx, src_fee_idx = 6, 7, 8

                # Case B：6 是 fee_type、7 是 is_closed、8 是 amount
                elif _is_fee_type_like(v6) and _is_closed_like(v7) and _is_numberlike(v8):
                    src_fee_idx, src_closed_idx, src_amt_idx = 6, 7, 8

                # Case C：6 是 is_closed、7 是 fee_type、8 是 amount
                elif _is_closed_like(v6) and _is_fee_type_like(v7) and _is_numberlike(v8):
                    src_closed_idx, src_fee_idx, src_amt_idx = 6, 7, 8

                # Case D：6 是 amount、7 是 fee_type、8 是 is_closed
                elif _is_numberlike(v6) and _is_fee_type_like(v7) and _is_closed_like(v8):
                    src_amt_idx, src_fee_idx, src_closed_idx = 6, 7, 8

            # -------------------------
            # 2) 先把前 0~5 欄照原順序塞
            # -------------------------
            for col_index in range(min(6, len(activity))):
                value = "" if activity[col_index] is None else activity[col_index]
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignTop)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.activity_table.setItem(row_index, col_index, item)

            # -------------------------
            # 3) 再把 fee_type / amount / status 塞到固定欄位 (6/7/8)
            # -------------------------
            # fee_type → 欄 6
            fee_val = "" if len(activity) <= src_fee_idx or activity[src_fee_idx] is None else activity[src_fee_idx]
            fee_item = QTableWidgetItem(str(fee_val))
            fee_item.setTextAlignment(Qt.AlignTop)
            fee_item.setFlags(fee_item.flags() ^ Qt.ItemIsEditable)
            self.activity_table.setItem(row_index, 6, fee_item)

            # amount → 欄 7（多行千分位）
            amt_val = "" if len(activity) <= src_amt_idx or activity[src_amt_idx] is None else activity[src_amt_idx]
            amt_text = _format_amount_multiline(amt_val)
            amt_item = QTableWidgetItem(str(amt_text))
            amt_item.setTextAlignment(Qt.AlignTop)
            amt_item.setFlags(amt_item.flags() ^ Qt.ItemIsEditable)
            self.activity_table.setItem(row_index, 7, amt_item)

            # status → 欄 8（is_closed）
            closed_val = "" if len(activity) <= src_closed_idx or activity[src_closed_idx] is None else activity[src_closed_idx]
            status_text = "已關閉" if str(closed_val).strip() in ("1", "True", "true") else "進行中"
            st_item = QTableWidgetItem(status_text)
            st_item.setTextAlignment(Qt.AlignTop)
            st_item.setFlags(st_item.flags() ^ Qt.ItemIsEditable)
            self.activity_table.setItem(row_index, 8, st_item)

        self.activity_table.resizeRowsToContents()


    def handle_search_activity(self):
        keyword = self.activity_search_input.text().strip()
        # 先確保表格已載入全部活動
        self.load_activities_to_table()
        # 高亮顯示符合關鍵字的列（不移除其他資料）
        found_count = self.highlight_activity_rows(keyword)
        if keyword and found_count == 0:
            QMessageBox.information(self, "未找到資料", "找不到符合條件的活動。")

    def highlight_activity_rows(self, keyword: str) -> int:
        """以背景色高亮符合關鍵字的活動列，其他列恢復預設。回傳命中筆數。"""
        # 設定顏色：淡黃色做為高亮
        highlight_brush = QBrush(QColor('#FFF3CD'))
        default_brush = QBrush(Qt.white)

        # 正規化比對（小寫包含）
        norm_kw = keyword.lower()

        row_count = self.activity_table.rowCount()
        col_count = self.activity_table.columnCount()

        found = 0
        for row in range(row_count):
            # 是否此列命中
            is_match = False
            if norm_kw:
                for col in range(col_count):
                    item = self.activity_table.item(row, col)
                    if item and norm_kw in item.text().lower():
                        is_match = True
                        break

            if is_match:
                found += 1

            # 套用背景色
            for col in range(col_count):
                item = self.activity_table.item(row, col)
                if not item:
                    continue
                item.setBackground(highlight_brush if (norm_kw and is_match) else default_brush)

        return found

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
                self.activity_table.setCurrentItem(None)  
                self.activity_table.clearSelection()      
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

    def handle_add_signup(self):
        """處理新增報名人員"""
        # 檢查是否有選中的活動
        selected_row = self.activity_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "請選擇活動", "請先在上方表格中選取一個活動，然後再新增報名人員。")
            return
            
        # 取得選中活動的資料
        activity_id = self.activity_table.item(selected_row, 0).text()
        activity_name = self.activity_table.item(selected_row, 1).text()
        
        activity_data = {
            'activity_id': activity_id,
            'activity_name': activity_name
        }
        
        # 開啟人員搜尋報名對話框
        dialog = ActivityMemberSearchDialog(self.controller, activity_data, self)
        dialog.signup_added.connect(self.on_signup_added)
        dialog.exec_()
        
    def handle_edit_signup(self):
        """處理修改報名人員"""
        # 檢查是否有選中的活動
        selected_activity_row = self.activity_table.currentRow()
        if selected_activity_row == -1:
            QMessageBox.warning(
                self, 
                "請先選擇活動", 
                "請先在上方「活動項目管理」表格中選取一個活動，\n然後再點選「修改人員」按鈕。"
            )
            return
            
        # 檢查是否有選中的報名人員
        selected_signup_row = self.signup_table.currentRow()
        if selected_signup_row == -1:
            QMessageBox.warning(
                self, 
                "請先選擇要修改的人員", 
                "請先在下方「活動報名人員」表格中選取要修改的報名人員，\n然後再點選「修改人員」按鈕。"
            )
            return
            
        # 檢查報名人員表格是否有資料
        if self.signup_table.rowCount() == 0:
            QMessageBox.information(
                self, 
                "無報名人員資料", 
                "目前選中的活動還沒有報名人員，\n請先使用「新增人員」功能新增報名人員。"
            )
            return
            
        # 取得選中活動的資料
        activity_id = self.activity_table.item(selected_activity_row, 0).text()
        activity_name = self.activity_table.item(selected_activity_row, 1).text()
        
        # 取得選中報名人員的ID（從表格的隱藏欄位或從資料中取得）
        # 這裡我們需要從報名人員資料中取得ID
        try:
            # 從報名人員表格中取得對應的資料
            signup_data = self.get_signup_data_from_table(selected_signup_row)
            if not signup_data:
                QMessageBox.warning(self, "資料錯誤", "無法取得報名人員資料，請重新選擇。")
                return
                
            activity_data = {
                'activity_id': activity_id,
                'activity_name': activity_name
            }
            
            # 開啟修改報名對話框
            dialog = EditActivitySignupDialog(self.controller, activity_data, signup_data, self)
            dialog.signup_updated.connect(self.on_signup_updated)
            dialog.exec_()
            
        except Exception as e:
            print(f"❌ 修改報名人員時發生錯誤: {e}")
            QMessageBox.critical(self, "修改失敗", "修改報名人員時發生錯誤")
        
    def handle_delete_signup(self):
        """處理刪除報名人員"""
        # 檢查是否有選中的活動
        selected_activity_row = self.activity_table.currentRow()
        if selected_activity_row == -1:
            QMessageBox.warning(
                self,
                "請先選擇活動",
                "請先在上方「活動項目管理」表格中選取一個活動，\n然後再點選「刪除人員」按鈕。"
            )
            return

        # 檢查是否有選中的報名人員
        selected_signup_row = self.signup_table.currentRow()
        if selected_signup_row == -1:
            QMessageBox.warning(
                self,
                "請先選擇要刪除的人員",
                "請先在下方「活動報名人員」表格中選取要刪除的報名人員，\n然後再點選「刪除人員」按鈕。"
            )
            return

        # 取得選中報名人員的 id 與名稱
        id_item = self.signup_table.item(selected_signup_row, 0)
        name_item = self.signup_table.item(selected_signup_row, 2)
        signup_id = id_item.data(Qt.UserRole) if id_item else None
        person_name = name_item.text() if name_item else ""

        if not signup_id:
            QMessageBox.critical(self, "刪除失敗", "找不到選中人員的識別碼，無法刪除。")
            return

        # 確認刪除
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("確認刪除")
        msg.setText(f"確定要刪除報名人員「{person_name}」嗎？此操作無法復原。")
        yes_btn = msg.addButton("是", QMessageBox.YesRole)
        no_btn = msg.addButton("否", QMessageBox.NoRole)
        msg.setDefaultButton(no_btn)
        msg.exec_()

        if msg.clickedButton() != yes_btn:
            return

        # 執行刪除
        try:
            success = self.controller.delete_activity_signup(signup_id)
            if success:
                QMessageBox.information(self, "刪除成功", f"報名人員「{person_name}」已刪除。")
                # 重新載入當前活動的報名人員
                activity_id = self.activity_table.item(selected_activity_row, 0).text()
                self.load_signups_for_activity(activity_id)
            else:
                QMessageBox.critical(self, "刪除失敗", "刪除報名人員時發生錯誤。")
        except Exception as e:
            print(f"❌ 刪除報名人員時發生錯誤: {e}")
            QMessageBox.critical(self, "刪除失敗", "刪除報名人員時發生未預期的錯誤。")
        
    def handle_search_signup(self):
        """處理搜尋報名人員"""
        selected_row = self.activity_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "請選擇活動", "請先在上方表格中選取一個活動，然後再搜尋報名人員。")
            return
            
        keyword = self.signup_search_input.text().strip()
        activity_id = self.activity_table.item(selected_row, 0).text()
        
        # 先載入全部，再做高亮
        self.load_signups_for_activity(activity_id)

        # 高亮顯示符合關鍵字的列（不移除其他資料）
        found_count = self.highlight_signup_rows(keyword)
        
        # 若有關鍵字但沒有命中，給提示
        if keyword and found_count == 0:
            QMessageBox.information(self, "未找到資料", "找不到符合條件的報名人員。")
        
    def handle_print_signup(self):
        """處理列印報名人員"""
        QMessageBox.information(self, "功能開發中", "列印報名人員功能正在開發中...")
        
    def on_activity_selection_changed(self):
        """當活動選擇改變時，載入對應的報名人員"""
        selected_row = self.activity_table.currentRow()
        if selected_row >= 0:
            activity_id = self.activity_table.item(selected_row, 0).text()
            self.load_signups_for_activity(activity_id)
        else:
            # 清空報名人員表格
            self.signup_table.setRowCount(0)
            
        # 報名人員按鈕狀態維持統一風格

    def highlight_signup_rows(self, keyword: str) -> int:
        """以背景色高亮符合關鍵字的報名人員列，返回命中筆數。"""
        highlight_brush = QBrush(QColor('#FFF3CD'))
        default_brush = QBrush(Qt.white)

        norm_kw = (keyword or "").lower()
        row_count = self.signup_table.rowCount()
        col_count = self.signup_table.columnCount()

        found = 0
        for row in range(row_count):
            is_match = False
            if norm_kw:
                for col in range(col_count):
                    item = self.signup_table.item(row, col)
                    if item and norm_kw in item.text().lower():
                        is_match = True
                        break

            if is_match:
                found += 1

            for col in range(col_count):
                item = self.signup_table.item(row, col)
                if not item:
                    continue
                item.setBackground(highlight_brush if (norm_kw and is_match) else default_brush)

        return found
            
    # 報名人員表格選擇改變時不做樣式與狀態切換，維持統一
            
    def load_signups_for_activity(self, activity_id):
        """載入指定活動的報名人員"""
        if not self.controller:
            return
            
        try:
            signups = self.controller.get_activity_signups(activity_id)
            self.update_signup_table(signups)
        except Exception as e:
            print(f"❌ 載入報名人員時發生錯誤: {e}")
            self.signup_table.setRowCount(0)
            
    def update_signup_table(self, signups):
        """更新報名人員表格"""
        self.signup_table.setRowCount(len(signups))
        
        for row, signup in enumerate(signups):
            # 序號（同時在序號儲存格的 data 中保存實際 signup id）
            seq_item = QTableWidgetItem(str(row + 1))
            try:
                signup_id = signup.get("id") if isinstance(signup, dict) else signup[0]
            except Exception:
                signup_id = None
            if signup_id is not None:
                seq_item.setData(Qt.UserRole, signup_id)
            self.signup_table.setItem(row, 0, seq_item)
            
            # 登記日期
            reg_date = signup.get("created_at", "")
            self.signup_table.setItem(row, 1, QTableWidgetItem(reg_date))
            
            # 信眾姓名
            self.signup_table.setItem(row, 2, QTableWidgetItem(signup.get("person_name", "")))
            
            # 聯絡電話
            self.signup_table.setItem(row, 3, QTableWidgetItem(signup.get("phone", "")))
            
            # 性別
            self.signup_table.setItem(row, 4, QTableWidgetItem(signup.get("gender", "")))
            
            # 國曆生日
            self.signup_table.setItem(row, 5, QTableWidgetItem(signup.get("birth_ad", "")))
            
            # 農曆生日
            self.signup_table.setItem(row, 6, QTableWidgetItem(signup.get("birth_lunar", "")))
            
            # 生肖
            self.signup_table.setItem(row, 7, QTableWidgetItem(signup.get("zodiac", "")))
            
            # 生辰
            self.signup_table.setItem(row, 8, QTableWidgetItem(signup.get("birth_time", "")))
            
            # 活動名稱（從當前選中的活動取得）
            selected_row = self.activity_table.currentRow()
            if selected_row >= 0:
                activity_name = self.activity_table.item(selected_row, 1).text()
                self.signup_table.setItem(row, 9, QTableWidgetItem(activity_name))
            
            # 活動項目
            activity_items = signup.get("activity_items", "")
            item = QTableWidgetItem(activity_items)
            item.setToolTip(activity_items)  # 設定工具提示
            self.signup_table.setItem(row, 10, item)
            
            # 活動金額
            activity_amount = signup.get("activity_amount", 0)
            amount_text = f"${activity_amount:,.0f}" if activity_amount > 0 else ""
            item = QTableWidgetItem(amount_text)
            item.setToolTip(amount_text)
            self.signup_table.setItem(row, 11, item)
            
            # 收據號碼
            receipt_number = signup.get("receipt_number", "")
            item = QTableWidgetItem(receipt_number)
            item.setToolTip(receipt_number)
            self.signup_table.setItem(row, 12, item)
            
            # 聯絡地址
            address = signup.get("address", "")
            item = QTableWidgetItem(address)
            item.setToolTip(address)  # 設定工具提示
            self.signup_table.setItem(row, 13, item)
            
            # 備註
            note = signup.get("note", "")
            item = QTableWidgetItem(note)
            item.setToolTip(note)  # 設定工具提示
            self.signup_table.setItem(row, 14, item)
            
        # 按鈕樣式不依選擇變化
            
    def on_signup_added(self, signup_data):
        """當新增報名人員成功時的回調"""
        print(f"✅ 新增報名人員成功: {signup_data['name']}")
        # 重新載入當前活動的報名人員
        selected_row = self.activity_table.currentRow()
        if selected_row >= 0:
            activity_id = self.activity_table.item(selected_row, 0).text()
            self.load_signups_for_activity(activity_id)
            
    def on_signup_updated(self, signup_data):
        """當修改報名人員成功時的回調"""
        print(f"✅ 修改報名人員成功: {signup_data['name']}")
        # 重新載入當前活動的報名人員
        selected_row = self.activity_table.currentRow()
        if selected_row >= 0:
            activity_id = self.activity_table.item(selected_row, 0).text()
            self.load_signups_for_activity(activity_id)
            
    def get_signup_data_from_table(self, row):
        """從報名人員表格中取得指定行的資料"""
        try:
            # 從表格中取得基本資料
            person_name = self.signup_table.item(row, 2).text() if self.signup_table.item(row, 2) else ""
            phone = self.signup_table.item(row, 3).text() if self.signup_table.item(row, 3) else ""
            gender = self.signup_table.item(row, 4).text() if self.signup_table.item(row, 4) else ""
            birth_ad = self.signup_table.item(row, 5).text() if self.signup_table.item(row, 5) else ""
            birth_lunar = self.signup_table.item(row, 6).text() if self.signup_table.item(row, 6) else ""
            zodiac = self.signup_table.item(row, 7).text() if self.signup_table.item(row, 7) else ""
            birth_time = self.signup_table.item(row, 8).text() if self.signup_table.item(row, 8) else ""
            activity_items = self.signup_table.item(row, 10).text() if self.signup_table.item(row, 10) else ""
            activity_amount_text = self.signup_table.item(row, 11).text() if self.signup_table.item(row, 11) else ""
            receipt_number = self.signup_table.item(row, 12).text() if self.signup_table.item(row, 12) else ""
            address = self.signup_table.item(row, 13).text() if self.signup_table.item(row, 13) else ""
            note = self.signup_table.item(row, 14).text() if self.signup_table.item(row, 14) else ""
            created_at = self.signup_table.item(row, 1).text() if self.signup_table.item(row, 1) else ""
            
            # 處理活動金額
            activity_amount = 0
            if activity_amount_text:
                try:
                    activity_amount = float(activity_amount_text.replace("$", "").replace(",", ""))
                except:
                    activity_amount = 0
            
            # 根據姓名和電話從資料庫中取得完整的報名人員資料
            selected_activity_row = self.activity_table.currentRow()
            if selected_activity_row >= 0:
                activity_id = self.activity_table.item(selected_activity_row, 0).text()
                
                # 搜尋對應的報名人員資料
                signups = self.controller.get_activity_signups(activity_id)
                for signup in signups:
                    if (signup.get("person_name") == person_name and 
                        signup.get("phone") == phone):
                        return signup
                        
            # 如果找不到，返回基本資料
            return {
                "person_name": person_name,
                "phone": phone,
                "gender": gender,
                "birth_ad": birth_ad,
                "birth_lunar": birth_lunar,
                "zodiac": zodiac,
                "birth_time": birth_time,
                "activity_items": activity_items,
                "activity_amount": activity_amount,
                "receipt_number": receipt_number,
                "address": address,
                "note": note,
                "created_at": created_at
            }
            
        except Exception as e:
            print(f"❌ 取得報名人員資料時發生錯誤: {e}")
            return None


