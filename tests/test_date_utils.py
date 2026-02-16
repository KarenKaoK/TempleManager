from PyQt5.QtCore import QDate

from app.utils.date_utils import (
    normalize_ymd_text,
    is_valid_ymd_text,
    parse_qdate_flexible,
    to_ui_ymd_text,
    qdate_to_db_ymd,
)


def test_normalize_ymd_text_converts_dash_to_slash():
    assert normalize_ymd_text("2026-02-16") == "2026/02/16"
    assert normalize_ymd_text("2026/02/16") == "2026/02/16"


def test_is_valid_ymd_text():
    assert is_valid_ymd_text("2026/02/16") is True
    # normalize 後仍可被判斷為合法
    assert is_valid_ymd_text("2026-02-16") is True
    assert is_valid_ymd_text("2026/2/16") is False
    assert is_valid_ymd_text("2026/13/01") is False
    assert is_valid_ymd_text("abc") is False


def test_parse_qdate_flexible_supports_slash_and_dash():
    qd1 = parse_qdate_flexible("2026/02/16")
    qd2 = parse_qdate_flexible("2026-02-16")
    assert qd1 is not None and qd1.isValid()
    assert qd2 is not None and qd2.isValid()
    assert (qd1.year(), qd1.month(), qd1.day()) == (2026, 2, 16)
    assert (qd2.year(), qd2.month(), qd2.day()) == (2026, 2, 16)


def test_to_ui_ymd_text():
    assert to_ui_ymd_text("2026-02-16") == "2026/02/16"
    assert to_ui_ymd_text("2026/02/16") == "2026/02/16"
    # 非法輸入則至少做 normalize
    assert to_ui_ymd_text("x-y-z") == "x/y/z"


def test_qdate_to_db_ymd():
    qd = QDate(2026, 2, 16)
    assert qdate_to_db_ymd(qd) == "2026-02-16"
