import sqlite3
import pytest
from app.database.setup_db import (
    create_users_table,
    create_income_items_table,
    create_expense_items_table,
    create_member_identity_table,
    create_lighting_items_table,
    create_lighting_signup_tables,
)

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.close()
    return str(db_path)

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

def test_create_lighting_items_table(test_db):
    """測試 lighting_items 表是否能成功建立"""
    create_lighting_items_table(test_db)
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lighting_items';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None, "lighting_items 表未成功建立"

def test_create_lighting_signup_tables(test_db):
    create_lighting_signup_tables(test_db)
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lighting_signups';")
    result1 = cursor.fetchone()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lighting_signup_items';")
    result2 = cursor.fetchone()
    conn.close()
    assert result1 is not None, "lighting_signups 表未成功建立"
    assert result2 is not None, "lighting_signup_items 表未成功建立"
