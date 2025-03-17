import sqlite3
import bcrypt
from app.config import DB_NAME, DEFAULT_USERS, USER_ROLES

def create_users_table(db_name=DB_NAME):
    """建立 `users` 表，儲存使用者帳號與權限"""
    print(f"📂 建立 users 表於 {db_name}")  # ✅ 確認資料庫名稱
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN {USER_ROLES}) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ `users` 資料表檢查完成（如不存在則建立）")

def create_income_items_table(db_name=DB_NAME):
    """建立 `income_items` 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS income_items (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        amount REAL DEFAULT 0
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ `income_items` 資料表檢查完成（如不存在則建立）")

def create_expense_items_table(db_name=DB_NAME):
    """建立 `expense_items` 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expense_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount INTEGER DEFAULT 0  -- ✅ 確保金額為整數
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ `expense_items` 資料表檢查完成（如不存在則建立）")

def create_member_identity_table(db_name=DB_NAME):
    """建立 `member_identity` 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS member_identity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ `member_identity` 資料表檢查完成（如不存在則建立）")
