# app/controller/app_controller.py
import uuid
import locale
import sqlite3
from app.config import DB_NAME
from datetime import datetime
from app.utils.id_utils import generate_activity_id_safe, new_plan_id

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

    def insert_member(self, data):
        data["id"] = str(uuid.uuid4())
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO people (
                id, name, gender, birthday_ad, birthday_lunar, birth_time,
                age, zodiac, phone_home, phone_mobile, email,
                address, zip_code, identity, note, joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"], data["name"], data["gender"], data["birthday_ad"], data["birthday_lunar"],
            data["birth_time"], data["age"], data["zodiac"], data["phone_home"], data["phone_mobile"],
            data["email"], data["address"], data["zip_code"], data["identity"], data["note"], 
            data["joined_at"]
        ))
        cursor.execute("""
            INSERT INTO household_members (household_id, person_id)
            VALUES (?, ?)
        """, (
            data["household_id"],
            data["id"]
        ))
        self.conn.commit()

    def update_member(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE people SET
                name=?, gender=?, birthday_ad=?, birthday_lunar=?, birth_time=?,
                age=?, zodiac=?, phone_home=?, phone_mobile=?, email=?,
                address=?, zip_code=?, identity=?, note=?, joined_at=?,
                lunar_is_leap=?, id_number=?
            WHERE id=?
        """, (
            data["name"], data["gender"], data["birthday_ad"], data["birthday_lunar"], data["birth_time"],
            data["age"], data["zodiac"], data["phone_home"], data["phone_mobile"], data["email"],
            data["address"], data["zip_code"], data["identity"], data["note"], data["joined_at"],
            data["lunar_is_leap"], data["id_number"], data["id"]
        ))
        self.conn.commit()

    def delete_member_by_id(self, person_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self.conn.commit()

    def get_member_by_id(self, person_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        return None
    


    def get_household_by_id(self, household_id):
        """根據 household_id 取得戶長資料"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, head_name, head_gender, head_birthday_ad, head_birthday_lunar,
                head_birth_time, head_age, head_zodiac, head_phone_home, head_phone_mobile,
                head_email, head_address, head_zip_code, head_identity, head_note, head_joined_at
            FROM households
            WHERE id = ?
        """, (household_id,))
        row = cursor.fetchone()

        if row is None:
            return {}

        # 欄位順序需與 SELECT 對應
        keys = [
            "id", "head_name", "head_gender", "head_birthday_ad", "head_birthday_lunar",
            "head_birth_time", "head_age", "head_zodiac", "head_phone_home", "head_phone_mobile",
            "head_email", "head_address", "head_zip_code", "head_identity", "head_note", "head_joined_at"
        ]
        return dict(zip(keys, row))

    # def generate_activity_id(self):
    #     today_str = datetime.now().strftime("%Y%m%d")
    #     cursor = self.conn.cursor()
    #     cursor.execute("""
    #         SELECT COUNT(DISTINCT activity_id)
    #         FROM activities
    #         WHERE activity_id LIKE ?
    #     """, (f"{today_str}%",))
    #     count = cursor.fetchone()[0] + 1
    #     return f"{today_str}-{count:03}"

    # def insert_activity(self, data: dict):
    #     cursor = self.conn.cursor()
    #     activity_id = self.generate_activity_id()

    #     for scheme in data.get("scheme_rows", []):
    #         row_id = "R" + uuid.uuid4().hex[:8]

    #         cursor.execute("""
    #             INSERT INTO activities (
    #                 id, activity_id, name, start_date, end_date,
    #                 scheme_name, scheme_item, amount, note,
    #                 is_closed, created_at, updated_at
    #             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    #         """, (
    #             row_id,
    #             activity_id,
    #             data.get("activity_name"),
    #             data.get("start_date"),
    #             data.get("end_date"),
    #             scheme.get("scheme_name"),  # ✅ 這裡要對應你在 get_scheme_data() 傳回的 key
    #             scheme.get("scheme_item"),
    #             float(scheme.get("amount") or 0),
    #             data.get("content"),
    #             0  # is_closed
    #         ))

    #     self.conn.commit()

    # def get_all_activities(self):
    #     cursor = self.conn.cursor()
    #     cursor.execute("""
    #         SELECT 
    #             activity_id,
    #             name,
    #             start_date,
    #             end_date,
    #             GROUP_CONCAT(scheme_name, CHAR(10)) AS scheme_names,
    #             GROUP_CONCAT(scheme_item, CHAR(10)) AS scheme_items,
    #             GROUP_CONCAT(amount, CHAR(10)) AS amounts,
    #             is_closed
    #         FROM activities
    #         GROUP BY activity_id
    #         ORDER BY MAX(created_at) DESC
    #     """)
    #     return cursor.fetchall()
    
    # def search_activities(self, keyword):
    #     cursor = self.conn.cursor()
    #     like_pattern = f"%{keyword}%"

    #     cursor.execute("""
    #         SELECT 
    #             activity_id,
    #             name,
    #             start_date,
    #             end_date,
    #             GROUP_CONCAT(scheme_name, CHAR(10)) AS scheme_names,
    #             GROUP_CONCAT(scheme_item, CHAR(10)) AS scheme_items,
    #             GROUP_CONCAT(amount, CHAR(10)) AS amounts,
    #             is_closed
    #         FROM activities
    #         WHERE 
    #             activity_id LIKE ? OR
    #             name LIKE ? OR
    #             start_date LIKE ?
    #         GROUP BY activity_id
    #         ORDER BY MAX(created_at) DESC
    #     """, (like_pattern, like_pattern, like_pattern))

    #     return cursor.fetchall()
    
    # def get_activity_by_id(self, activity_id):
    #     cursor = self.conn.cursor()
    #     cursor.execute("""
    #         SELECT name, start_date, end_date, note
    #         FROM activities
    #         WHERE activity_id = ?
    #         LIMIT 1
    #     """, (activity_id,))
    #     basic_info = cursor.fetchone()

    #     cursor.execute("""
    #         SELECT scheme_name, scheme_item, amount
    #         FROM activities
    #         WHERE activity_id = ?
    #     """, (activity_id,))
    #     scheme_rows = [
    #         {
    #             "scheme_name": row[0],
    #             "scheme_item": row[1],
    #             "amount": row[2]
    #         }
    #         for row in cursor.fetchall()
    #     ]

    #     activity_data = {
    #         "activity_id": activity_id,
    #         "activity_name": basic_info[0],
    #         "start_date": basic_info[1],
    #         "end_date": basic_info[2],
    #         "content": basic_info[3]
    #     }

    #     return activity_data, scheme_rows
    
    

    # def delete_activity(self, activity_id):
    #     try:
    #         cursor = self.conn.cursor()
    #         cursor.execute("DELETE FROM activities WHERE activity_id = ?", (activity_id,))
    #         self.conn.commit()
    #         return cursor.rowcount > 0
    #     except Exception as e:
    #         print("❌ 刪除活動時出錯：", e)
    #         return False

    # def insert_activity_signup(self, signup_data):
    #     """新增活動報名人員資料"""
    #     try:
    #         cursor = self.conn.cursor()
            
    #         # 處理活動項目資料
    #         selected_items = signup_data.get("selected_items", [])
    #         activity_items_text = ""
    #         if selected_items:
    #             items_list = []
    #             for item in selected_items:
    #                 items_list.append(f"{item['item_name']} x{item['quantity']}")
    #             activity_items_text = "; ".join(items_list)
            
    #         # 插入報名人員基本資料
    #         cursor.execute("""
    #             INSERT INTO activity_signups (
    #                 activity_id, person_name, gender, birth_ad, birth_lunar,
    #                 zodiac, birth_time, phone, mobile, identity, identity_number,
    #                 address, note, activity_items, activity_amount, receipt_number, created_at
    #             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    #         """, (
    #             signup_data.get("activity_id"),
    #             signup_data.get("name"),
    #             signup_data.get("gender"),
    #             signup_data.get("gregorian_birthday"),
    #             signup_data.get("lunar_birthday"),
    #             signup_data.get("zodiac"),
    #             signup_data.get("birth_time"),
    #             signup_data.get("contact_phone"),
    #             signup_data.get("contact_phone"),  # 使用相同電話號碼
    #             signup_data.get("identity", ""),
    #             signup_data.get("identity_number", ""),
    #             signup_data.get("address"),
    #             signup_data.get("remarks"),
    #             activity_items_text,
    #             signup_data.get("activity_amount", 0),
    #             signup_data.get("receipt_number", ""),
    #             signup_data.get("registration_date")
    #         ))
            
    #         self.conn.commit()
    #         return True
    #     except Exception as e:
    #         print(f"❌ 新增報名人員時出錯：{e}")
    #         return False

    # def get_activity_signups(self, activity_id):
    #     """取得特定活動的報名人員列表"""
    #     try:
    #         cursor = self.conn.cursor()
    #         cursor.execute("""
    #             SELECT 
    #                 id, person_name, gender, birth_ad, birth_lunar,
    #                 zodiac, birth_time, phone, mobile, identity, identity_number,
    #                 address, note, activity_items, activity_amount, receipt_number, created_at
    #             FROM activity_signups
    #             WHERE activity_id = ?
    #             ORDER BY created_at DESC
    #         """, (activity_id,))
            
    #         return [dict(row) for row in cursor.fetchall()]
    #     except Exception as e:
    #         print(f"❌ 取得報名人員列表時出錯：{e}")
    #         return []

    # def search_activity_signups(self, activity_id, keyword):
    #     """搜尋特定活動的報名人員"""
    #     try:
    #         cursor = self.conn.cursor()
    #         like_pattern = f"%{keyword}%"
    #         cursor.execute("""
    #             SELECT 
    #                 id, person_name, gender, birth_ad, birth_lunar,
    #                 zodiac, birth_time, phone, mobile, identity, identity_number,
    #                 address, note, activity_items, activity_amount, receipt_number, created_at
    #             FROM activity_signups
    #             WHERE activity_id = ? AND (
    #                 person_name LIKE ? OR 
    #                 phone LIKE ? OR 
    #                 mobile LIKE ? OR
    #                 address LIKE ?
    #             )
    #             ORDER BY created_at DESC
    #         """, (activity_id, like_pattern, like_pattern, like_pattern, like_pattern))
            
    #         return [dict(row) for row in cursor.fetchall()]
    #     except Exception as e:
    #         print(f"❌ 搜尋報名人員時出錯：{e}")
    #         return []

    def search_people(self, keyword):
        """搜尋人員資料（從 people 表）"""
        try:
            cursor = self.conn.cursor()
            like_pattern = f"%{keyword}%"
            cursor.execute("""
                SELECT 
                    id, name, gender, birthday_ad, birthday_lunar, birth_time,
                    age, zodiac, phone_home, phone_mobile, email,
                    address, zip_code, identity, note, joined_at
                FROM people
                WHERE name LIKE ? OR phone_home LIKE ? OR phone_mobile LIKE ? OR address LIKE ?
                ORDER BY name
            """, (like_pattern, like_pattern, like_pattern, like_pattern))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"❌ 搜尋人員資料時出錯：{e}")
            return []

    # def delete_activity_signup(self, signup_id):
    #     """刪除特定報名人員資料"""
    #     try:
    #         cursor = self.conn.cursor()
    #         cursor.execute("DELETE FROM activity_signups WHERE id = ?", (signup_id,))
    #         self.conn.commit()
    #         return cursor.rowcount > 0
    #     except Exception as e:
    #         print(f"❌ 刪除報名人員時出錯：{e}")
    #         return False

    # def get_activity_signup_by_id(self, signup_id):
    #     """根據ID取得特定報名人員資料"""
    #     try:
    #         cursor = self.conn.cursor()
    #         cursor.execute("""
    #             SELECT 
    #                 id, activity_id, person_name, gender, birth_ad, birth_lunar,
    #                 zodiac, birth_time, phone, mobile, identity, identity_number,
    #                 address, note, activity_items, activity_amount, receipt_number, created_at
    #             FROM activity_signups
    #             WHERE id = ?
    #         """, (signup_id,))
            
    #         result = cursor.fetchone()
    #         return dict(result) if result else None
    #     except Exception as e:
    #         print(f"❌ 取得報名人員資料時出錯：{e}")
    #         return None

    


    # -------------------------
    # Activities
    # -------------------------
    def _activity_id_exists(self, activity_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM activities WHERE id = ? LIMIT 1", (activity_id,))
        return cursor.fetchone() is not None


    # def create_activity(self, data: dict) -> str:
    #     """
    #     data:
    #       name, activity_date, location?, note?, is_active?
    #     """
    #     activity_id = self._uuid()
    #     now = self._now()
    #     cursor = self.conn.cursor()
    #     cursor.execute("""
    #         INSERT INTO activities (
    #             id, name, activity_date, location, note, is_active, created_at, updated_at
    #         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    #     """, (
    #         activity_id,
    #         data.get("name"),
    #         data.get("activity_date"),
    #         data.get("location"),
    #         data.get("note"),
    #         int(data.get("is_active", 1)),
    #         now,
    #         now
    #     ))
    #     self.conn.commit()
    #     return activity_id

    def update_activity(self, activity_id: str, data: dict):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE activities
            SET
                name = ?,
                activity_start_date = ?,
                activity_end_date = ?,
                note = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get("name"),
            data.get("activity_start_date"),
            data.get("activity_end_date"),
            data.get("note", ""),
            int(data.get("status", 1)),
            activity_id
        ))

        conn.commit()
        conn.close()

    def get_activity_delete_stats(self, activity_id: str) -> dict:
        """
        回傳刪除前的統計資訊：方案數 / 報名數
        """
        cur = self.conn.cursor()

        cur.execute("SELECT COUNT(*) FROM activity_plans WHERE activity_id = ?", (activity_id,))
        plan_cnt = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM activity_signups WHERE activity_id = ?", (activity_id,))
        signup_cnt = int(cur.fetchone()[0] or 0)

        return {"plan_cnt": plan_cnt, "signup_cnt": signup_cnt}


    def delete_activity(self, activity_id: str) -> bool:
        """
        刪除活動（含關聯資料）：
        1) activity_signup_plans（明細）
        2) activity_signups（主檔）
        3) activity_plans
        4) activities
        用交易包起來，避免刪到一半。
        """
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN;")

            # 1) 刪報名明細（透過 signup_id）
            cur.execute("""
                DELETE FROM activity_signup_plans
                WHERE signup_id IN (
                    SELECT id FROM activity_signups WHERE activity_id = ?
                )
            """, (activity_id,))

            # 2) 刪報名主檔
            cur.execute("DELETE FROM activity_signups WHERE activity_id = ?", (activity_id,))

            # 3) 刪方案
            cur.execute("DELETE FROM activity_plans WHERE activity_id = ?", (activity_id,))

            # 4) 刪活動
            cur.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            deleted = cur.rowcount > 0

            cur.execute("COMMIT;")
            return deleted

        except Exception:
            cur.execute("ROLLBACK;")
            raise

    def get_all_activities(self, active_only: bool = False):
        """
        回傳給 UI：list[dict]
        dict keys: id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
        """
        cursor = self.conn.cursor()

        if active_only:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE status = 1
                ORDER BY activity_start_date DESC, created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                ORDER BY activity_start_date DESC, created_at DESC
            """)

        return [dict(row) for row in cursor.fetchall()]


    def search_activities(self, keyword: str, active_only: bool = False):
        """
        keyword 搜尋：活動名稱 / 起日 / 迄日
        """
        cursor = self.conn.cursor()
        like = f"%{(keyword or '').strip()}%"

        if active_only:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE status = 1
                  AND (name LIKE ? OR activity_start_date LIKE ? OR activity_end_date LIKE ?)
                ORDER BY activity_start_date DESC, created_at DESC
            """, (like, like, like))
        else:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE name LIKE ? OR activity_start_date LIKE ? OR activity_end_date LIKE ?
                ORDER BY activity_start_date DESC, created_at DESC
            """, (like, like, like))

        return [dict(row) for row in cursor.fetchall()]

    def get_activity_by_id(self, activity_id: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
            FROM activities
            WHERE id = ?
        """, (activity_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # -------------------------
    # Activity Plans
    # -------------------------
    def get_activity_plans(self, activity_id: str, active_only: bool = True):
        cursor = self.conn.cursor()

        where = "WHERE activity_id = ?"
        params = [activity_id]
        if active_only:
            where += " AND is_active = 1"

        cursor.execute(f"""
            SELECT *
            FROM activity_plans
            {where}
            ORDER BY sort_order ASC, created_at ASC
        """, params)

        rows = [dict(row) for row in cursor.fetchall()]

        # 轉成 UI 期待的 keys：items / fee_type / amount
        result = []
        for r in rows:
            price_type = (r.get("price_type") or "").upper()

            if price_type == "FIXED":
                fee_type = "fixed"
                amount = r.get("fixed_price")
            elif price_type == "FREE":
                fee_type = "donation"   # 你的 UI 裡 donation 代表「報名時自由填」
                amount = None
            else:
                fee_type = "other"
                amount = None

            result.append({
                "id": r.get("id"),
                "activity_id": r.get("activity_id"),
                "name": r.get("name"),
                # DB 若是 description，就映射成 items 給 UI 用
                "items": r.get("description") if r.get("description") is not None else r.get("items", ""),
                "fee_type": fee_type,
                "amount": amount,
            })

        return result


    def create_activity_plan(
        self,
        activity_id: str,
        name: str,
        items: str,
        fee_type: str,
        amount: int | None,
        note: str = ""
    ) -> str:

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # ---- 1. 產生 plan_id（activity_id + 4位數字，含防撞）----
        plan_id = None
        for _ in range(20):  # 最多嘗試 20 次，理論上 1 次就會過
            candidate = new_plan_id(activity_id)
            cursor.execute(
                "SELECT 1 FROM activity_plans WHERE id = ? LIMIT 1",
                (candidate,)
            )
            if cursor.fetchone() is None:
                plan_id = candidate
                break

        if plan_id is None:
            conn.close()
            raise RuntimeError("無法產生唯一的方案 ID")

        # ---- 2. fee_type → DB schema mapping ----
        if fee_type == "fixed":
            price_type = "FIXED"
            fixed_price = int(amount or 0)
            suggested_price = None
            min_price = None
        else:
            # donation / other
            price_type = "FREE"
            fixed_price = None
            suggested_price = 0
            min_price = 0

        # ---- 3. 寫入 DB ----
        cursor.execute("""
            INSERT INTO activity_plans
            (id, activity_id, name, items,
             price_type, fixed_price, suggested_price, min_price,
             note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            activity_id,
            name,
            items,
            price_type,
            fixed_price,
            suggested_price,
            min_price,
            note
        ))

        conn.commit()
        conn.close()
        return plan_id

    def update_activity_plan(self, plan_id: str, plan: dict) -> bool:
        """
        Update a plan.

        Supports TWO payload shapes:
        1) UI payload (PlanEditDialog): {name, items, fee_type, amount, note}
        2) DB payload (advanced): keys like {name, description/items, price_type, fixed_price, ...}
        """
        cols = self._table_columns("activity_plans")

        # --- normalize payload ---
        if "fee_type" in (plan or {}):
            # UI payload
            name = (plan.get("name") or "").strip()
            items = (plan.get("items") or "").strip()
            fee_type = (plan.get("fee_type") or "fixed")
            amount = plan.get("amount", None)
            note = plan.get("note") or ""

            if fee_type == "fixed":
                price_type = "FIXED"
                fixed_price = int(amount or 0)
                suggested_price = None
                min_price = None
            else:
                price_type = "FREE"
                fixed_price = None
                suggested_price = 0
                min_price = 0

            payload = {
                "name": name,
                "items": items,
                "description": items,
                "price_type": price_type,
                "fixed_price": fixed_price,
                "suggested_price": suggested_price,
                "min_price": min_price,
                "note": note,
            }
        else:
            payload = dict(plan or {})

        # --- build SQL dynamically based on actual columns ---
        set_parts = []
        params = []

        def set_if(col, key=None, default=None):
            if col in cols:
                set_parts.append(f"{col} = ?")
                params.append(payload.get(key or col, default))

        set_if("name", "name", "")

        # items/description: support either schema
        if "items" in cols:
            set_if("items", "items", "")
        elif "description" in cols:
            set_if("description", "description", "")

        set_if("price_type", "price_type", "FREE")
        set_if("fixed_price", "fixed_price", None)
        set_if("suggested_price", "suggested_price", 0)
        set_if("min_price", "min_price", 0)
        set_if("note", "note", "")

        # optional columns
        set_if("allow_qty", "allow_qty", 1)
        set_if("sort_order", "sort_order", 0)
        set_if("is_active", "is_active", 1)

        if "updated_at" in cols:
            set_parts.append("updated_at = CURRENT_TIMESTAMP")

        if not set_parts:
            raise RuntimeError("activity_plans schema has no updatable columns")

        sql = f"UPDATE activity_plans SET {', '.join(set_parts)} WHERE id = ?"
        params.append(plan_id)

        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur.rowcount > 0

    def delete_activity_plan(self, plan_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM activity_plans WHERE id = ?", (plan_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def _table_columns(self, table: str) -> set[str]:
        """Return a set of column names for a sqlite table."""
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}
    
    def get_activity_plan_by_id(self, plan_id: str):
        """Get a single plan and map it into UI-friendly keys."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM activity_plans WHERE id = ? LIMIT 1", (plan_id,))
        row = cur.fetchone()
        if not row:
            return None
        r = dict(row)

        price_type = (r.get("price_type") or "").upper()
        if price_type == "FIXED":
            fee_type = "fixed"
            amount = r.get("fixed_price")
        else:
            fee_type = "donation"
            amount = None

        items = r.get("items")
        if items is None:
            items = r.get("description")
        if items is None:
            items = ""

        return {
            "id": r.get("id"),
            "activity_id": r.get("activity_id"),
            "name": r.get("name") or "",
            "items": items or "",
            "fee_type": fee_type,
            "amount": amount,
            "note": r.get("note") or "",
            "_raw": r,
        }


    # -------------------------
    # Signups (核心)
    # -------------------------
    def create_activity_signup(self, activity_id: str, person_id: str, selected_plans: list, note: str = None) -> str:
        """
        selected_plans: list of dict
          {
            "plan_id": "...",
            "qty": 1,
            "amount_override": 600  # FREE 用（整行總額），FIXED 通常 None
          }

        規則：
          - FIXED: line_total = qty * fixed_price
          - FREE : amount_override 必填，且 >= min_price
        """
        signup_id = self._uuid()
        now = self._now()
        cursor = self.conn.cursor()

        try:
            cursor.execute("BEGIN;")

            # 1) insert signup 主檔（total_amount 先 0）
            cursor.execute("""
                INSERT INTO activity_signups (
                    id, activity_id, person_id, signup_time, note, total_amount, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (signup_id, activity_id, person_id, now, note, 0, now, now))

            # 2) 逐筆寫明細 + 計算總額
            total_amount = 0

            for row in selected_plans:
                plan_id = row.get("plan_id")
                qty = int(row.get("qty", 1) or 1)
                amount_override = row.get("amount_override", None)

                # 取方案資訊（快照基礎）
                cursor.execute("""
                    SELECT price_type, fixed_price, min_price
                    FROM activity_plans
                    WHERE id = ? AND activity_id = ?
                """, (plan_id, activity_id))
                plan = cursor.fetchone()
                if not plan:
                    raise ValueError(f"找不到方案 plan_id={plan_id}")

                price_type = plan["price_type"]
                fixed_price = int(plan["fixed_price"] or 0)
                min_price = int(plan["min_price"] or 0)

                if price_type == "FIXED":
                    unit_price_snapshot = fixed_price
                    line_total = qty * unit_price_snapshot
                    amount_override_db = None
                elif price_type == "FREE":
                    if amount_override is None or str(amount_override).strip() == "":
                        raise ValueError("隨喜方案必須填寫金額")
                    amt = int(float(amount_override))
                    if amt < min_price:
                        raise ValueError(f"隨喜金額不得低於最低金額 {min_price}")
                    unit_price_snapshot = 0
                    line_total = amt
                    amount_override_db = amt
                    # 一般隨喜不太需要 qty；但如果你 UI 允許 qty，就以你輸入為準
                else:
                    raise ValueError(f"未知 price_type: {price_type}")

                item_id = self._uuid()
                cursor.execute("""
                    INSERT INTO activity_signup_plans (
                        id, signup_id, plan_id,
                        qty, unit_price_snapshot, amount_override, line_total, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id, signup_id, plan_id,
                    qty, unit_price_snapshot, amount_override_db, line_total, None
                ))

                total_amount += int(line_total)

            # 3) 回填總金額
            cursor.execute("""
                UPDATE activity_signups
                SET total_amount = ?, updated_at = ?
                WHERE id = ?
            """, (total_amount, now, signup_id))

            cursor.execute("COMMIT;")
            return signup_id

        except Exception as e:
            cursor.execute("ROLLBACK;")
            raise e

    def get_activity_signups(self, activity_id: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, p.name AS person_name, p.phone_mobile AS person_phone
            FROM activity_signups s
            JOIN people p ON p.id = s.person_id
            WHERE s.activity_id = ?
            ORDER BY s.signup_time DESC
        """, (activity_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_activity_signup_detail(self, signup_id: str):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT s.*, p.name AS person_name
            FROM activity_signups s
            JOIN people p ON p.id = s.person_id
            WHERE s.id = ?
            LIMIT 1
        """, (signup_id,))
        signup = cursor.fetchone()
        if not signup:
            return None, []

        cursor.execute("""
            SELECT sp.*, ap.name AS plan_name, ap.price_type
            FROM activity_signup_plans sp
            JOIN activity_plans ap ON ap.id = sp.plan_id
            WHERE sp.signup_id = ?
            ORDER BY ap.sort_order ASC, sp.created_at ASC
        """, (signup_id,))
        items = [dict(row) for row in cursor.fetchall()]
        return dict(signup), items

    def delete_activity_signup(self, signup_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM activity_signups WHERE id = ?", (signup_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def insert_activity_new(self, data: dict) -> str:
        """
        schema: activities
        data: {name, activity_start_date, activity_end_date, note, status}
        return: new activity_id (YYYYMMDDHHMMSS)
        """
        activity_id = generate_activity_id_safe(self._activity_id_exists)
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO activities (
                id, name, activity_start_date, activity_end_date,
                note, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            activity_id,
            data.get("name"),
            data.get("activity_start_date"),
            data.get("activity_end_date"),
            data.get("note"),
            int(data.get("status", 1)),
        ))
        self.conn.commit()
        return activity_id




