from PyQt5.QtCore import QDate
from app.utils.date_utils import ad_to_roc_string, roc_to_ad_string


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

def test_ad_to_roc_string():
    # 1. 正常轉換 (預設分隔符號 /)
    assert ad_to_roc_string("2024-03-15") == "113/03/15"
    assert ad_to_roc_string("2024/12/31") == "113/12/31"
    
    # 2. 自訂分隔符號
    assert ad_to_roc_string("2024-03-15", separator="-") == "113-03-15"
    
    # 3. 邊界年份 (民國 1 年)
    assert ad_to_roc_string("1912-01-01") == "1/01/01"
    
    # 4. 個位數月份與日期的補零測試
    assert ad_to_roc_string("2024-3-5") == "113/03/05"
    
    # 5. 防呆測試 (空字串、None 或非日期格式)
    assert ad_to_roc_string("") == ""
    assert ad_to_roc_string(None) == ""
    assert ad_to_roc_string("invalid-date") == "invalid-date"  # 原字串吐回
    assert ad_to_roc_string("2024.03.15") == "2024.03.15"      # 不支援的符號原樣吐回


def test_roc_to_ad_string():
    # 1. 正常轉換 (預設分隔符號 -，寫入 DB 用)
    assert roc_to_ad_string("113/03/15") == "2024-03-15"
    assert roc_to_ad_string("113-12-31") == "2024-12-31"
    
    # 2. 自訂分隔符號
    assert roc_to_ad_string("113/03/15", separator="/") == "2024/03/15"
    
    # 3. 跨世紀/兩位數年份 (民國 99 年)
    assert roc_to_ad_string("99/01/01") == "2010-01-01"
    assert roc_to_ad_string("80/5/5") == "1991-05-05"
    
    # 4. 單位數輸入，確保輸出有正確補零
    assert roc_to_ad_string("1/1/1") == "1912-01-01"
    
    # 5. 防呆測試
    assert roc_to_ad_string("") == ""
    assert roc_to_ad_string(None) == ""
    assert roc_to_ad_string("不是日期") == "不是日期"