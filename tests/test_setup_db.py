import os
import sqlite3
import pytest
from database.setup_db import (
    create_users_table,
    create_income_items_table,
    create_expense_items_table,
    create_member_identity_table,
)
from config import DB_NAME

@pytest.fixture(scope="module")
def setup_database():
    """執行 setup_db.py 內的所有資料表建立函式，並在測試完成後刪除資料庫"""
    create_users_table()
    create_income_items_table()
    create_expense_items_table()
    create_member_identity_table()
    yield
    os.remove(DB_NAME)  # 測試完成後移除資料庫檔案，保持乾淨

def test_database_file_exists(setup_database):
    """測試是否成功建立資料庫檔案"""
    assert os.path.exists(DB_NAME), "❌ 資料庫檔案未建立"

def test_users_table_exists(setup_database):
    """測試 `users` 資料表是否存在"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "❌ `users` 資料表未建立"

def test_income_items_table_exists(setup_database):
    """測試 `income_items` 資料表是否存在"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='income_items'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "❌ `income_items` 資料表未建立"

def test_expense_items_table_exists(setup_database):
    """測試 `expense_items` 資料表是否存在"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_items'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "❌ `expense_items` 資料表未建立"

def test_member_identity_table_exists(setup_database):
    """測試 `member_identity` 資料表是否存在"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='member_identity'")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "❌ `member_identity` 資料表未建立"
