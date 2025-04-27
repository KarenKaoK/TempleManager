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

    # ✅ 建立 users 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ✅ 建立 income_items 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)

    # ✅ 建立 expense_items 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0
        )
    """)

    # ✅ 建立 member_identity 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_identity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    conn.commit()
    conn.close()

    yield str(test_db)

    # debug用 print
    print("目前 app.config.DB_NAME =", app_config.DB_NAME)
