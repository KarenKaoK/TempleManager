# app/controller/app_controller.py
import uuid
import locale
import sqlite3
from typing import Tuple, Optional,  List, Dict, Any

from datetime import datetime


from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout, QMessageBox
from app.utils.id_utils import generate_activity_id_safe, new_plan_id
from app.config import DB_NAME



class AppController:
    def __init__(self, db_path=DB_NAME):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    # -------------------------
    # Helpers 
    # -------------------------
    def _uuid(self) -> str:
        return str(uuid.uuid4())
    
    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    # -------------------------
    # Identity 
    # -------------------------
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


    # -------------------------
    # Household / Person
    # -------------------------


    def create_household(self, person_payload: dict) -> Tuple[str, str]:
        """
        建立新戶籍 + 新增戶長 (people: role=HEAD)
        return: (person_id, household_id)
        """

        # 1) 先做必填檢查
        required_fields = {
            "name": "必須填寫姓名",
            "gender": "必須填寫性別",
            "phone_mobile": "必須填寫手機號碼",
            "birthday_ad": "必須填寫國曆生日",
            "birthday_lunar": "必須填寫農曆生日",
            "birth_time": "必須填寫出生時辰",
            "address": "必須填寫地址",
        }

        cleaned_required = {}
        missing = []

        for field, err_msg in required_fields.items():
            v = person_payload.get(field, None)

            if isinstance(v, str):
                v = v.strip()

            if v is None or v == "":
                missing.append(err_msg)
            else:
                cleaned_required[field] = v

        if missing:
            raise ValueError(" / ".join(missing))

        # 2) 檢查通過後，才開始組資料（填寫輸入）
        person_id = self._uuid()
        household_id = self._uuid()

        data = {
            "id": person_id,
            "household_id": household_id,
            "role_in_household": "HEAD",
            "status": "ACTIVE",
            "name": cleaned_required["name"],
            "gender": cleaned_required["gender"],
            "birthday_ad": cleaned_required["birthday_ad"],
            "birthday_lunar": cleaned_required["birthday_lunar"],
            "birth_time": cleaned_required["birth_time"],
            "phone_mobile": cleaned_required["phone_mobile"],
            "address": cleaned_required["address"],
            "joined_at": self._now(),
        }

        # 選填欄位：payload 有帶、且不是空字串/None 才寫入
        optional_cols = {"phone_home", "zip_code", "note"}
        for col in optional_cols:
            v = person_payload.get(col, None)
            if isinstance(v, str):
                v = v.strip()
            if v not in (None, ""):
                data[col] = v

        # 3) 寫入 DB
        cur = self.conn.cursor()
        keys = list(data.keys())
        cur.execute(
            f"INSERT INTO people ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            tuple(data[k] for k in keys),
        )
        self.conn.commit()
        return person_id, household_id

    def create_people(self, household_id: str, person_payload: dict) -> str:
        """
        在指定戶長底下新增成員 (people: role=MEMBER)
        return: person_id
        """

        household_id = (household_id or "").strip()
        if not household_id:
            raise ValueError("household_id is required")

        cur = self.conn.cursor()

        # 0) 先確認戶長存在，且是 HEAD，並取 household_id
        row = cur.execute(
            """
            SELECT household_id
            FROM people
            WHERE id = ?
            AND role_in_household = 'HEAD'
            AND status = 'ACTIVE'
            """,
            (household_id,),
        ).fetchone()

        if not row:
            raise ValueError("head person not found or not ACTIVE HEAD")

        household_id = row[0]

        # 1) 先做必填檢查（跟 create_household 一樣的欄位）
        required_fields = {
            "name": "name is required",
            "gender": "gender is required",
            "phone_mobile": "phone_mobile is required",
            "birthday_ad": "birthday_ad is required",
            "birthday_lunar": "birthday_lunar is required",
            "birth_time": "birth_time is required",
            "address": "address is required",
        }

        cleaned_required = {}
        missing = []

        for field, err_msg in required_fields.items():
            v = person_payload.get(field, None)
            if isinstance(v, str):
                v = v.strip()

            if v is None or v == "":
                missing.append(err_msg)
            else:
                cleaned_required[field] = v

        if missing:
            raise ValueError(" / ".join(missing))

        # 2) 檢查通過後，才開始組資料
        person_id = self._uuid()

        data = {
            "id": person_id,
            "household_id": household_id,
            "role_in_household": "MEMBER",
            "status": "ACTIVE",

            "name": cleaned_required["name"],
            "gender": cleaned_required["gender"],
            "birthday_ad": cleaned_required["birthday_ad"],
            "birthday_lunar": cleaned_required["birthday_lunar"],
            "birth_time": cleaned_required["birth_time"],

            "phone_mobile": cleaned_required["phone_mobile"],
            "address": cleaned_required["address"],

            "joined_at": self._now(),
        }

        # 3) 選填欄位：payload 有帶、且不是空字串/None 才寫入
        optional_cols = {
            "phone_home",
            "zip_code",
            "note",
            "lunar_is_leap",
            "age",
            "zodiac",
        }
        for col in optional_cols:
            v = person_payload.get(col, None)
            if isinstance(v, str):
                v = v.strip()
            if v not in (None, ""):
                data[col] = v

        # 4) 寫入 DB
        keys = list(data.keys())
        cur.execute(
            f"INSERT INTO people ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            tuple(data[k] for k in keys),
        )
        self.conn.commit()

        return person_id



    def list_household(
        self,
        keyword: Optional[str] = None,
        status: str = "ACTIVE",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        列出戶籍清單（以戶長 HEAD 為代表）
        Phase 1（方案 B）：
        - 回傳「戶長完整資訊」供 household_table 12 欄顯示
        - keyword：戶長姓名 / 手機
        - status 篩選、limit/offset 分頁
        """

        kw = (keyword or "").strip()
        status = (status or "").strip().upper()

        params = []
        where = ["p.role_in_household = 'HEAD'"]

        if status and status != "ALL":
            where.append("p.status = ?")
            params.append(status)

        if kw:
            where.append("(p.name LIKE ? OR p.phone_mobile LIKE ?)")
            like_kw = f"%{kw}%"
            params.extend([like_kw, like_kw])

        where_sql = " AND ".join(where)

        sql = f"""
        SELECT
            p.household_id,
            p.id AS head_person_id,

            -- 戶長完整欄位
            p.name,
            p.gender,
            p.birthday_ad,
            p.birthday_lunar,
            p.lunar_is_leap,
            p.birth_time,
            p.zodiac,
            p.age,
            p.phone_home,
            p.phone_mobile,
            p.address,
            p.note

        FROM people p
        WHERE {where_sql}
        ORDER BY p.joined_at ASC
        LIMIT ? OFFSET ?;
        """

        params.extend([int(limit), int(offset)])

        cur = self.conn.cursor()
        rows = cur.execute(sql, tuple(params)).fetchall()

        result = []
        for r in rows:
            result.append({
                "household_id": r[0],

                # 兼容：兩個 key 都給，避免其他舊 code 還在用 head_person_id
                "id": r[1],
                "head_person_id": r[1],

                "name": r[2],
                "gender": r[3],
                "birthday_ad": r[4],
                "birthday_lunar": r[5],
                "lunar_is_leap": r[6],
                "birth_time": r[7],
                "zodiac": r[8],
                "age": r[9],
                "phone_home": r[10],
                "phone_mobile": r[11],
                "address": r[12],
                "note": r[13],
            })

        return result


    def list_people_by_household(self, household_id: str, status: str = "ACTIVE") -> List[Dict]:
        """
        列出指定 household_id 底下的所有 people（含 HEAD / MEMBER）
        預設只列 ACTIVE，可用 status='ALL' 取消篩選
        回傳：List[dict]
        """

        household_id = (household_id or "").strip()
        if not household_id:
            raise ValueError("household_id is required")

        status = (status or "").strip().upper()

        params = [household_id]
        where = ["household_id = ?"]

        if status and status != "ALL":
            where.append("status = ?")
            params.append(status)

        where_sql = " AND ".join(where)

        sql = f"""
        SELECT
            id,
            household_id,
            role_in_household,
            status,
            name,
            gender,
            birthday_ad,
            birthday_lunar,
            lunar_is_leap,
            birth_time,
            age,
            zodiac,
            phone_home,
            phone_mobile,
            address,
            zip_code,
            note,
            joined_at
        FROM people
        WHERE {where_sql}
        ORDER BY
            CASE role_in_household
                WHEN 'HEAD' THEN 0
                ELSE 1
            END,
            joined_at ASC;
        """

        cur = self.conn.cursor()
        rows = cur.execute(sql, tuple(params)).fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "household_id": r[1],
                "role_in_household": r[2],
                "status": r[3],
                "name": r[4],
                "gender": r[5],
                "birthday_ad": r[6],
                "birthday_lunar": r[7],
                "lunar_is_leap": r[8],
                "birth_time": r[9],
                "age": r[10],
                "zodiac": r[11],
                "phone_home": r[12],
                "phone_mobile": r[13],
                "address": r[14],
                "zip_code": r[15],
                "note": r[16],
                "joined_at": r[17],
            })

        return result

    def update_person(self, person_id: str, payload: Dict[str, Any]) -> int:

        """
        更新 people 表某一筆 person 資料（白名單欄位）
        - 只允許更新 UPDATABLE_FIELDS 內的欄位
        - 會自動 strip 字串
        - 若 payload 沒有任何可更新欄位 -> raise
        return: 影響筆數 rowcount（正常應為 1）
        """

        UPDATABLE_FIELDS = {
            "name",
            "gender",
            "birthday_ad",
            "birthday_lunar",
            "lunar_is_leap",
            "birth_time",
            "phone_home",
            "phone_mobile",
            "address",
            "zip_code",
            "note",
        }
        person_id = (person_id or "").strip()
        if not person_id:
            raise ValueError("person_id is required")

        if payload is None or not isinstance(payload, dict):
            raise ValueError("payload must be a dict")

        # 1) 過濾出允許更新的欄位
        updates: Dict[str, Any] = {}
        for k, v in payload.items():
            if k not in UPDATABLE_FIELDS:
                continue

            # 統一處理字串
            if isinstance(v, str):
                v = v.strip()

            # 你也可以選擇：不允許把欄位更新成空字串
            if v == "":
                continue

            # lunar_is_leap 建議確保是 0/1（但不強制也可）
            if k == "lunar_is_leap" and v not in (None, ""):
                try:
                    v = int(v)
                except Exception:
                    raise ValueError("lunar_is_leap must be 0 or 1")
                if v not in (0, 1):
                    raise ValueError("lunar_is_leap must be 0 or 1")

            updates[k] = v

        if not updates:
            raise ValueError("no updatable fields in payload")

        # 2) 先確認 person 存在（避免 rowcount=0 你不好判斷）
        cur = self.conn.cursor()
        exists = cur.execute("SELECT 1 FROM people WHERE id = ?", (person_id,)).fetchone()
        if not exists:
            raise ValueError("person not found")

        # 3) 組 SQL
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        sql = f"UPDATE people SET {set_clause} WHERE id = ?"

        params = list(updates.values()) + [person_id]
        cur.execute(sql, tuple(params))
        self.conn.commit()

        return cur.rowcount

    def split_member_to_new_household(
        self,
        member_person_id: str,
        *,
        require_active: bool = True,
    ) -> str:
        """
        分戶：把一位 MEMBER 移到新 household，並升為新戶的 HEAD

        - 只允許 MEMBER 分戶（HEAD 不在這支處理）
        - 會產生新的 household_id
        - 會把此人的 role_in_household 改為 'HEAD'
        - 會把此人的 household_id 更新為新的 household_id
        return: new_household_id
        """

        member_person_id = (member_person_id or "").strip()
        if not member_person_id:
            raise ValueError("member_person_id is required")

        cur = self.conn.cursor()

        # 1) 先抓出該人目前狀態
        row = cur.execute(
            """
            SELECT id, household_id, role_in_household, status
            FROM people
            WHERE id = ?
            """,
            (member_person_id,),
        ).fetchone()

        if not row:
            raise ValueError("person not found")

        _id, old_household_id, role, status = row

        if role != "MEMBER":
            raise ValueError("only MEMBER can be split to a new household")

        if require_active and status != "ACTIVE":
            raise ValueError("only ACTIVE person can be split")

        # 2) 確認原 household 的 HEAD 存在（避免資料已壞）
        head = cur.execute(
            """
            SELECT 1
            FROM people
            WHERE household_id = ?
            AND role_in_household = 'HEAD'
            LIMIT 1
            """,
            (old_household_id,),
        ).fetchone()

        if not head:
            raise ValueError("source household has no HEAD (data integrity issue)")

        new_household_id = self._uuid()

        # 3) 交易：更新該 member -> 新戶 + HEAD
        try:
            cur.execute("BEGIN")

            # 把此人搬到新 household，並升為 HEAD
            # （partial unique index 會確保新 household 只有一位 HEAD）
            cur.execute(
                """
                UPDATE people
                SET household_id = ?,
                    role_in_household = 'HEAD'
                WHERE id = ?
                AND role_in_household = 'MEMBER'
                """,
                (new_household_id, member_person_id),
            )

            if cur.rowcount != 1:
                raise ValueError("split failed (person role changed concurrently?)")

            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        return new_household_id

    def list_active_heads(self, *, exclude_household_id: Optional[str] = None) -> List[Dict]:
        """
        列出所有 ACTIVE 戶長（HEAD），給 UI 下拉選單用
        - exclude_household_id: 可排除某一戶（避免選到同戶）
        """
        exclude_household_id = (exclude_household_id or "").strip()

        params = []
        where = [
            "role_in_household = 'HEAD'",
            "status = 'ACTIVE'",
        ]
        if exclude_household_id:
            where.append("household_id != ?")
            params.append(exclude_household_id)

        where_sql = " AND ".join(where)

        sql = f"""
        SELECT
            id AS head_person_id,
            household_id,
            name,
            phone_mobile
        FROM people
        WHERE {where_sql}
        ORDER BY joined_at ASC;
        """

        cur = self.conn.cursor()
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def transfer_member_to_head(
        self,
        member_person_id: str,
        target_head_person_id: str,
        *,
        require_active: bool = True,
    ) -> str:
        """
        戶籍變更：把 member 搬到 target_head 的 household
        - member 必須是 MEMBER（不能拿 HEAD 去搬）
        - target 必須是 ACTIVE HEAD
        - return: target_household_id（方便 UI 切換）
        """
        member_person_id = (member_person_id or "").strip()
        target_head_person_id = (target_head_person_id or "").strip()

        if not member_person_id:
            raise ValueError("member_person_id is required")
        if not target_head_person_id:
            raise ValueError("target_head_person_id is required")

        cur = self.conn.cursor()

        # 1) member 檢查
        m = cur.execute(
            """
            SELECT id, household_id, role_in_household, status, name
            FROM people
            WHERE id = ?
            """,
            (member_person_id,),
        ).fetchone()
        if not m:
            raise ValueError("member not found")

        if m["role_in_household"] != "MEMBER":
            raise ValueError("only MEMBER can be transferred")

        if require_active and m["status"] != "ACTIVE":
            raise ValueError("only ACTIVE member can be transferred")

        source_household_id = m["household_id"]

        # 2) target head 檢查 + 取 household_id
        t = cur.execute(
            """
            SELECT id AS head_person_id, household_id, status, name
            FROM people
            WHERE id = ?
            AND role_in_household = 'HEAD'
            """,
            (target_head_person_id,),
        ).fetchone()
        if not t:
            raise ValueError("target head not found")

        if require_active and t["status"] != "ACTIVE":
            raise ValueError("target head is not ACTIVE")

        target_household_id = t["household_id"]

        if target_household_id == source_household_id:
            raise ValueError("member already belongs to this household")

        # 3) 交易更新
        try:
            cur.execute("BEGIN")
            cur.execute(
                """
                UPDATE people
                SET household_id = ?
                WHERE id = ?
                AND role_in_household = 'MEMBER'
                """,
                (target_household_id, member_person_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("transfer failed")
            self.conn.commit()
            return target_household_id
        except Exception:
            self.conn.rollback()
            raise

    def deactivate_person(self, person_id: str, *, allow_head: bool = False) -> int:
        """
        停用一個人（status -> INACTIVE）
        - 預設不允許停用 HEAD（避免一戶沒戶長）
        - return: 影響筆數 rowcount（正常 1）
        """

        person_id = (person_id or "").strip()
        if not person_id:
            raise ValueError("person_id is required")

        cur = self.conn.cursor()

        # 1) 先確認存在並取得角色/狀態/household
        row = cur.execute(
            """
            SELECT role_in_household, status, household_id
            FROM people
            WHERE id = ?
            """,
            (person_id,),
        ).fetchone()

        if not row:
            raise ValueError("person not found")

        role, status, household_id = row

        # 2) 若已停用，直接回傳 0（你也可以選擇回傳 1 視為 idempotent）
        if status == "INACTIVE":
            return 0

        # 3) 安全：預設不允許停用戶長
        if role == "HEAD" and not allow_head:
            raise ValueError("cannot deactivate HEAD (use change_head / dissolve household flow)")

        # 4) 更新狀態
        cur.execute(
            """
            UPDATE people
            SET status = 'INACTIVE'
            WHERE id = ?
            AND status = 'ACTIVE'
            """,
            (person_id,),
        )
        self.conn.commit()
        return cur.rowcount

    def deactivate_household_head_if_no_members(
        self,
        household_id: str,
        head_person_id: str,
        *,
        require_active: bool = True,
    ) -> int:
        """
        刪除戶籍（= 停用戶長）：
        1) 檢查該 household 底下是否還有 ACTIVE MEMBER
        2) 沒有才允許把 HEAD 設為 INACTIVE

        return: rowcount（正常 1；已是 INACTIVE 可能 0）
        """
        household_id = (household_id or "").strip()
        head_person_id = (head_person_id or "").strip()
        if not household_id:
            raise ValueError("household_id is required")
        if not head_person_id:
            raise ValueError("head_person_id is required")

        cur = self.conn.cursor()

        # 0) 確認戶長存在且屬於該 household
        head = cur.execute(
            """
            SELECT id, status
            FROM people
            WHERE id = ?
            AND household_id = ?
            AND role_in_household = 'HEAD'
            """,
            (head_person_id, household_id),
        ).fetchone()

        if not head:
            raise ValueError("head person not found in this household")

        if require_active and head["status"] != "ACTIVE":
            raise ValueError("head person is not ACTIVE")

        # 1) 檢查是否有 ACTIVE MEMBER
        cnt = cur.execute(
            """
            SELECT COUNT(1)
            FROM people
            WHERE household_id = ?
            AND role_in_household = 'MEMBER'
            AND status = 'ACTIVE'
            """,
            (household_id,),
        ).fetchone()[0]

        if int(cnt or 0) > 0:
            raise ValueError("此戶籍底下仍有會員，請先刪除/移轉/分戶所有會員後才能刪除戶長")

        # 2) 停用戶長
        cur.execute(
            """
            UPDATE people
            SET status = 'INACTIVE'
            WHERE id = ?
            AND household_id = ?
            AND role_in_household = 'HEAD'
            AND status = 'ACTIVE'
            """,
            (head_person_id, household_id),
        )
        self.conn.commit()
        return cur.rowcount

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

    def upsert_person(self, person_payload: Dict[str, Any]) -> str:
        """
        給「活動報名頁」用：
        - 若 payload 有 id：更新該 people（白名單欄位），回傳同一個 id
        - 若 payload 無 id：建立新戶籍 + 新戶長（people: HEAD），回傳新 id

        注意：
        - create_household() 有必填欄位要求（name/gender/phone_mobile/birthday_ad/birthday_lunar/birth_time/address）
        """

        if not isinstance(person_payload, dict):
            raise ValueError("person_payload must be a dict")

        # --- normalize keys (避免 UI 用 phone 而 DB 用 phone_mobile) ---
        payload = dict(person_payload)

        if (not payload.get("phone_mobile")) and payload.get("phone"):
            payload["phone_mobile"] = payload.get("phone")

        person_id = (payload.get("id") or "").strip()

        # 1) 已有人：更新後回傳 id
        if person_id:
            # update_person 會自動做白名單欄位過濾與 strip
            self.update_person(person_id, payload)
            return person_id

        # 2) 新人：直接建立新 household + HEAD
        new_person_id, _new_household_id = self.create_household(payload)
        return new_person_id



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

    
    def get_activity_signup_for_edit(self, signup_id: str):
        cur = self.conn.cursor()

        person_sql = """
        SELECT
            s.id AS signup_id,
            s.activity_id,
            s.person_id,

            p.name,
            p.gender,
            p.birthday_ad,
            p.birthday_lunar,
            p.lunar_is_leap,
            p.birth_time,
            p.age,
            p.zodiac,

            p.phone_home,
            p.phone_mobile,
            p.address,
            p.zip_code,
            p.note

        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        WHERE s.id = ?
        """
        cur.execute(person_sql, (signup_id,))
        base = cur.fetchone()
        if not base:
            return None

        cols = [d[0] for d in cur.description]
        base = dict(zip(cols, base))

        activity_id = base["activity_id"]
        items_sql = """
        SELECT
            ap.id AS plan_id,
            ap.name AS plan_name,
            ap.price_type,
            ap.fixed_price,
            ap.suggested_price,
            ap.min_price,
            ap.sort_order,

            COALESCE(sp.qty, 0) AS qty,

            -- 已報名：使用原本快照；未報名：FIXED 用 ap.fixed_price 當預設快照
            CASE
                WHEN sp.unit_price_snapshot IS NOT NULL THEN sp.unit_price_snapshot
                ELSE COALESCE(ap.fixed_price, 0)
            END AS unit_price_snapshot,

            COALESCE(sp.amount_override, 0) AS amount_override,
            COALESCE(sp.line_total, 0) AS line_total

        FROM activity_plans ap
        LEFT JOIN activity_signup_plans sp
            ON sp.plan_id = ap.id
        AND sp.signup_id = ?
        WHERE ap.activity_id = ?
        AND ap.is_active = 1
        ORDER BY ap.sort_order ASC, ap.created_at ASC
        """
        cur.execute(items_sql, (signup_id, activity_id))
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
        items = [dict(zip(col_names, r)) for r in rows]

        return {
            "signup_id": base["signup_id"],
            "activity_id": base["activity_id"],
            "person_id": base.get("person_id", ""),
            "person": {
                "name": base.get("name", "") or "",
                "gender": base.get("gender", "") or "",
                "birthday_ad": base.get("birthday_ad", "") or "",
                "birthday_lunar": base.get("birthday_lunar", "") or "",
                "lunar_is_leap": int(base.get("lunar_is_leap") or 0),
                "birth_time": base.get("birth_time", "") or "",
                "age": base.get("age", "") or "",
                "zodiac": base.get("zodiac", "") or "",
                "phone_mobile": base.get("phone_mobile", "") or "",
                "phone_home": base.get("phone_home", "") or "",
                "email": base.get("email", "") or "",
                "address": base.get("address", "") or "",
                "zip_code": base.get("zip_code", "") or "",
                "identity": base.get("identity", "") or "",
                "id_number": base.get("id_number", "") or "",
                "note": base.get("note", "") or "",
            },
            "items": items
        }


    def update_activity_signup_quantities(self, signup_id: str, qty_by_plan_id: dict) -> bool:
        """
        qty_by_plan_id: {plan_id: new_qty}
        - FIXED: line_total = qty * unit_price_snapshot
        - FREE : 維持 line_total（隨喜金額），qty 更新與否不影響總額（這裡仍可更新 qty 但不改 line_total）
        """
        cur = self.conn.cursor()
        now = self._now()

        try:
            cur.execute("BEGIN;")

            # 取目前明細（含 price_type）
            cur.execute("""
                SELECT
                    sp.plan_id, sp.qty, sp.unit_price_snapshot, sp.line_total,
                    ap.price_type
                FROM activity_signup_plans sp
                JOIN activity_plans ap ON ap.id = sp.plan_id
                WHERE sp.signup_id = ?
            """, (signup_id,))
            rows = cur.fetchall()

            if not rows:
                cur.execute("ROLLBACK;")
                return False

            total_amount = 0

            for r in rows:
                plan_id = r["plan_id"]
                price_type = r["price_type"]
                unit_price = int(r["unit_price_snapshot"] or 0)
                old_line_total = int(r["line_total"] or 0)

                new_qty = int(qty_by_plan_id.get(plan_id, r["qty"]) or 0)
                if new_qty < 0:
                    new_qty = 0

                if price_type == "FIXED":
                    new_line_total = new_qty * unit_price
                else:
                    # FREE(隨喜)：維持原本隨喜金額（line_total）
                    new_line_total = old_line_total

                cur.execute("""
                    UPDATE activity_signup_plans
                    SET qty = ?, line_total = ?
                    WHERE signup_id = ? AND plan_id = ?
                """, (new_qty, new_line_total, signup_id, plan_id))

                total_amount += int(new_line_total)

            # 回填總金額
            cur.execute("""
                UPDATE activity_signups
                SET total_amount = ?, updated_at = ?
                WHERE id = ?
            """, (total_amount, now, signup_id))

            cur.execute("COMMIT;")
            return True

        except Exception:
            cur.execute("ROLLBACK;")
            raise

    def update_activity_signup_items(self, signup_id: str, qty_by_plan_id: dict, free_amount_by_plan_id: dict) -> bool:
        """
        ✅ 支援新增/刪除：
        - FIXED: qty=0 刪除明細；qty>0 upsert；line_total = qty * unit_price_snapshot
        - FREE : qty=0 刪除明細；qty=1 upsert；line_total = amount_override（qty 固定 1）
        """
        cur = self.conn.cursor()
        now = self._now()

        try:
            cur.execute("BEGIN;")

            # 1) 取得 activity_id
            cur.execute("SELECT activity_id FROM activity_signups WHERE id = ? LIMIT 1", (signup_id,))
            r = cur.fetchone()
            if not r:
                cur.execute("ROLLBACK;")
                return False
            activity_id = r["activity_id"]

            # 2) 取該活動所有方案（含 FIXED/FREE 規則）
            cur.execute("""
                SELECT id AS plan_id, price_type, fixed_price, suggested_price, min_price
                FROM activity_plans
                WHERE activity_id = ? AND is_active = 1
            """, (activity_id,))
            plans = [dict(x) for x in cur.fetchall()]
            plan_map = {p["plan_id"]: p for p in plans}

            # 3) 取目前已報名明細（用來判斷 update vs insert vs delete）
            cur.execute("""
                SELECT id, plan_id, qty, unit_price_snapshot, amount_override, line_total
                FROM activity_signup_plans
                WHERE signup_id = ?
            """, (signup_id,))
            existing = [dict(x) for x in cur.fetchall()]
            existing_by_plan = {e["plan_id"]: e for e in existing}

            total_amount = 0

            for plan_id, plan in plan_map.items():
                price_type = (plan.get("price_type") or "").upper()
                desired_qty = int(qty_by_plan_id.get(plan_id, 0) or 0)

                ex = existing_by_plan.get(plan_id)

                # ========= qty=0 → 刪除 =========
                if desired_qty <= 0:
                    if ex:
                        cur.execute("DELETE FROM activity_signup_plans WHERE signup_id = ? AND plan_id = ?", (signup_id, plan_id))
                    continue

                # ========= qty>0 → upsert =========
                if price_type == "FIXED":
                    # 已有明細：沿用 unit_price_snapshot；新增：用目前 fixed_price 當快照
                    unit_price = int((ex.get("unit_price_snapshot") if ex else plan.get("fixed_price")) or 0)
                    line_total = desired_qty * unit_price

                    if ex:
                        cur.execute("""
                            UPDATE activity_signup_plans
                            SET qty = ?, line_total = ?, amount_override = NULL
                            WHERE signup_id = ? AND plan_id = ?
                        """, (desired_qty, line_total, signup_id, plan_id))
                    else:
                        item_id = self._uuid()
                        cur.execute("""
                            INSERT INTO activity_signup_plans
                                (id, signup_id, plan_id, qty, unit_price_snapshot, amount_override, line_total, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (item_id, signup_id, plan_id, desired_qty, unit_price, None, line_total, None))

                    total_amount += int(line_total)

                else:  # FREE
                    # FREE 只允許 0/1；這裡進來代表要報名，所以固定 qty=1
                    min_price = int(plan.get("min_price") or 0)
                    amt = free_amount_by_plan_id.get(plan_id, None)

                    if amt is None or str(amt).strip() == "":
                        # 若 UI 沒帶，嘗試用既有金額；再不行用 suggested_price
                        if ex and ex.get("amount_override") is not None:
                            amt = int(ex.get("amount_override") or 0)
                        else:
                            amt = int(plan.get("suggested_price") or 0)

                    amt = int(amt)
                    if amt < min_price:
                        raise ValueError(f"隨喜金額不得低於最低金額 {min_price}")

                    if ex:
                        cur.execute("""
                            UPDATE activity_signup_plans
                            SET qty = 1, unit_price_snapshot = 0, amount_override = ?, line_total = ?
                            WHERE signup_id = ? AND plan_id = ?
                        """, (amt, amt, signup_id, plan_id))
                    else:
                        item_id = self._uuid()
                        cur.execute("""
                            INSERT INTO activity_signup_plans
                                (id, signup_id, plan_id, qty, unit_price_snapshot, amount_override, line_total, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (item_id, signup_id, plan_id, 1, 0, amt, amt, None))

                    total_amount += int(amt)

            # 4) 回填總金額
            cur.execute("""
                UPDATE activity_signups
                SET total_amount = ?, updated_at = ?
                WHERE id = ?
            """, (total_amount, now, signup_id))

            cur.execute("COMMIT;")
            return True

        except Exception:
            cur.execute("ROLLBACK;")
            raise



    def delete_activity_signup(self, signup_id: str) -> bool:
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN;")
            cur.execute("DELETE FROM activity_signup_plans WHERE signup_id = ?", (signup_id,))
            cur.execute("DELETE FROM activity_signups WHERE id = ?", (signup_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception:
            self.conn.rollback()
            raise

    
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





    # -------------------------
    # Transactions (Income / Expense)
    # -------------------------
    def get_all_income_items(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM income_items ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_expense_items(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM expense_items ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def search_people(self, keyword):
        """
        搜尋信徒（不分戶長或成員），回傳 id, name, phone, address
        供 UI 搜尋並取得 person_id
        """
        cursor = self.conn.cursor()
        kw = f"%{keyword}%"
        cursor.execute("""
            SELECT id, name, phone_mobile, phone_home, address 
            FROM people 
            WHERE name LIKE ? OR phone_mobile LIKE ? OR phone_home LIKE ?
            LIMIT 50
        """, (kw, kw, kw))
        return [dict(row) for row in cursor.fetchall()]

    def search_people_unified_dedup_name_birthday(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        給「活動報名頁：參加人員資料 / 快速搜尋」使用
        - 來源：people 表（不分 HEAD / MEMBER）
        - 搜尋：name / phone_mobile / phone_home
        - 去重：name + birthday_ad（若 birthday_ad 空，則用 birthday_lunar）
        - 輸出欄位：讓 UI 好填表（phone_mobile 統一）
        """
        kw = (keyword or "").strip()
        if not kw:
            return []

        # 1) 先用既有方法查（避免重複寫 SQL）
        rows = self.search_people(kw)  # -> [{id,name,phone_mobile,phone_home,address,...}]

        # 2) 如果活動頁 UI 需要生日去重，那就補查生日欄位（因為 search_people 現在沒帶生日）
        #    這裡用一次性 query 把這批 id 的 birthday 撈回來，避免 UI 自己亂處理
        ids = [r.get("id") for r in rows if r.get("id")]
        if not ids:
            return []

        placeholders = ",".join(["?"] * len(ids))
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT id, birthday_ad, birthday_lunar
            FROM people
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )
        bmap = {x["id"]: dict(x) for x in cur.fetchall()}

        # 3) 去重：name + birthday（優先 birthday_ad，沒有就 birthday_lunar）
        seen = set()
        result = []
        for r in rows:
            pid = r.get("id")
            b = bmap.get(pid, {})
            birthday_key = (b.get("birthday_ad") or b.get("birthday_lunar") or "").strip()
            name_key = (r.get("name") or "").strip()
            dedup_key = (name_key, birthday_key)

            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # 4) 統一輸出欄位（活動頁最常用）
            phone_mobile = (r.get("phone_mobile") or "").strip()
            phone_home = (r.get("phone_home") or "").strip()

            result.append({
                "id": pid,
                "name": name_key,
                "phone_mobile": phone_mobile,                 # ✅ 統一活動頁用這個
                "phone_home": phone_home,
                "phone_display": phone_mobile or phone_home,  # ✅ 顯示用（可選）
                "address": (r.get("address") or "").strip(),
                "birthday_ad": (b.get("birthday_ad") or "").strip(),
                "birthday_lunar": (b.get("birthday_lunar") or "").strip(),
            })

            if len(result) >= int(limit):
                break

        return result


    def generate_receipt_number(self, date_str):
        """
        產生收據號碼：民國年 + 4碼流水號
        例如：1130001 (113年第1張)
        """
        # date_str 格式預期為 "YYYY-MM-DD"
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            roc_year = dt.year - 1911
            prefix = f"{roc_year}"
        except ValueError:
            # Fallback
            dt = datetime.now()
            roc_year = dt.year - 1911
            prefix = f"{roc_year}"
        
        cursor = self.conn.cursor()
        # 查詢該民國年開頭的最後一筆收據號碼
        # 注意：要確保只抓到符合 "prefix + 數字" 格式的
        cursor.execute("""
            SELECT receipt_number FROM transactions 
            WHERE receipt_number LIKE ? 
            ORDER BY receipt_number DESC LIMIT 1
        """, (f"{prefix}%",))
        
        row = cursor.fetchone()
        new_seq = 1
        
        if row and row[0]:
            last_no = row[0]
            # 嘗試解析後面的流水號
            # 假設格式: [ROC_YEAR][0000] (len(prefix) + 4 or more)
            if len(last_no) > len(prefix):
                try:
                    # 取出後面的數字部分
                    seq_str = last_no[len(prefix):]
                    if seq_str.isdigit():
                        new_seq = int(seq_str) + 1
                except:
                    pass
        
        # 格式化: 1130001 (4碼流水號)
        return f"{prefix}{new_seq:04d}"

    def add_transaction(self, data):
        """
        新增收支紀錄
        data: {
            "date": "2023-10-24",
            "type": "income" | "expense",
            "category_id": REQUIRED,
            "category_name": ...,
            "amount": ...,
            "payer_person_id": (Income 建議必填),
            "payer_name": ...,
            "receipt_number": ...,
            "note": ...
        }
        """
        # 簡易檢查
        if not data.get("category_id"):
            raise ValueError("category_id is required")
        if data.get("type") == "income" and not data.get("payer_person_id"):
             # 雖然 DB 允許 NULL (為了彈性)，但業務邏輯上我們盡量要求 UI 傳入
             pass 

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                date, type, category_id, category_name, amount, 
                payer_person_id, payer_name, handler, receipt_number, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("date"),
            data.get("type"),
            data.get("category_id"),
            data.get("category_name"),
            data.get("amount"),
            data.get("payer_person_id"),
            data.get("payer_name"),
            data.get("handler"),
            data.get("receipt_number"),
            data.get("note")
        ))
        self.conn.commit()
    
    def get_transactions(self, transaction_type=None, start_date=None, end_date=None, keyword=None):
        cursor = self.conn.cursor()
        query = """
            SELECT t.*, p.phone_mobile, p.address
            FROM transactions t
            LEFT JOIN people p ON t.payer_person_id = p.id
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
        """
        params = []

        if transaction_type:
            query += " AND t.type = ?"
            params.append(transaction_type)
        
        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)
        
        if keyword:
            kw = f"%{keyword}%"
            query += " AND (t.payer_name LIKE ? OR t.receipt_number LIKE ? OR t.note LIKE ?)"
            params.extend([kw, kw, kw])
            
        query += " ORDER BY t.date DESC, t.created_at DESC"
        
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def delete_transaction(self, transaction_id):
        """軟刪除"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE transactions SET is_deleted=1 WHERE id=?", (transaction_id,))
        self.conn.commit()

    def update_transaction(self, transaction_id, data):
        """更新交易紀錄"""
        cursor = self.conn.cursor()
        
        # 這裡只允許更新部分欄位，確保資料一致性
        # 注意：如果 user 修改了日期，receipt_number 是否要重算？
        # 目前策略：不重算單號，保留原單號，除非 user 自己想改(但 UI 不開放改單號)
        
        cursor.execute("""
            UPDATE transactions
            SET date=?, category_id=?, category_name=?, amount=?, 
                payer_person_id=?, payer_name=?, handler=?, note=?
            WHERE id=?
        """, (
            data.get("date"),
            data.get("category_id"),
            data.get("category_name"),
            data.get("amount"),
            data.get("payer_person_id"),
            data.get("payer_name"),
            data.get("handler"),
            data.get("note"),
            transaction_id
        ))
        self.conn.commit()
