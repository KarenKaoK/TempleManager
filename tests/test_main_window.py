# tests/test_main_window.py
import pytest
from app.main import MainWindow
from unittest.mock import MagicMock, PropertyMock

def test_main_window_init(qtbot):
    mock_controller = MagicMock()
    mock_controller.username = "test_user"
    mock_controller.role = "管理者"

    window = MainWindow("test_user", "管理者", mock_controller)
    qtbot.addWidget(window)

    assert window.username == "test_user"
    assert window.role == "管理者"
    assert "宮廟管理系統" in window.windowTitle()
