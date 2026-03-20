from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout

from app.logging.base_logger import LOG_FILE_PATH, read_log_tail_text, read_log_text


class SystemLogViewerDialog(QDialog):
    DEFAULT_TAIL_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系統日誌")
        if parent is not None:
            self.resize(parent.size())
        else:
            self.resize(1000, 700)
        self._build_ui()
        self._reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self.lbl_hint = QLabel(self)
        self.lbl_hint.setStyleSheet("QLabel { color:#6B7280; }")
        root.addWidget(self.lbl_hint)

        self.txt_log = QPlainTextEdit(self)
        self.txt_log.setReadOnly(True)
        self.txt_log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_log.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        root.addWidget(self.txt_log, 1)

        row = QHBoxLayout()
        self.btn_reload = QPushButton("重新整理", self)
        self.btn_load_all = QPushButton("載入全部", self)
        self.btn_close = QPushButton("關閉", self)
        self.btn_reload.clicked.connect(lambda: self._reload(load_all=False))
        self.btn_load_all.clicked.connect(lambda: self._reload(load_all=True))
        self.btn_close.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(self.btn_reload)
        row.addWidget(self.btn_load_all)
        row.addWidget(self.btn_close)
        root.addLayout(row)

    def _reload(self, load_all: bool = False):
        path = Path(LOG_FILE_PATH)
        if not path.exists():
            self.lbl_hint.setText("目前尚無 log 紀錄。")
            self.txt_log.setPlainText("目前尚無 log 紀錄。")
            return
        try:
            if load_all:
                self.lbl_hint.setText("目前顯示全部 log。")
                text = read_log_text()
            else:
                self.lbl_hint.setText(f"目前僅顯示最近 {self.DEFAULT_TAIL_LINES} 行；如需完整內容請按「載入全部」。")
                text = read_log_tail_text(self.DEFAULT_TAIL_LINES)
            self.txt_log.setPlainText(text or "目前尚無 log 紀錄。")
            self.txt_log.moveCursor(self.txt_log.textCursor().End)
        except Exception as e:
            QMessageBox.warning(self, "讀取失敗", f"無法讀取系統日誌：{e}")
