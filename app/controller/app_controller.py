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
    def get_household_members(self, household_id):
        cursor = self.conn.cursor()
        query = """
            SELECT p.*
            FROM household_members hm
            JOIN people p ON hm.person_id = p.id
            WHERE hm.household_id = ?
        """
        cursor.execute(query, (household_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_by_any_name(self, keyword):
        cursor = self.conn.cursor()

        # 搜尋戶長
        cursor.execute("""
            SELECT * FROM households
            WHERE head_name LIKE ?
            LIMIT 1
        """, (f"%{keyword}%",))
        head_row = cursor.fetchone()

        if head_row:
            household_id = head_row[0]  # 假設 household.id 在第 0 欄
        else:
            # 沒找到戶長 → 查 household_members 對應的 people.name
            cursor.execute("""
                SELECT hm.household_id
                FROM household_members hm
                JOIN people p ON hm.person_id = p.id
                WHERE p.name LIKE ?
                LIMIT 1
            """, (f"%{keyword}%",))
            row = cursor.fetchone()
            if row:
                household_id = row[0]
                cursor.execute("SELECT * FROM households WHERE id = ?", (household_id,))
                head_row = cursor.fetchone()
            else:
                return None, []

        # 查 household_id 對應的戶員
        members = self.get_household_members(household_id)
        return head_row, members

    def format_head_data(self, row):
        return dict(row)


    


