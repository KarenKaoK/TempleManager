import re
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import QDate, QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator


YMD_SLASH = "%Y/%m/%d"


def normalize_ymd_text(value: str) -> str:
    """Normalize supported date separators to YYYY/MM/DD style text."""
    return str(value or "").strip().replace("-", "/")


def is_valid_ymd_text(value: str) -> bool:
    normalized = normalize_ymd_text(value)
    if not re.match(r"^\d{4}/\d{2}/\d{2}$", normalized):
        return False
    try:
        datetime.strptime(normalized, YMD_SLASH)
        return True
    except Exception:
        return False


def make_ymd_validator(parent=None) -> QRegularExpressionValidator:
    return QRegularExpressionValidator(QRegularExpression(r"^\d{4}/\d{2}/\d{2}$"), parent)


def parse_qdate_flexible(value: str) -> Optional[QDate]:
    s = str(value or "").strip()
    if not s:
        return None
    for fmt in ("yyyy/MM/dd", "yyyy-MM-dd"):
        qd = QDate.fromString(s, fmt)
        if qd.isValid():
            return qd
    return None


def to_ui_ymd_text(value: str) -> str:
    qd = parse_qdate_flexible(value)
    if qd is None:
        return normalize_ymd_text(value)
    return qd.toString("yyyy/MM/dd")


def qdate_to_db_ymd(qd: QDate) -> str:
    return qd.toString("yyyy-MM-dd")
