import pytest
from PyQt5.QtCore import QDate, QDateTime

from app.widgets.roc_date_edit import ROCDateEdit
from app.widgets.lighting_signup_page import ROCYearSpinBox


def test_roc_date_edit_text_conversion(qtbot):
    """測試 ROCDateEdit 攔截 QDateTime 並顯示為民國年的邏輯"""
    widget = ROCDateEdit()
    qtbot.addWidget(widget)

    # 1. 測試：底層設定西元，UI 必須吐出民國
    dt = QDateTime(QDate(2024, 3, 15))
    assert widget.textFromDateTime(dt) == "113/03/15"
    
    # 2. 測試：使用者輸入民國，底層必須轉回西元
    parsed_dt = widget.dateTimeFromText("113/03/15")
    assert parsed_dt.date() == QDate(2024, 3, 15)
    
    # 3. 測試邊界值 (民國元年)
    assert widget.textFromDateTime(QDateTime(QDate(1912, 1, 1))) == "1/01/01"
    assert widget.dateTimeFromText("1/01/01").date() == QDate(1912, 1, 1)


def test_roc_year_spinbox_conversion(qtbot):
    """測試 ROCYearSpinBox 隱藏西元並顯示民國的邏輯"""
    widget = ROCYearSpinBox()
    qtbot.addWidget(widget)

    # 1. 測試：底層設定西元 2024，畫面顯示 113
    assert widget.textFromValue(2024) == "113"
    
    # 2. 測試：使用者在畫面輸入 113，底層轉回 2024
    assert widget.valueFromText("113") == 2024
    
    # 3. 測試：使用者亂打非數字，要有容錯機制
    assert isinstance(widget.valueFromText("abc"), int)