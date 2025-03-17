import sqlite3
import pytest
from app.database.setup_db import (
    create_users_table,
    create_income_items_table,
    create_expense_items_table,
    create_member_identity_table
)

@pytest.fixture(scope="function")
def test_db():
    """建立測試用資料庫，並在測試結束後刪除"""
    test_db_name = "tests/temp_test.db"
    conn = sqlite3.connect(test_db_name)
    conn.close()
    
    yield test_db_name  # 讓測試使用這個資料庫
    
    # # 測試完成後刪除測試用資料庫
    # import os
    # if os.path.exists(test_db_name):
    #     os.remove(test_db_name)

def test_create_users_table(test_db):
    """測試 users 表是否能成功建立"""
    create_users_table(test_db)  # ✅ 這裡傳入 test_db
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "users 表未成功建立"

def test_create_income_items_table(test_db):
    """測試 income_items 表是否能成功建立"""
    create_income_items_table(test_db)  # ✅ 這裡傳入 test_db
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='income_items';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "income_items 表未成功建立"

def test_create_expense_items_table(test_db):
    """測試 expense_items 表是否能成功建立"""
    create_expense_items_table(test_db)  # ✅ 這裡傳入 test_db
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_items';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "expense_items 表未成功建立"

def test_create_member_identity_table(test_db):
    """測試 member_identity 表是否能成功建立"""
    create_member_identity_table(test_db)  # ✅ 這裡傳入 test_db
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='member_identity';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "member_identity 表未成功建立"
