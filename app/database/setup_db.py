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
        id TEXT PRIMARY KEY,
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
        id TEXT PRIMARY KEY,
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
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ `member_identity` 資料表檢查完成（如不存在則建立）")

def add_default_users(db_name=DB_NAME):
    """新增預設角色帳號（管理員、會計、委員、工作人員）"""
    users = [
        ("t", "", "管理員"),
        ("admin", "admin123", "管理員"),
        ("accountant", "acc123", "會計"),
        ("committee", "com123", "委員"),
        ("staff", "staff123", "工作人員")
    ]

    conn = sqlite3.connect(db_name)
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

def create_people_table(db_name=DB_NAME):
    """建立 people 表，儲存個人基本資料"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS people (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        gender TEXT,
        birthday_ad TEXT,
        birthday_lunar TEXT,
        birth_time TEXT,
        age INTEGER,
        zodiac TEXT,
        phone_home TEXT,
        phone_mobile TEXT,
        email TEXT,
        address TEXT,
        zip_code TEXT,
        identity TEXT,
        note TEXT,
        joined_at TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("✅ `people` 資料表檢查完成")

def create_households_table(db_name=DB_NAME):
    """建立 households 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS households (
        id TEXT PRIMARY KEY,
        head_person_id TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(head_person_id) REFERENCES people(id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ `households` 資料表檢查完成")

def create_household_members_table(db_name=DB_NAME):
    """建立 household_members 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS household_members (
        id TEXT PRIMARY KEY,
        household_id TEXT NOT NULL,
        person_id TEXT NOT NULL,
        relationship TEXT,
        FOREIGN KEY(household_id) REFERENCES households(id),
        FOREIGN KEY(person_id) REFERENCES people(id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ `household_members` 資料表檢查完成")


if __name__ == "__main__":
    print("🔄 初始化資料庫...")
    create_users_table()
    create_income_items_table()
    create_expense_items_table()  
    create_member_identity_table()
    add_default_users()

    create_people_table() # 所有人的基本資料表
    create_households_table() # 戶長表
    create_household_members_table() # 戶長和戶員關係表

    print("🎉 資料庫初始化完成！")
