from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import pyqtSlot

class AutoResizingTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 預設樣式
        self.setStyleSheet("font-size: 14px;")
        self.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)

    def adjust_to_contents(self):
        """根據內容自動調整表格大小"""
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        total_width = self.verticalHeader().width() + self.frameWidth() * 2
        for col in range(self.columnCount()):
            total_width += self.columnWidth(col)

        total_height = self.horizontalHeader().height() + self.frameWidth() * 2
        for row in range(self.rowCount()):
            total_height += self.rowHeight(row)

        self.setMinimumSize(total_width, total_height)
