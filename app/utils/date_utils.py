import re
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import QDate, QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator


YMD_SLASH = "%Y/%m/%d"


def normalize_ymd_text(value: str) -> str:
    """Normalize supported date separators to canonical YYYY/MM/DD text."""
    text = str(value or "").strip().replace("-", "/")
    if not text:
        return ""
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", text)
    if not m:
        return text
    y, mo, d = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d))
    except Exception:
        return text
    return dt.strftime(YMD_SLASH)


def is_valid_ymd_text(value: str) -> bool:
    text = str(value or "").strip().replace("-", "/")
    if not re.match(r"^\d{4}/\d{2}/\d{2}$", text):
        return False
    try:
        datetime.strptime(text, YMD_SLASH)
        return True
    except Exception:
        return False


def make_ymd_validator(parent=None) -> QRegularExpressionValidator:
    # Allow 1-2 digit month/day while typing; normalized on blur/save.
    return QRegularExpressionValidator(QRegularExpression(r"^\d{0,4}([/-]\d{0,2}([/-]\d{0,2})?)?$"), parent)


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


def ad_to_roc_string(ad_str: str, separator: str = "/") -> str:
    """
    西元日期字串轉換為民國日期字串
    (例如: '2024-03-15' -> '113/03/15')
    """
    if not ad_str:
        return ""
    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", str(ad_str).strip())
    if not m:
        return str(ad_str)
    y, mo, d = m.groups()
    roc_year = int(y) - 1911
    return f"{roc_year}{separator}{int(mo):02d}{separator}{int(d):02d}"


def roc_to_ad_string(roc_str: str, separator: str = "-") -> str:
    """
    民國日期字串轉換為西元日期字串
    (例如: '113/03/15' -> '2024-03-15' 或 '99-1-1' -> '2010-01-01')
    """
    if not roc_str:
        return ""
    m = re.search(r"(\d{1,3})[/-](\d{1,2})[/-](\d{1,2})", str(roc_str).strip())
    if not m:
        return str(roc_str)
    y, mo, d = m.groups()
    ad_year = int(y) + 1911
    return f"{ad_year}{separator}{int(mo):02d}{separator}{int(d):02d}"
