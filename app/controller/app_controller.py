# app/controller/app_controller.py
import sqlite3
from app.config import DB_NAME

class AppController:
    def __init__(self, db_path=DB_NAME):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def format_head_data(self, row):
        return {
            "id": row[0],
            "head_name": row[1],
            "head_gender": row[2],
            "head_birthday_ad": row[3],
            "head_birthday_lunar": row[4],
            "head_birth_time": row[5],
            "head_age": row[6],
            "head_zodiac": row[7],
            "head_phone_home": row[8],
            "head_phone_mobile": row[9],
            "head_email": row[10],
            "head_address": row[11],
            "head_zip_code": row[12],
            "head_identity": row[13],
            "head_note": row[14],
            "head_joined_at": row[15],
            "household_note": row[16],
        }

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


    


