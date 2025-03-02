import os
import sys
import sqlite3
import pytest
import bcrypt

# 設定路徑，確保能夠找到 `init_data.py`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DB_NAME
from database.init_data import add_default_users, add_default_member_identities

@pytest.fixture
def setup_database():
    """在測試前重新建立一個乾淨的資料庫"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 重新建立 `users` 資料表
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('管理員', '會計', '委員', '工作人員')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 重新建立 `member_identity` 資料表
    cursor.execute("DROP TABLE IF EXISTS member_identity")
    cursor.execute("""
    CREATE TABLE member_identity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()
    yield  # 測試完成後不做額外清理

def test_add_default_users(setup_database):
    """測試預設使用者是否正確新增"""
    add_default_users()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users")
    users = cursor.fetchall()
    conn.close()

    expected_users = [
        ("admin", "管理員"),
        ("accountant", "會計"),
        ("committee", "委員"),
        ("staff", "工作人員")
    ]

    assert len(users) == len(expected_users)
    for user in expected_users:
        assert user in users

def test_add_default_member_identities(setup_database):
    """測試預設信眾身份是否正確新增"""
    add_default_member_identities()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM member_identity")
    identities = [row[0] for row in cursor.fetchall()]
    conn.close()

    expected_identities = ["信徒", "香客", "義工"]
    
    assert len(identities) == len(expected_identities)
    for identity in expected_identities:
        assert identity in identities
