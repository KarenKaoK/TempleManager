import os

# 設定專案根目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 資料庫路徑
DB_NAME = os.path.join(BASE_DIR, "./database/temple.db")

# 預設使用者帳號
DEFAULT_USERS = [
    ("admin", "admin123", "管理員"),
    ("accountant", "acc123", "會計"),
    ("committee", "com123", "委員"),
    ("staff", "staff123", "工作人員")
]

# 角色類型
USER_ROLES = ('管理員', '會計', '委員', '工作人員')
