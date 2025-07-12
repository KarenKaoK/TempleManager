# app/controller/app_controller.py
import locale
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
    def add_new_household(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO households (
                head_name, head_gender, head_birthday_ad, head_birthday_lunar,
                head_birth_time, head_age, head_zodiac, head_phone_home,
                head_phone_mobile, head_email, head_address, head_zip_code,
                head_identity, head_note, head_joined_at, household_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("head_name"), data.get("head_gender"), data.get("head_birthday_ad"),
            data.get("head_birthday_lunar"), data.get("head_birth_time"), data.get("head_age"),
            data.get("head_zodiac"), data.get("head_phone_home"), data.get("head_phone_mobile"),
            data.get("head_email"), data.get("head_address"), data.get("head_zip_code"),
            data.get("head_identity"), data.get("head_note"), data.get("head_joined_at"),
            data.get("household_note")
        ))
        self.conn.commit()

    def insert_household(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO households (
                head_name, head_gender, head_birthday_ad, head_birthday_lunar, head_birth_time,
                head_age, head_zodiac, head_phone_home, head_phone_mobile, head_email,
                head_address, head_zip_code, head_identity, head_note, head_joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["head_name"],
            data["head_gender"],
            data["head_birthday_ad"],
            data["head_birthday_lunar"],
            data["head_birth_time"],
            data["head_age"],
            data["head_zodiac"],
            data["head_phone_home"],
            data["head_phone_mobile"],
            data["head_email"],
            data["head_address"],
            data["head_zip_code"],
            data["head_identity"],
            data["head_note"],
            data["head_joined_at"]
        ))
        self.conn.commit()
    
    def get_all_households_ordered(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM households")
        rows = [dict(row) for row in cursor.fetchall()]

        # 設定locale（注意: 要在支援中文排序的系統）
        locale.setlocale(locale.LC_COLLATE, "zh_TW.UTF-8")

        # 排序
        rows.sort(key=lambda x: locale.strxfrm(x["head_name"]))

        return rows
    
    def household_has_members(self, household_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM household_members
            WHERE household_id = ?
        """, (household_id,))
        count = cursor.fetchone()[0]
        return count > 0

    def delete_household(self, household_id):
        cursor = self.conn.cursor()

        # 先刪 household_members（避免外鍵違反）
        cursor.execute("""
            DELETE FROM household_members
            WHERE household_id = ?
        """, (household_id,))

        # 再刪 households
        cursor.execute("""
            DELETE FROM households
            WHERE id = ?
        """, (household_id,))

        self.conn.commit()

    def get_all_member_identities(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, name FROM member_identity
            ORDER BY name COLLATE NOCASE ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def add_member_identity(self, identity_id, name):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO member_identity (id, name)
            VALUES (?, ?)
        """, (identity_id, name))
        self.conn.commit()

    def update_member_identity(self, identity_id, new_name):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE member_identity
            SET name = ?
            WHERE id = ?
        """, (new_name, identity_id))
        self.conn.commit()
    
    def delete_member_identity(self, identity_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM member_identity
            WHERE id = ?
        """, (identity_id,))
        self.conn.commit()




    


