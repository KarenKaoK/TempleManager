from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractScrollArea
from PyQt5.QtCore import pyqtSlot, Qt

class AutoResizingTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet("font-size: 14px;")
        self.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def adjust_to_contents(self):
        """自動調整每欄大小，讓內容完整呈現，不壓縮也不撐爆"""
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # 加上每欄最大寬度限制（可選）
        # for col in range(self.columnCount()):
        #     width = self.columnWidth(col)
        #     self.setColumnWidth(col, min(width, 300))