from PyQt5.QtWidgets import QDateEdit
from PyQt5.QtCore import QDateTime, QDate

from app.utils.date_utils import ad_to_roc_string, roc_to_ad_string


class ROCDateEdit(QDateEdit):
    """自訂的民國日期選擇器：底層維持西元 QDate，UI 顯示與輸入為民國年"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("yyyy/MM/dd")

    def textFromDateTime(self, dt: QDateTime) -> str:
        if not dt.isValid():
            return ""
        ad_str = dt.toString("yyyy-MM-dd")
        return ad_to_roc_string(ad_str, separator="/")

    def dateTimeFromText(self, text: str) -> QDateTime:
        ad_str = roc_to_ad_string(text, separator="-")
        qd = QDate.fromString(ad_str, "yyyy-MM-dd")
        if qd.isValid():
            return QDateTime(qd)
        return super().dateTimeFromText(text)