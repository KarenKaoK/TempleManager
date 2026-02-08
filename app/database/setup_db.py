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
    """
    建立 people 表（單表版）
    - 所有人（戶長/會員）都存在 people
    - 用 household_id 將同戶的人歸在一起
    - 用 role_in_household 區分 HEAD / MEMBER
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS people (
        -- 角色/戶籍
        id TEXT PRIMARY KEY,                           -- person UUID
        household_id TEXT NOT NULL,                    -- household UUID (同戶共用)
        role_in_household TEXT NOT NULL CHECK(role_in_household IN ('HEAD','MEMBER')),
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','INACTIVE')),

        -- 基本資料
        name TEXT NOT NULL,
        gender TEXT,
        birthday_ad TEXT,
        birthday_lunar TEXT,
        lunar_is_leap INTEGER DEFAULT 0,               -- 0/1
        birth_time TEXT,
        age INTEGER,
        zodiac TEXT,

        -- 聯絡資訊
        phone_home TEXT,
        phone_mobile TEXT,
        address TEXT,
        zip_code TEXT,

        -- 身份/備註
        note TEXT,
        joined_at TEXT
    );

    -- 常用查詢 index
    CREATE INDEX IF NOT EXISTS idx_people_household_id
    ON people(household_id);

    CREATE INDEX IF NOT EXISTS idx_people_name
    ON people(name);

    CREATE INDEX IF NOT EXISTS idx_people_phone_mobile
    ON people(phone_mobile);

    -- 同一戶只能有一位戶長（SQLite partial index）
    CREATE UNIQUE INDEX IF NOT EXISTS ux_people_one_head_per_household
    ON people(household_id)
    WHERE role_in_household = 'HEAD';
    """)

    conn.commit()
    conn.close()
    print("✅ `people` 資料表檢查完成（單表：含 household_id / role / status）")






def create_activities_table(db_name=DB_NAME):
    """建立 activities 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id TEXT PRIMARY KEY,                 -- YYYYMMDDHHMMSS（由程式產生）
        name TEXT NOT NULL,
        activity_start_date TEXT NOT NULL,
        activity_end_date TEXT NOT NULL,
        note TEXT,
        status INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)


    conn.commit()
    conn.close()
    print("✅ `activities` 資料表檢查完成")

def create_activity_plans_table(db_name=DB_NAME):
    """建立 activity_plans 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS activity_plans (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,

    name TEXT NOT NULL,                 -- 方案名稱
    items TEXT,                   -- 方案項目文字敘述

    price_type TEXT NOT NULL CHECK (price_type IN ('FIXED', 'FREE')),
    
    fixed_price INTEGER DEFAULT 0,      -- 固定金額（FIXED 用）
    note TEXT,
    suggested_price INTEGER DEFAULT 0,  -- 隨喜建議金額（FREE 顯示用）
    min_price INTEGER DEFAULT 0,        -- 隨喜最低金額（可 0）

    allow_qty INTEGER DEFAULT 1,        -- 是否允許數量（0/1）
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_activity_plans_activity_id
    ON activity_plans(activity_id);


    """)

    conn.commit()
    conn.close()
    print("✅ `activity_plans` 資料表檢查完成")

def create_activity_signups_table(db_name=DB_NAME):
    """建立 activity_signups 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS activity_signups (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    person_id TEXT NOT NULL,

    signup_time TEXT NOT NULL,           -- YYYY-MM-DD HH:MM:SS
    note TEXT,

    total_amount INTEGER NOT NULL DEFAULT 0,  -- 報名總金額快照

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE RESTRICT
    );

    CREATE INDEX IF NOT EXISTS idx_activity_signups_activity_id
    ON activity_signups(activity_id);

    CREATE INDEX IF NOT EXISTS idx_activity_signups_person_id
    ON activity_signups(person_id);


    """)

    conn.commit()
    conn.close()
    print("✅ `activity_signups` 資料表檢查完成")

def create_transactions_table(db_name=DB_NAME):
    """建立 transactions 表，儲存收支明細"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
        category_id TEXT NOT NULL, -- 強制關聯 income_items 或 expense_items
        category_name TEXT, -- 冗餘儲存項目名稱(Snapshot)
        amount INTEGER DEFAULT 0,
        payer_person_id TEXT, -- 強制關聯 people.id (僅 income 需要)
        payer_name TEXT, -- 冗餘儲存姓名(Snapshot)
        receipt_number TEXT, -- 收據號碼
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        
        -- 確保 payer_person_id 有對應的人 (雖 SQLite 預設不開 FK，但宣告有好處)
        FOREIGN KEY (payer_person_id) REFERENCES people(id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ `transactions` 資料表檢查完成")

def create_activity_signup_plans_table(db_name=DB_NAME):
    """建立 activity_signup_plans 表"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS activity_signup_plans (
    id TEXT PRIMARY KEY,
    signup_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,

    qty INTEGER NOT NULL DEFAULT 1,

    unit_price_snapshot INTEGER NOT NULL DEFAULT 0,
    amount_override INTEGER,             -- 隨喜 / 手動改價（整行總額）
    line_total INTEGER NOT NULL DEFAULT 0,

    note TEXT,

    FOREIGN KEY (signup_id) REFERENCES activity_signups(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES activity_plans(id) ON DELETE RESTRICT
    );

    CREATE INDEX IF NOT EXISTS idx_signup_plans_signup_id
    ON activity_signup_plans(signup_id);

    CREATE INDEX IF NOT EXISTS idx_signup_plans_plan_id
    ON activity_signup_plans(plan_id);


    """)

    conn.commit()
    conn.close()
    print("✅ `activity_signup_plans` 資料表檢查完成")


if __name__ == "__main__":
    print("🔄 初始化資料庫...")
    create_users_table()
    create_income_items_table()
    create_expense_items_table()  
    create_member_identity_table()
    add_default_users()



    create_people_table() # 所有人的基本資料表
    create_activities_table() # 活動主檔
    create_activity_plans_table() # 活動方案
    create_activity_signups_table() # 活動報名
    create_activity_signup_plans_table() # 活動報名方案
    create_transactions_table() # 收支明細表


    print("🎉 資料庫初始化完成！")
