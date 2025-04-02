# tests/conftest.py
import os
import sqlite3
import pytest
from PyQt5.QtWidgets import QApplication
import app.config as app_config

@pytest.fixture(scope="session")
def app():
    """PyQt5 測試用的 QApplication 實例"""
    return QApplication([])

@pytest.fixture(scope="function")
def temp_db(tmp_path):
    """建立暫時測試資料庫並覆蓋 DB_NAME"""
    test_db = tmp_path / "test.db"

    # ✅ 覆蓋全域 DB_NAME，確保被測物件也用這個路徑
    app_config.DB_NAME = str(test_db) 

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # ✅ 支出項目：id 為 TEXT 主鍵
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)

    # ✅ 收入項目（假如之後有需要）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

    yield str(test_db)

    # teardown print for debug
    print("目前 app.config.DB_NAME =", app_config.DB_NAME)
