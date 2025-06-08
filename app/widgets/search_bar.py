from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel


class SearchBarWidget(QWidget):
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
