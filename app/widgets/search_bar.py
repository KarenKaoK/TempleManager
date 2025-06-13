from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal

class SearchBarWidget(QWidget):
    # ✅ 定義一個 Signal，會傳出搜尋文字
    search_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("請輸入電話 / 姓名 / 地址")
        self.search_button = QPushButton("資料查詢")
        layout.addWidget(QLabel("快速查詢："))
        layout.addWidget(self.search_input)
        layout.addWidget(self.search_button)
        self.setLayout(layout)

        # ✅ 當按鈕被點擊時，發出 search_triggered signal
        self.search_button.clicked.connect(self.emit_search_signal)

    def emit_search_signal(self):
        keyword = self.search_input.text().strip()
        self.search_triggered.emit(keyword)  # ✅ 發出 signal 到 MainWindow
