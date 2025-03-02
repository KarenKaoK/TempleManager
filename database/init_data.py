import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sqlite3
import bcrypt
from config import DB_NAME

def add_default_users():
    """新增預設使用者"""
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
        if cursor.fetchone() is None:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                           (username, hashed_pw, role))
            print(f"已建立帳號 {username}（{role}）")
        else:
            print(f"帳號 {username} 已存在，跳過")

    conn.commit()
    conn.close()

def add_default_member_identities():
    """新增預設信眾身份"""
    identities = ["信徒", "香客", "義工"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for identity in identities:
        cursor.execute("SELECT id FROM member_identity WHERE name = ?", (identity,))
        if cursor.fetchone() is None:
            cursor.execute("INSERT INTO member_identity (name) VALUES (?)", (identity,))
            print(f"已建立身份 {identity}")
        else:
            print(f"身份 {identity} 已存在，跳過")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("初始化預設數據...")
    add_default_users()
    add_default_member_identities()
    print("預設數據初始化完成！")
