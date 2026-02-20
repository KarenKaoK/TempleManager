import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)


class CoverSettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._image_path = ""
        self.setWindowTitle("封面設定")
        self.resize(780, 520)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)

        root.addWidget(QLabel("登入封面照片"))
        self.lbl_preview = QLabel("尚未設定封面照片")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setFixedHeight(260)
        self.lbl_preview.setStyleSheet(
            "QLabel { border: 1px solid #E6D8C7; border-radius: 8px; background: #FAF5EF; color: #7A6B5D; }"
        )
        root.addWidget(self.lbl_preview)

        row_pick = QHBoxLayout()
        self.edt_image_path = QLineEdit()
        self.edt_image_path.setReadOnly(True)
        self.edt_image_path.setPlaceholderText("尚未選擇照片")
        btn_pick = QPushButton("上傳照片")
        btn_clear = QPushButton("清除照片")
        btn_pick.clicked.connect(self._pick_image)
        btn_clear.clicked.connect(self._clear_image)
        row_pick.addWidget(self.edt_image_path, 1)
        row_pick.addWidget(btn_pick)
        row_pick.addWidget(btn_clear)
        root.addLayout(row_pick)

        root.addWidget(QLabel("登入標題（毛筆風）"))
        self.edt_title = QLineEdit()
        self.edt_title.setPlaceholderText("例如：深坑天南宮")
        root.addWidget(self.edt_title)

        footer = QHBoxLayout()
        footer.addStretch()
        btn_save = QPushButton("儲存")
        btn_close = QPushButton("關閉")
        btn_save.clicked.connect(self._save_settings)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_save)
        footer.addWidget(btn_close)
        root.addLayout(footer)

    def _load_settings(self):
        data = self.controller.get_login_cover_settings()
        self.edt_title.setText(data.get("title") or "")
        self._image_path = (data.get("image_path") or "").strip()
        self._refresh_preview()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇封面照片",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not path:
            return
        self._image_path = path
        self._refresh_preview()

    def _clear_image(self):
        self._image_path = ""
        self._refresh_preview()

    def _refresh_preview(self):
        self.edt_image_path.setText(self._image_path)
        if self._image_path and os.path.exists(self._image_path):
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                self.lbl_preview.setPixmap(
                    pixmap.scaled(
                        self.lbl_preview.contentsRect().size(),
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation,
                    )
                )
                self.lbl_preview.setText("")
                return
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_preview.setText("尚未設定封面照片")

    def _save_settings(self):
        self.controller.save_login_cover_settings(
            (self.edt_title.text() or "").strip(),
            (self._image_path or "").strip(),
        )
        QMessageBox.information(self, "成功", "封面設定已儲存")
