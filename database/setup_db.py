import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import DB_NAME

def create_users_table():
    """建立 `users` 表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('管理員', '會計', '委員', '工作人員')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def create_income_items_table():
    """建立 `income_items` 表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS income_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        amount INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def create_expense_items_table():
    """建立 `expense_items` 表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expense_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        amount INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def create_member_identity_table():
    """建立 `member_identity` 表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS member_identity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("初始化資料庫結構...")
    create_users_table()
    create_income_items_table()
    create_expense_items_table()
    create_member_identity_table()
    print("資料庫結構建立完成！")
