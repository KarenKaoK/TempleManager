# tests/test_main_window.py
import pytest
from app.main import MainWindow

def test_main_window_init(qtbot):
    username = "test_user"
    role = "管理者"
    window = MainWindow(username, role)
    qtbot.addWidget(window)

    assert window.username == username
    assert window.role == role
    assert window.windowTitle() == f"宮廟管理系統 - {role}"
