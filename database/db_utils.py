import sqlite3
from config import DB_NAME

class Database:
    """統一管理資料庫連線"""

    @staticmethod
    def connect():
        """建立資料庫連線"""
        return sqlite3.connect(DB_NAME)

    @staticmethod
    def execute(query, params=()):
        """執行 SQL 指令"""
        conn = Database.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()

    @staticmethod
    def fetchall(query, params=()):
        """執行 SQL 查詢並回傳所有結果"""
        conn = Database.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
