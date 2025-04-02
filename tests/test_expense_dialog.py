import pytest
import sqlite3
from PyQt5.QtWidgets import QDialog
from app.dialogs.expense_dialog import ExpenseSetupDialog

def test_expense_dialog_load_data(qtbot, temp_db):
    """測試支出視窗能正確載入資料（id 改為 TEXT）"""
    dialog = ExpenseSetupDialog(db_path=str(temp_db))
    qtbot.addWidget(dialog)

    # 插入一筆資料（手動給 id）
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("E001", "香油錢", 300))
    conn.commit()
    rows = conn.execute("SELECT * FROM expense_items").fetchall()
    conn.close()

    dialog.load_data()

    assert dialog.table.rowCount() == len(rows)
    assert dialog.table.item(0, 0).text() == "E001"
    assert dialog.table.item(0, 1).text() == "香油錢"
    assert dialog.table.item(0, 2).text() == "300"

def test_expense_dialog_add_item_success(qtbot, temp_db, monkeypatch):
    """測試成功新增支出項目（文字型 id）"""
    dialog = ExpenseSetupDialog(db_path=str(temp_db))
    qtbot.addWidget(dialog)

    # mock QMessageBox 防止跳視窗
    monkeypatch.setattr("PyQt5.QtWidgets.QMessageBox.information", lambda *args, **kwargs: None)

    dialog.confirm_add_expense_item(QDialog(), "E002", "供品", 500)

    conn = sqlite3.connect(temp_db)
    result = conn.execute("SELECT * FROM expense_items WHERE id = ?", ("E002",)).fetchone()
    conn.close()

    assert result is not None
    assert result[0] == "E002"
    assert result[1] == "供品"
    assert result[2] == 500
