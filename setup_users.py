import sqlite3
import bcrypt

def create_users_table():
    """建立 SQLite 資料庫與 users 表，支援多個角色"""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'accountant', 'committee', 'staff')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("資料表檢查完成（如不存在則建立）")

def add_default_users():
    """新增預設角色帳號（admin, accountant, committee, staff）"""
    users = [
        ("admin", "admin123", "admin"),
        ("accountant", "acc123", "accountant"),
        ("committee", "com123", "committee"),
        ("staff", "staff123", "staff")
    ]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    for username, password, role in users:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():  # 帳號不存在，則新增
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                           (username, hashed_pw, role))
            print(f"已建立 {username}（{role}）")
        else:
            print(f"⚠️ 帳號 {username} 已存在，跳過")

    conn.commit()
    conn.close()
    print("所有角色帳號已建立完成！")

if __name__ == "__main__":
    create_users_table()
    add_default_users()
