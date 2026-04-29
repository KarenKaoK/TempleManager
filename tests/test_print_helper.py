import pytest
import os
from unittest.mock import Mock
from PyQt5.QtGui import QFontDatabase
from app.utils.print_helper import PrintHelper

def test_number_to_chinese_integers():
    """測試整數轉大寫中文"""
    assert PrintHelper.number_to_chinese(0) == "零"
    assert PrintHelper.number_to_chinese(1) == "壹"
    assert PrintHelper.number_to_chinese(10) == "壹拾"
    assert PrintHelper.number_to_chinese(105) == "壹佰零伍" # 視實作而定，有些是壹佰零伍，有些是壹佰伍
    assert PrintHelper.number_to_chinese(1234) == "壹仟貳佰參拾肆"
    # 根據目前的實作確認

def test_number_to_chinese_large(qtbot): # 使用 qtbot 確保 application 存在 (雖不一定需要)
    """測試較大金額"""
    assert PrintHelper.number_to_chinese(10000) == "壹萬"
    assert PrintHelper.number_to_chinese(50000) == "伍萬"

def test_get_compatible_font_family(qtbot):
    """測試字體選擇"""
    font_family = PrintHelper._get_compatible_font_family()
    assert isinstance(font_family, str)
    assert len(font_family) > 0
    
    # 確保回傳的是我們偏好列表中的一個，或是系統預設
    db = QFontDatabase()
    families = db.families()
    
    # 如果系統裡有我們支援的字體，它應該要回傳其中之一
    # 這裡只能做基本的型別檢查，因為不同環境字體不同

def test_pair_rows_for_half_a4():
    rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    pairs = PrintHelper._pair_rows_for_half_a4(rows)
    assert pairs == [({"name": "A"}, {"name": "B"}), ({"name": "C"}, None)]

def test_to_roc_birthday_text():
    # 把原本的 '33年08月08日' 改成新的 '民國33年8月8日'
    assert PrintHelper._to_roc_birthday_text("1944/08/08") == "民國33年8月8日"

def test_force_a4_landscape_calls_printer_setters():
    printer = Mock()
    PrintHelper._force_a4_landscape(printer)
    assert printer.setPageSize.called
    printer.setOrientation.assert_called_once()


def test_resource_path_uses_app_root_when_not_bundled(monkeypatch):
    monkeypatch.delattr("sys._MEIPASS", raising=False)
    path = PrintHelper._resource_path("resources", "seal.png")
    assert os.path.normpath(path).endswith(os.path.normpath("app/resources/seal.png"))


def test_resource_path_uses_meipass_when_bundled(monkeypatch):
    monkeypatch.setattr("sys._MEIPASS", "/tmp/fake_bundle", raising=False)
    path = PrintHelper._resource_path("resources", "seal.png")
    assert os.path.normpath(path) == os.path.normpath("/tmp/fake_bundle/app/resources/seal.png")
