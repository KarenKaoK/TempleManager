# app/controller/app_controller.py
import sqlite3
from app.config import DB_NAME

class AppController:
    def __init__(self, db_path=DB_NAME):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def search_households(self, keyword):
        cursor = self.conn.cursor()
        like_value = f"%{keyword}%"
        query = """
            SELECT * FROM households
            WHERE head_name LIKE ? OR head_phone_home LIKE ? OR head_phone_mobile LIKE ?
        """
        cursor.execute(query, (like_value, like_value, like_value))
        return [dict(row) for row in cursor.fetchall()]
