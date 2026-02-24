from typing import Optional

from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QDialog, QPushButton, QApplication, QMessageBox, QInputDialog, QFileDialog


_BUTTON_TEXT_MAP = {
    "yes": "是",
    "no": "否",
    "ok": "好",
    "cancel": "取消",
    "close": "關閉",
    "open": "開啟",
    "save": "儲存",
    "save all": "全部儲存",
    "apply": "套用",
    "retry": "重試",
    "ignore": "忽略",
    "abort": "中止",
    "discard": "捨棄",
    "reset": "重設",
    "restore defaults": "還原預設值",
}


def translate_dialog_button_text(text: str) -> Optional[str]:
    """
    將 Qt 標準英文字按鈕轉為中文。
    只做精準 mapping；若不是已知英文按鈕文字則回傳 None（不改動）。
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    normalized = raw.replace("&", "").strip()
    normalized = normalized.rstrip(":").strip()
    if normalized.endswith("..."):
        normalized = normalized[:-3].strip()
    return _BUTTON_TEXT_MAP.get(normalized.lower())


class DialogButtonLocalizer(QObject):
    """
    全域事件過濾器：當 QDialog 顯示時，自動將標準英文字按鈕替換為中文。
    適用 QMessageBox / QFileDialog / QInputDialog 等 Qt 標準彈窗。
    """

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and self._is_supported_dialog(obj):
            self._safe_localize(obj)
        return super().eventFilter(obj, event)

    @staticmethod
    def _is_supported_dialog(obj) -> bool:
        # 僅處理 Qt 標準彈窗，避免干擾自訂 QDialog（例如登入視窗）造成平台穩定性問題
        return isinstance(obj, (QMessageBox, QInputDialog, QFileDialog))

    def _safe_localize(self, dialog):
        try:
            self._localize_dialog_buttons(dialog)
        except (RuntimeError, TypeError):
            pass

    def _localize_dialog_buttons(self, dialog: QDialog):
        for btn in dialog.findChildren(QPushButton):
            new_text = translate_dialog_button_text(btn.text())
            if new_text:
                btn.setText(new_text)


def install_dialog_localizer(app: QApplication):
    """
    安裝全域彈窗按鈕中文化事件過濾器（僅安裝一次）。
    """
    if app is None:
        return
    if getattr(app, "_dialog_button_localizer_installed", False):
        return
    localizer = DialogButtonLocalizer(app)
    app.installEventFilter(localizer)
    app._dialog_button_localizer = localizer
    app._dialog_button_localizer_installed = True
