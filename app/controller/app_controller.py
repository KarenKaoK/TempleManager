# app/controller/app_controller.py
import uuid
import locale
import sqlite3
from app.config import DB_NAME
from datetime import datetime
from typing import Optional
from app.utils.id_utils import generate_activity_id_safe, new_plan_id


class AppController:
    def __init__(self, db_path=DB_NAME):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def _uuid(self) -> str:
        return str(uuid.uuid4())
    
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    def search_people_unified_dedup_name_birthday(self, keyword):
        """
        搜尋 people + households 戶長
        去重規則：name + birthday_ad
        優先保留 people
        """
        like_pattern = f"%{keyword}%"

        sql = """
        WITH unified AS (
            SELECT
                'person' AS type,
                CAST(id AS TEXT) AS source_id,
                name,
                birthday_ad,
                birthday_lunar,
                birth_time,
                age,
                zodiac,
                phone_home,
                phone_mobile,
                email,
                address,
                zip_code,
                identity,
                note,
                joined_at,
                1 AS priority
            FROM people
            WHERE name LIKE ? OR phone_home LIKE ? OR phone_mobile LIKE ? OR address LIKE ?

            UNION ALL

            SELECT
                'household_head' AS type,
                CAST(id AS TEXT) AS source_id,
                head_name AS name,
                head_birthday_ad AS birthday_ad,
                head_birthday_lunar AS birthday_lunar,
                head_birth_time AS birth_time,
                head_age AS age,
                head_zodiac AS zodiac,
                head_phone_home AS phone_home,
                head_phone_mobile AS phone_mobile,
                head_email AS email,
                head_address AS address,
                head_zip_code AS zip_code,
                head_identity AS identity,
                head_note AS note,
                head_joined_at AS joined_at,
                2 AS priority
            FROM households
            WHERE head_name LIKE ? OR head_phone_home LIKE ? OR head_phone_mobile LIKE ? OR head_address LIKE ?
        ),
        ranked AS (
            SELECT *,
                CASE
                    WHEN birthday_ad IS NOT NULL AND birthday_ad != ''
                    THEN name || '|' || birthday_ad
                    ELSE source_id || '|' || type
                END AS dedup_key,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        CASE
                            WHEN birthday_ad IS NOT NULL AND birthday_ad != ''
                            THEN name || '|' || birthday_ad
                            ELSE source_id || '|' || type
                        END
                    ORDER BY priority
                ) AS rn
            FROM unified
        )
        SELECT *
        FROM ranked
        WHERE rn = 1
        ORDER BY name
        LIMIT 50;
        """

        try:
            cur = self.conn.cursor()
            cur.execute(
                sql,
                (
                    like_pattern, like_pattern, like_pattern, like_pattern,
                    like_pattern, like_pattern, like_pattern, like_pattern,
                ),
            )
            rows = [dict(row) for row in cur.fetchall()]

            # 欄位補齊（UI 保證用得到）
            for r in rows:
                r.setdefault("phone_mobile", r.get("phone_mobile") or "")
                r.setdefault("phone", r.get("phone_mobile") or r.get("phone_home") or "")

            return rows

        except Exception as e:
            print(f"❌ search_people_unified_dedup_name_birthday error: {e}")
            return []


    def upsert_person(self, payload: dict) -> str:
        """
        新增或更新 people 表的一筆資料，回傳 person_id。

        使用情境：活動報名左下角「參加人員資料」
        - 若 payload 內有 id 且該 id 存在 → update
        - 否則 → insert

        注意：這裡「只處理 people 表」，不處理 household_members。
        """
        if not isinstance(payload, dict):
            raise ValueError("payload 必須是 dict")

        cur = self.conn.cursor()
        person_id = (payload.get("id") or "").strip() or None

        def _now_str():
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "id": person_id or str(uuid.uuid4()),
            "name": (payload.get("name") or "").strip(),
            "gender": (payload.get("gender") or "").strip() or None,
            "birthday_ad": (payload.get("birthday_ad") or "").strip() or None,
            "birthday_lunar": (payload.get("birthday_lunar") or "").strip() or None,
            "lunar_is_leap": int(payload.get("lunar_is_leap") or 0),
            "birth_time": (payload.get("birth_time") or "").strip() or None,
            "age": payload.get("age"),
            "zodiac": (payload.get("zodiac") or "").strip() or None,
            "phone_home": (payload.get("phone_home") or "").strip() or None,
            "phone_mobile": (payload.get("phone_mobile") or payload.get("phone") or "").strip() or None,
            "email": (payload.get("email") or "").strip() or None,
            "address": (payload.get("address") or "").strip() or None,
            "zip_code": (payload.get("zip_code") or "").strip() or None,
            "identity": (payload.get("identity") or "").strip() or None,
            "id_number": (payload.get("id_number") or "").strip() or None,
            "note": (payload.get("note") or "").strip() or None,
            "joined_at": (payload.get("joined_at") or _now_str()).strip() if payload.get("joined_at") else _now_str(),
        }

        if not data["name"]:
            raise ValueError("name 為必填")

        exists = False
        if person_id:
            cur.execute("SELECT 1 FROM people WHERE id = ? LIMIT 1", (person_id,))
            exists = cur.fetchone() is not None

        if exists:
            cur.execute(
                """
                UPDATE people SET
                    name = ?,
                    gender = ?,
                    birthday_ad = ?,
                    birthday_lunar = ?,
                    lunar_is_leap = ?,
                    birth_time = ?,
                    age = ?,
                    zodiac = ?,
                    phone_home = ?,
                    phone_mobile = ?,
                    email = ?,
                    address = ?,
                    zip_code = ?,
                    identity = ?,
                    id_number = ?,
                    note = ?,
                    joined_at = ?
                WHERE id = ?
                """,
                (
                    data["name"], data["gender"], data["birthday_ad"], data["birthday_lunar"],
                    data["lunar_is_leap"], data["birth_time"], data["age"], data["zodiac"],
                    data["phone_home"], data["phone_mobile"], data["email"], data["address"],
                    data["zip_code"], data["identity"], data["id_number"], data["note"],
                    data["joined_at"],
                    data["id"],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO people (
                    id, name, gender, birthday_ad, birthday_lunar, lunar_is_leap,
                    birth_time, age, zodiac, phone_home, phone_mobile, email,
                    address, zip_code, identity, id_number, note, joined_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["id"], data["name"], data["gender"], data["birthday_ad"], data["birthday_lunar"],
                    data["lunar_is_leap"], data["birth_time"], data["age"], data["zodiac"],
                    data["phone_home"], data["phone_mobile"], data["email"], data["address"],
                    data["zip_code"], data["identity"], data["id_number"], data["note"], data["joined_at"],
                ),
            )

        self.conn.commit()
        return data["id"]



    # -------------------------
    # Activities
    # -------------------------
    def _activity_id_exists(self, activity_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM activities WHERE id = ? LIMIT 1", (activity_id,))
        return cursor.fetchone() is not None


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

        result = []
        for r in rows:
            price_type = (r.get("price_type") or "").upper()
            fixed_price = r.get("fixed_price")
            suggested_price = r.get("suggested_price")
            min_price = r.get("min_price")

            if price_type == "FIXED":
                fee_type = "fixed"
                amount = fixed_price
            elif price_type == "FREE":
                fee_type = "donation"   # 你 UI donation 代表「報名時自由填」
                amount = None
            else:
                fee_type = "other"
                amount = None

            items = r.get("description")
            if items is None:
                items = r.get("items", "") or ""

            result.append({
                "id": r.get("id"),
                "activity_id": r.get("activity_id"),
                "name": r.get("name") or "",
                "items": items,
                "fee_type": fee_type,
                "amount": amount,

                # ✅ 右半邊會用到的額外資訊（不影響舊 UI）
                "price_type": price_type,                       # FIXED / FREE
                "fixed_price": fixed_price,                     # FIXED 用
                "suggested_price": int(suggested_price or 0),   # FREE 預設值
                "min_price": int(min_price or 0),               # FREE 驗證底線
                "allow_qty": int(r.get("allow_qty") or 1),      # 可選：若 DB 有
                "sort_order": int(r.get("sort_order") or 0),
                "is_active": int(r.get("is_active") or 1),
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

    # def get_activity_signups(self, activity_id: str):
    #     cursor = self.conn.cursor()
    #     cursor.execute("""
    #         SELECT s.*, p.name AS person_name, p.phone_mobile AS person_phone
    #         FROM activity_signups s
    #         JOIN people p ON p.id = s.person_id
    #         WHERE s.activity_id = ?
    #         ORDER BY s.signup_time DESC
    #     """, (activity_id,))
    #     return [dict(row) for row in cursor.fetchall()]

    def get_activity_signups(self, activity_id):
        sql = """
        SELECT
            s.id AS signup_id,
            p.name AS person_name,
            p.phone_mobile AS person_phone,
            p.address AS person_address,
            s.total_amount,
            GROUP_CONCAT(ap.name || '×' || sp.qty, '、') AS plan_summary,
            MAX(CASE WHEN ap.price_type = 'FREE' THEN 1 ELSE 0 END) AS is_donation
        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        JOIN activity_signup_plans sp ON sp.signup_id = s.id
        JOIN activity_plans ap ON ap.id = sp.plan_id
        WHERE s.activity_id = ?
        GROUP BY s.id
        ORDER BY s.created_at ASC
        """

        cur = self.conn.cursor()
        cur.execute(sql, (activity_id,))
        rows = cur.fetchall()

        # sqlite3 預設回傳 tuple，要轉成 dict 給 UI 用
        col_names = [desc[0] for desc in cur.description]

        result = []
        for r in rows:
            result.append(dict(zip(col_names, r)))

        return result



    # def get_activity_signup_detail(self, signup_id: str):
    #     cursor = self.conn.cursor()

    #     cursor.execute("""
    #         SELECT s.*, p.name AS person_name
    #         FROM activity_signups s
    #         JOIN people p ON p.id = s.person_id
    #         WHERE s.id = ?
    #         LIMIT 1
    #     """, (signup_id,))
    #     signup = cursor.fetchone()
    #     if not signup:
    #         return None, []

    #     cursor.execute("""
    #         SELECT sp.*, ap.name AS plan_name, ap.price_type
    #         FROM activity_signup_plans sp
    #         JOIN activity_plans ap ON ap.id = sp.plan_id
    #         WHERE sp.signup_id = ?
    #         ORDER BY ap.sort_order ASC, sp.created_at ASC
    #     """, (signup_id,))
    #     items = [dict(row) for row in cursor.fetchall()]
    #     return dict(signup), items

    def get_activity_signup_detail(self, signup_id):
        # ===== 取得人員基本資料 =====
        person_sql = """
        SELECT
            p.name,
            p.phone_mobile,
            p.address
        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        WHERE s.id = ?
        """

        cur = self.conn.cursor()
        cur.execute(person_sql, (signup_id,))
        row = cur.fetchone()

        if not row:
            return None

        col_names = [d[0] for d in cur.description]
        person = dict(zip(col_names, row))

        # ===== 取得方案明細 =====
        item_sql = """
        SELECT
            ap.name AS plan_name,
            sp.qty,
            sp.unit_price_snapshot AS unit_price,
            sp.line_total
        FROM activity_signup_plans sp
        JOIN activity_plans ap ON ap.id = sp.plan_id
        WHERE sp.signup_id = ?
        """

        cur.execute(item_sql, (signup_id,))
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]

        items = [dict(zip(col_names, r)) for r in rows]

        return {
            "person": {
                "name": person.get("name", ""),
                "phone": person.get("phone_mobile", ""),
                "address": person.get("address", ""),
            },
            "items": items
        }



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

    def _parse_dt(self, s: Optional[str]) -> Optional[datetime]:
        """
        支援 'YYYY-MM-DD' / 'YYYY-MM-DD HH:MM' / 'YYYY-MM-DD HH:MM:SS'
        解析失敗回 None
        """
        if not s:
            return None
        s = str(s).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return None

    def _format_date_range(self, start_s: str, end_s: str) -> str:
        start_s = (start_s or "").strip()
        end_s = (end_s or "").strip()
        if start_s and end_s:
            return f"{start_s} ~ {end_s}"
        return start_s or end_s or ""

    def _compute_activity_status_for_signup(self, start_s: str, end_s: str):
        """
        回傳 (status_text, is_open)
        is_open: True 表示允許在報名頁「被選取/報名」

        你現在先用時間推導即可：
        - 未開始：可報名 (True)  —— 如果你想「未開始不能報名」就改 False
        - 進行中：可報名 (True)
        - 已結束：不可報名 (False)
        """
        now = datetime.now()
        start_dt = self._parse_dt(start_s)
        end_dt = self._parse_dt(end_s)

        # 若日期格式不標準，保守回可報名，避免 UI 被鎖死
        if not start_dt or not end_dt:
            return ("可報名", True)

        if now < start_dt:
            return ("未開始", True)
        if now > end_dt:
            return ("已結束", False)
        return ("可報名", True)

    def list_activities_for_signup(self, active_only: bool = True) -> list[dict]:
        """
        給 ActivitySignupPage 上方活動卡片用。

        回傳格式（UI 會用到）：
        - id / code / title(name) / date_range
        - status_text / is_open（可用來做 tag 顏色與禁用）
        """
        activities = self.get_all_activities(active_only=active_only)

        results: list[dict] = []
        for a in activities:
            start_s = a.get("activity_start_date", "") or ""
            end_s = a.get("activity_end_date", "") or ""

            status_text, is_open = self._compute_activity_status_for_signup(start_s, end_s)

            results.append({
                "id": a.get("id"),
                "code": a.get("id"),  # 目前你活動編號就用 id 顯示
                "name": a.get("name") or "",
                "title": a.get("name") or "",
                "date_range": self._format_date_range(start_s, end_s),
                "status_text": status_text,
                "is_open": bool(is_open),
            })

        return results




