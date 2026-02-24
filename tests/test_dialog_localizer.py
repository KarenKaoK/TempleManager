from app.utils.dialog_localizer import translate_dialog_button_text


def test_translate_dialog_button_text_basic():
    assert translate_dialog_button_text("Yes") == "是"
    assert translate_dialog_button_text("No") == "否"
    assert translate_dialog_button_text("OK") == "好"
    assert translate_dialog_button_text("Cancel") == "取消"


def test_translate_dialog_button_text_with_qt_ampersand():
    assert translate_dialog_button_text("&Yes") == "是"
    assert translate_dialog_button_text("&No") == "否"
    assert translate_dialog_button_text("&OK") == "好"


def test_translate_dialog_button_text_unknown_returns_none():
    assert translate_dialog_button_text("重新整理") is None
    assert translate_dialog_button_text("") is None
    assert translate_dialog_button_text(None) is None
