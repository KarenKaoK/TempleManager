from PyQt5.QtWidgets import QDialog, QMessageBox, QInputDialog, QFileDialog

from app.utils.dialog_localizer import translate_dialog_button_text
from app.utils.dialog_localizer import DialogButtonLocalizer


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


def test_dialog_localizer_only_targets_standard_dialogs():
    assert DialogButtonLocalizer._is_supported_dialog(QMessageBox()) is True
    assert DialogButtonLocalizer._is_supported_dialog(QInputDialog()) is True
    assert DialogButtonLocalizer._is_supported_dialog(QFileDialog()) is True
    assert DialogButtonLocalizer._is_supported_dialog(QDialog()) is False
