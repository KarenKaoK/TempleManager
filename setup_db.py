import sqlite3
import bcrypt

DB_NAME = "temple.db"  # ✅ 確保統一使用 users.db

def create_users_table():
    """建立 `users` 表，儲存使用者帳號與權限"""
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
    print("✅ `users` 資料表檢查完成（如不存在則建立）")

def create_income_items_table():
    """建立 `income_items` 表，儲存收入項目"""
    conn = sqlite3.connect(DB_NAME)
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

def create_expense_items_table():
    """建立 `expense_items` 表，儲存支出項目"""
    conn = sqlite3.connect(DB_NAME)
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

def create_member_identity_table():
    """建立 `member_identity` 表，存放信眾身份名稱"""
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
    print("✅ `member_identity` 資料表檢查完成（如不存在則建立）")

def add_default_users():
    """新增預設角色帳號（管理員、會計、委員、工作人員）"""
    users = [
        ("admin", "admin123", "管理員"),
        ("accountant", "acc123", "會計"),
        ("committee", "com123", "委員"),
        ("staff", "staff123", "工作人員")
    ]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for username, password, role in users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone() is None:  # 🔹 確保帳號不存在才建立
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                           (username, hashed_pw, role))
            print(f"✅ 已建立帳號 {username}（{role}）")
        else:
            print(f"⚠️ 帳號 {username} 已存在，跳過")

    conn.commit()
    conn.close()
    print("✅ 預設使用者建立完成！")


if __name__ == "__main__":
    print("🔄 初始化資料庫...")
    create_users_table()
    create_income_items_table()
    create_expense_items_table()  # ✅ 新增 `expense_items` 表
    create_member_identity_table()
    add_default_users()
    print("🎉 資料庫初始化完成！")
