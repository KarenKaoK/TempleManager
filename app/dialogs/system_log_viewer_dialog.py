from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout

from app.logging.base_logger import LOG_FILE_PATH


class SystemLogViewerDialog(QDialog):
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
        self.txt_log = QPlainTextEdit(self)
        self.txt_log.setReadOnly(True)
        self.txt_log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.txt_log.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        root.addWidget(self.txt_log, 1)

        row = QHBoxLayout()
        self.btn_reload = QPushButton("重新整理", self)
        self.btn_close = QPushButton("關閉", self)
        self.btn_reload.clicked.connect(self._reload)
        self.btn_close.clicked.connect(self.accept)
        row.addStretch()
        row.addWidget(self.btn_reload)
        row.addWidget(self.btn_close)
        root.addLayout(row)

    def _reload(self):
        path = Path(LOG_FILE_PATH)
        if not path.exists():
            self.txt_log.setPlainText("目前尚無 log 紀錄。")
            return
        try:
            text = path.read_text(encoding="utf-8")
            self.txt_log.setPlainText(text or "目前尚無 log 紀錄。")
            self.txt_log.moveCursor(self.txt_log.textCursor().End)
        except Exception as e:
            QMessageBox.warning(self, "讀取失敗", f"無法讀取系統日誌：{e}")
