# app/controller/app_controller.py
import uuid
import locale
import sqlite3
import json
import re
import os
from typing import Tuple, Optional,  List, Dict, Any
import app.utils.secret_store as secret_store
from cryptography.fernet import Fernet

from datetime import datetime, date, timedelta


from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout, QMessageBox
from app.utils.id_utils import generate_activity_id_safe, new_plan_id
from app.config import DB_NAME
from app.logging import log_data_change, log_system



class AppController:
    SYSTEM_INCOME_ITEMS = (
        ("90", "活動收入"),
        ("91", "點燈收入"),
    )
    SYSTEM_EXPENSE_ITEMS = (
        ("90R", "活動退費"),
        ("91R", "安燈退費"),
    )
    ACTIVITY_INCOME_ITEM_ID = "90"
    LIGHTING_INCOME_ITEM_ID = "91"
    ACTIVITY_REFUND_EXPENSE_ITEM_ID = "90R"
    LIGHTING_REFUND_EXPENSE_ITEM_ID = "91R"
    SYSTEM_LIGHTING_ITEMS = (
        ("L01", "太歲燈", 500, "TAI_SUI", 1),
        ("L02", "光明燈", 500, "BRIGHT", 2),
        ("L03", "吉祥如意燈", 1200, "JI_XIANG", 3),
        ("L04", "祭改", 500, "JI_GAI", 4),
    )
    SCHEDULER_SMTP_PASSWORD_SECRET_KEY = "scheduler/smtp_app_password"
    BACKUP_DRIVE_OAUTH_TOKEN_SECRET_KEY = "backup/google_oauth_token_json"
    BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT = "backup/cloud_encryption_key/current"
    BACKUP_CLOUD_ENCRYPTION_KEY_PREVIOUS = "backup/cloud_encryption_key/previous"
    BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY = "backup/cloud_encryption_key"

    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_security_schema()
        self._ensure_backup_schema()
        self._ensure_lighting_schema()
        self._ensure_lighting_signup_schema()
        self._ensure_system_income_items()
        self._ensure_system_expense_items()

    # -------------------------
    # Helpers 
    # -------------------------
    def _uuid(self) -> str:
        return str(uuid.uuid4())
    
    MIN_PASSWORD_LENGTH = 8

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _log_finance_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_finance_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    @staticmethod
    def _tx_type_label(tx_type: str) -> str:
        t = str(tx_type or "").strip().lower()
        if t == "income":
            return "收入"
        if t == "expense":
            return "支出"
        return "交易"

    def _build_transaction_detail(self, data: Dict[str, Any]) -> str:
        d = dict(data or {})
        parts = [
            f"日期 {self._fmt_log_val(d.get('date'))}",
            f"類型 {self._fmt_log_val(d.get('type'))}",
            f"項目代號 {self._fmt_log_val(d.get('category_id'))}",
            f"項目名稱 {self._fmt_log_val(d.get('category_name'))}",
            f"金額 {self._fmt_log_val(d.get('amount'))}",
            f"對象 {self._fmt_log_val(d.get('payer_name'))}",
            f"信眾ID {self._fmt_log_val(d.get('payer_person_id'))}",
            f"經手人 {self._fmt_log_val(d.get('handler'))}",
            f"收據 {self._fmt_log_val(d.get('receipt_number'))}",
            f"備註 {self._fmt_log_val(d.get('note'))}",
            f"來源類型 {self._fmt_log_val(d.get('source_type'))}",
            f"來源ID {self._fmt_log_val(d.get('source_id'))}",
            f"調整類型 {self._fmt_log_val(d.get('adjustment_kind'))}",
            f"系統產生 {self._fmt_log_val(d.get('is_system_generated'))}",
        ]
        return "，".join(parts)

    def _build_transaction_diff(self, before: Dict[str, Any], after: Dict[str, Any]) -> str:
        fields = [
            ("date", "日期"),
            ("category_id", "項目代號"),
            ("category_name", "項目名稱"),
            ("amount", "金額"),
            ("payer_person_id", "信眾ID"),
            ("payer_name", "對象"),
            ("handler", "經手人"),
            ("receipt_number", "收據"),
            ("note", "備註"),
            ("source_type", "來源類型"),
            ("source_id", "來源ID"),
            ("adjustment_kind", "調整類型"),
        ]
        changes = []
        for key, label in fields:
            old = self._fmt_log_val(before.get(key))
            new = self._fmt_log_val(after.get(key))
            if old != new:
                changes.append(f"{label}：{old} -> {new}")
        return "；".join(changes) if changes else "無欄位變更"

    def _log_transaction_change(
        self,
        action: str,
        tx_id,
        data: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = dict(data or {})
        before_payload = dict(before or {})
        tx_type = str(payload.get("type") or before_payload.get("type") or "").strip().lower()
        tx_label = self._tx_type_label(tx_type)
        action_u = str(action or "").strip().upper()
        detail = self._build_transaction_detail(payload)

        if action_u.endswith(".UPDATE"):
            diff = self._build_transaction_diff(before_payload, payload)
            msg = f"修改{tx_label}資料（ID {tx_id}，{detail}，變更：{diff}）"
        elif action_u.endswith(".DELETE"):
            msg = f"刪除{tx_label}資料（ID {tx_id}，{detail}）"
        elif action_u.endswith(".CREATE"):
            msg = f"新增{tx_label}資料（ID {tx_id}，{detail}）"
        else:
            msg = f"{tx_label}資料異動（ID {tx_id}，{detail}）"
        self._log_finance_data_change(action=action, message=msg)

    def _log_people_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_people_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _log_activity_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_activity_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _log_lighting_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_lighting_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _log_account_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_account_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _log_backup_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_backup_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _log_scheduler_data_change(self, action: str, message: str) -> None:
        try:
            log_data_change(action=action, message=message, level="INFO")
        except Exception:
            pass

    def _log_scheduler_system_event(self, message: str, level: str = "WARN") -> None:
        try:
            log_system(message, level=level)
        except Exception:
            pass

    def _lighting_item_ids_text(
        self,
        item_ids: List[str],
        active_map: Optional[Dict[str, Any]] = None,
    ) -> str:
        ids = [str(x or "").strip() for x in (item_ids or []) if str(x or "").strip()]
        if not ids:
            return "-"
        if not active_map:
            return "、".join(ids)
        parts = []
        for iid in ids:
            item = active_map.get(iid) or {}
            name = str(item.get("name") or "").strip()
            fee = int(item.get("fee") or 0)
            if name:
                parts.append(f"{iid}:{name}({fee})")
            else:
                parts.append(iid)
        return "、".join(parts) if parts else "-"

    def _resolve_person_name(self, person_id: str) -> str:
        pid = str(person_id or "").strip()
        if not pid or not self._table_exists("people"):
            return ""
        try:
            cur = self.conn.cursor()
            row = cur.execute("SELECT name FROM people WHERE id = ? LIMIT 1", (pid,)).fetchone()
            return str((row["name"] if row and "name" in row.keys() else "") or "").strip()
        except Exception:
            return ""

    def _resolve_activity_name(self, activity_id: str) -> str:
        aid = str(activity_id or "").strip()
        if not aid or not self._table_exists("activities"):
            return ""
        try:
            cur = self.conn.cursor()
            row = cur.execute("SELECT name FROM activities WHERE id = ? LIMIT 1", (aid,)).fetchone()
            return str((row["name"] if row and "name" in row.keys() else "") or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _fmt_log_val(value: Any) -> str:
        if value is None:
            return "-"
        text = str(value).strip()
        return text if text else "-"

    def _build_people_profile_detail(self, data: Dict[str, Any]) -> str:
        return (
            f"姓名 {self._fmt_log_val(data.get('name'))}，"
            f"性別 {self._fmt_log_val(data.get('gender'))}，"
            f"國曆生日 {self._fmt_log_val(data.get('birthday_ad'))}，"
            f"農曆生日 {self._fmt_log_val(data.get('birthday_lunar'))}，"
            f"農曆生日為閏月 {self._fmt_log_val(data.get('lunar_is_leap'))}，"
            f"出生時辰 {self._fmt_log_val(data.get('birth_time'))}，"
            f"手機號碼 {self._fmt_log_val(data.get('phone_mobile'))}，"
            f"聯絡電話 {self._fmt_log_val(data.get('phone_home'))}，"
            f"地址 {self._fmt_log_val(data.get('address'))}，"
            f"郵遞區號 {self._fmt_log_val(data.get('zip_code'))}，"
            f"年齡 {self._fmt_log_val(data.get('age'))}，"
            f"生肖 {self._fmt_log_val(data.get('zodiac'))}，"
            f"備註 {self._fmt_log_val(data.get('note'))}"
        )

    def _column_exists(self, table: str, column: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return any(r[1] == column for r in cur.fetchall())

    def _table_exists(self, table: str) -> bool:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return bool(row)

    @staticmethod
    def _parse_ymd_to_date(text: Optional[str]) -> Optional[date]:
        s = (text or "").strip()
        if not s:
            return None
        s = s.replace("-", "/")
        try:
            return datetime.strptime(s, "%Y/%m/%d").date()
        except Exception:
            return None

    def _calc_age_by_birthday(self, birthday_text: Optional[str]) -> Optional[int]:
        birthday = self._parse_ymd_to_date(birthday_text)
        if not birthday:
            return None
        today = date.today()
        age = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1
        return max(0, age)

    def _derive_age_offset(self, birthday_text: Optional[str], input_age: Any) -> Optional[int]:
        if input_age in (None, ""):
            return None
        try:
            age_value = int(str(input_age).strip())
        except Exception:
            return None
        auto_age = self._calc_age_by_birthday(birthday_text)
        if auto_age is None:
            return 0
        return age_value - auto_age

    def _apply_effective_age(self, person: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(person)
        auto_age = self._calc_age_by_birthday(data.get("birthday_ad"))
        if auto_age is None:
            return data
        try:
            offset = int(data.get("age_offset") or 0)
        except Exception:
            offset = 0
        data["age"] = max(0, auto_age + offset)
        return data

    def _ensure_security_schema(self):
        if not self._table_exists("app_settings"):
            return
        self._ensure_setting("security/password_reminder_days", "90")
        self._ensure_setting("security/idle_logout_minutes", "15")
        self._ensure_setting("ui/login_cover_title", "")
        self._ensure_setting("ui/login_cover_image_path", "")
        self._ensure_setting("scheduler/smtp_username", "")
        self._ensure_setting("scheduler/config_path", "app/scheduler/scheduler_config.yaml")
        self._ensure_setting("scheduler/mail_enabled", "1")
        self._ensure_setting("scheduler/backup_enabled", "1")
        self.conn.commit()

    @staticmethod
    def _map_security_action_to_event_type(action: str) -> str:
        a = str(action or "").strip().lower()
        mapping = {
            "create_user": "AUTH.USER.CREATE",
            "reset_password": "AUTH.USER.RESET_PASSWORD",
            "enable_user": "AUTH.USER.ENABLE",
            "disable_user": "AUTH.USER.DISABLE",
            "delete_user": "AUTH.USER.DELETE",
        }
        return mapping.get(a, "AUTH.SECURITY.EVENT")

    def _ensure_backup_schema(self):
        if not self._table_exists("app_settings"):
            return
        self._ensure_setting("backup/enabled", "0")
        self._ensure_setting("backup/frequency", "daily")     # daily / weekly / monthly
        self._ensure_setting("backup/time", "23:00")          # HH:MM
        self._ensure_setting("backup/weekday", "1")           # 1=Mon ... 7=Sun
        self._ensure_setting("backup/monthday", "1")          # 1..31
        self._ensure_setting("backup/keep_latest", "20")
        self._ensure_setting("backup/local_dir", "")
        self._ensure_setting("backup/last_run_at", "")
        self._ensure_setting("backup/drive_folder_id", "")    # phase-2 用
        self._ensure_setting("backup/drive_credentials_path", "")  # legacy key
        self._ensure_setting("backup/use_cli_scheduler", "0")
        self._ensure_setting("backup/enable_local", "1")
        self._ensure_setting("backup/enable_drive", "0")
        self.conn.commit()

    def _ensure_lighting_schema(self):
        if not self._table_exists("lighting_items"):
            return
        self._ensure_default_lighting_items()

    def _ensure_default_lighting_items(self):
        cur = self.conn.cursor()
        changed = False
        for item_id, name, fee, kind, sort_order in self.SYSTEM_LIGHTING_ITEMS:
            row = cur.execute(
                "SELECT id FROM lighting_items WHERE id = ? LIMIT 1",
                (item_id,),
            ).fetchone()
            if row:
                continue
            now_text = self._now()
            cur.execute(
                """
                INSERT INTO lighting_items
                (id, name, fee, kind, sort_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (item_id, name, int(fee), kind, int(sort_order), now_text, now_text),
            )
            changed = True
        if changed:
            self.conn.commit()

    def _next_lighting_item_id(self) -> str:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT id FROM lighting_items").fetchall()
        max_num = 0
        for (raw_id,) in rows:
            sid = str(raw_id or "").strip().upper()
            m = re.match(r"^L(\d+)$", sid)
            if m:
                max_num = max(max_num, int(m.group(1)))
        return f"L{max_num + 1:02d}"

    def list_lighting_items(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        sql = """
            SELECT id, name, fee, kind, sort_order, COALESCE(is_active, 1) AS is_active,
                   created_at, updated_at
            FROM lighting_items
        """
        params: List[Any] = []
        if not include_inactive:
            sql += " WHERE COALESCE(is_active, 1) = 1"
        sql += " ORDER BY COALESCE(sort_order, 0), id"
        rows = cur.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def create_lighting_item(self, name: str, fee: int, kind: str = "JI_XIANG") -> str:
        name = (name or "").strip()
        kind = (kind or "JI_XIANG").strip().upper()
        if not name:
            self._log_lighting_system_event("新增安燈燈別失敗（原因：燈別名稱為空）", level="WARN")
            raise ValueError("lighting name is required")
        try:
            fee_value = int(fee or 0)
        except Exception:
            fee_value = 0
        item_id = self._next_lighting_item_id()
        now_text = self._now()
        cur = self.conn.cursor()
        try:
            next_sort = cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM lighting_items").fetchone()[0]
            cur.execute(
                """
                INSERT INTO lighting_items
                (id, name, fee, kind, sort_order, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (item_id, name, fee_value, kind, int(next_sort or 1), now_text, now_text),
            )
            self.conn.commit()
        except Exception as e:
            self._log_lighting_system_event(
                f"新增安燈燈別失敗（燈別名稱 {name}，原因：{e}）",
                level="ERROR",
            )
            raise
        self._log_lighting_data_change(
            "LIGHTING.ITEM.CREATE",
            f"新增安燈燈別（燈別ID {item_id}，燈別名稱 {name}，費用 {fee_value}，類型 {kind}，狀態 啟用）",
        )
        return item_id

    def update_lighting_item(self, item_id: str, name: str, fee: int, kind: str = "JI_XIANG") -> bool:
        name = (name or "").strip()
        kind = (kind or "JI_XIANG").strip().upper()
        if not name:
            self._log_lighting_system_event(
                f"修改安燈燈別失敗（燈別ID {item_id}，原因：燈別名稱為空）",
                level="WARN",
            )
            raise ValueError("lighting name is required")
        try:
            fee_value = int(fee or 0)
        except Exception:
            fee_value = 0
        cur = self.conn.cursor()
        before = cur.execute(
            """
            SELECT id, name, fee, kind, COALESCE(is_active, 1) AS is_active
            FROM lighting_items
            WHERE id = ?
            LIMIT 1
            """,
            (item_id,),
        ).fetchone()
        if not before:
            self._log_lighting_system_event(
                f"修改安燈燈別失敗（燈別ID {item_id} 不存在）",
                level="WARN",
            )
            return False
        try:
            cur.execute(
                """
                UPDATE lighting_items
                SET name = ?, fee = ?, kind = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, fee_value, kind, self._now(), item_id),
            )
            self.conn.commit()
        except Exception as e:
            self._log_lighting_system_event(
                f"修改安燈燈別失敗（燈別ID {item_id}，原因：{e}）",
                level="ERROR",
            )
            raise
        ok = cur.rowcount > 0
        if ok:
            self._log_lighting_data_change(
                "LIGHTING.ITEM.UPDATE",
                (
                    f"修改安燈燈別（燈別ID {item_id}，"
                    f"燈別名稱：{self._fmt_log_val(before['name'])} -> {self._fmt_log_val(name)}，"
                    f"費用：{self._fmt_log_val(before['fee'])} -> {self._fmt_log_val(fee_value)}，"
                    f"類型：{self._fmt_log_val(before['kind'])} -> {self._fmt_log_val(kind)}，"
                    f"狀態 {'啟用' if int(before['is_active'] or 0) == 1 else '停用'}）"
                ),
            )
        else:
            self._log_lighting_system_event(
                f"修改安燈燈別失敗（燈別ID {item_id} 未更新任何資料）",
                level="WARN",
            )
        return ok

    def toggle_lighting_item_active(self, item_id: str) -> bool:
        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT name, COALESCE(is_active, 1) AS is_active
            FROM lighting_items
            WHERE id = ?
            LIMIT 1
            """,
            (item_id,),
        ).fetchone()
        if not row:
            self._log_lighting_system_event(
                f"停用/啟用安燈燈別失敗（燈別ID {item_id} 不存在）",
                level="WARN",
            )
            return False
        current_active = int(row["is_active"] or 0)
        next_active = 0 if current_active == 1 else 1
        try:
            cur.execute(
                "UPDATE lighting_items SET is_active = ?, updated_at = ? WHERE id = ?",
                (next_active, self._now(), item_id),
            )
            self.conn.commit()
        except Exception as e:
            self._log_lighting_system_event(
                f"停用/啟用安燈燈別失敗（燈別ID {item_id}，原因：{e}）",
                level="ERROR",
            )
            raise
        ok = cur.rowcount > 0
        if ok:
            self._log_lighting_data_change(
                "LIGHTING.ITEM.TOGGLE_ACTIVE",
                (
                    f"安燈燈別狀態變更（燈別ID {item_id}，燈別名稱 {self._fmt_log_val(row['name'])}，"
                    f"狀態：{'啟用' if current_active == 1 else '停用'} -> {'啟用' if next_active == 1 else '停用'}）"
                ),
            )
        else:
            self._log_lighting_system_event(
                f"停用/啟用安燈燈別失敗（燈別ID {item_id} 未更新任何資料）",
                level="WARN",
            )
        return ok

    def _ensure_lighting_signup_schema(self):
        # Runtime 不再自動建表（開發期 schema 由 setup_db.py 一次建立）
        return

    def list_lighting_signups(self, signup_year: int, keyword: str = "", unpaid_only: bool = False) -> List[Dict[str, Any]]:
        year_value = int(signup_year)
        kw = (keyword or "").strip()
        cur = self.conn.cursor()
        sql = """
            SELECT
                s.id AS signup_id,
                s.signup_year,
                s.person_id,
                COALESCE(s.group_id, s.id) AS group_id,
                COALESCE(s.signup_kind, 'INITIAL') AS signup_kind,
                p.name AS person_name,
                COALESCE(p.phone_mobile, '') AS person_phone,
                COALESCE(s.total_amount, 0) AS total_amount,
                COALESCE(s.is_paid, 0) AS is_paid,
                s.paid_at,
                s.payment_receipt_number,
                GROUP_CONCAT(i.lighting_item_name, '、') AS lighting_summary
            FROM lighting_signups s
            JOIN people p ON p.id = s.person_id
            LEFT JOIN lighting_signup_items i ON i.signup_id = s.id
            WHERE s.signup_year = ?
        """
        params: List[Any] = [year_value]
        if unpaid_only:
            sql += " AND COALESCE(s.is_paid, 0) = 0"
        if kw:
            sql += " AND (p.name LIKE ? OR COALESCE(p.phone_mobile,'') LIKE ?)"
            like_kw = f"%{kw}%"
            params.extend([like_kw, like_kw])
        sql += """
            GROUP BY s.id
            ORDER BY
                COALESCE(s.group_id, s.id) ASC,
                CASE COALESCE(s.signup_kind, 'INITIAL')
                  WHEN 'INITIAL' THEN 0
                  WHEN 'APPEND' THEN 1
                  ELSE 9
                END ASC,
                datetime(replace(COALESCE(s.created_at,''), '/', '-')) ASC,
                s.id ASC
        """
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def _prepare_lighting_signup_payload(self, person_id: str, lighting_item_ids: List[str]) -> Dict[str, Any]:
        pid = str(person_id or "").strip()
        if not pid:
            raise ValueError("person_id 為必填")

        normalized_item_ids: List[str] = []
        seen = set()
        for x in (lighting_item_ids or []):
            iid = str(x or "").strip()
            if not iid or iid in seen:
                continue
            seen.add(iid)
            normalized_item_ids.append(iid)
        if not normalized_item_ids:
            raise ValueError("至少選擇一個燈別")

        active_items = self.list_lighting_items(include_inactive=False)
        active_map = {str(r.get("id") or "").strip(): r for r in active_items}
        invalid = [iid for iid in normalized_item_ids if iid not in active_map]
        if invalid:
            raise ValueError(f"含無效或未啟用燈別：{', '.join(invalid)}")

        cur = self.conn.cursor()
        person_row = cur.execute("SELECT id FROM people WHERE id = ? LIMIT 1", (pid,)).fetchone()
        if not person_row:
            raise ValueError("找不到人員資料")

        total_amount = sum(int(active_map[iid].get("fee") or 0) for iid in normalized_item_ids)
        return {
            "person_id": pid,
            "item_ids": normalized_item_ids,
            "active_map": active_map,
            "total_amount": int(total_amount),
        }

    def get_lighting_signup_item_totals(self, signup_year: int, keyword: str = "") -> List[Dict[str, Any]]:
        """
        依燈別彙總報名人數與金額。
        keyword 會套用在姓名/手機（與明細搜尋一致）。
        """
        year_value = int(signup_year)
        kw = (keyword or "").strip()
        cur = self.conn.cursor()
        sql = """
            SELECT
                i.lighting_item_id,
                i.lighting_item_name,
                COUNT(DISTINCT s.id) AS signup_count,
                COALESCE(SUM(i.fee_snapshot), 0) AS total_amount
            FROM lighting_signups s
            JOIN people p ON p.id = s.person_id
            JOIN lighting_signup_items i ON i.signup_id = s.id
            WHERE s.signup_year = ?
        """
        params: List[Any] = [year_value]
        if kw:
            like_kw = f"%{kw}%"
            sql += " AND (p.name LIKE ? OR COALESCE(p.phone_mobile,'') LIKE ?)"
            params.extend([like_kw, like_kw])
        sql += """
            GROUP BY i.lighting_item_id, i.lighting_item_name
            ORDER BY i.lighting_item_id ASC
        """
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def list_lighting_signup_rows_by_item(self, signup_year: int, keyword: str = "") -> List[Dict[str, Any]]:
        """
        供「安燈報名 / 列印名單」使用：
        依燈別列出明細（每個人每個燈別一列），可套用姓名/手機關鍵字。
        """
        year_value = int(signup_year)
        kw = (keyword or "").strip()
        cur = self.conn.cursor()
        sql = """
            SELECT
                i.lighting_item_id,
                i.lighting_item_name,
                p.name AS person_name,
                COALESCE(p.phone_mobile, '') AS person_phone,
                COALESCE(i.fee_snapshot, 0) AS item_amount,
                COALESCE(s.is_paid, 0) AS is_paid,
                COALESCE(s.payment_receipt_number, '') AS payment_receipt_number
            FROM lighting_signups s
            JOIN people p ON p.id = s.person_id
            JOIN lighting_signup_items i ON i.signup_id = s.id
            WHERE s.signup_year = ?
        """
        params: List[Any] = [year_value]
        if kw:
            like_kw = f"%{kw}%"
            sql += " AND (p.name LIKE ? OR COALESCE(p.phone_mobile,'') LIKE ?)"
            params.extend([like_kw, like_kw])
        sql += """
            ORDER BY
                i.lighting_item_id ASC,
                i.lighting_item_name ASC,
                p.name ASC,
                s.id ASC
        """
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def get_lighting_signup_selected_item_ids(self, signup_year: int, person_ids: List[str]) -> Dict[str, List[str]]:
        """
        回傳指定人員在該年度已勾選燈別：
        {person_id: [lighting_item_id, ...]}
        """
        normalized_ids = []
        seen = set()
        for x in (person_ids or []):
            pid = str(x or "").strip()
            if not pid or pid in seen:
                continue
            seen.add(pid)
            normalized_ids.append(pid)
        if not normalized_ids:
            return {}

        cur = self.conn.cursor()
        q_marks = ",".join(["?"] * len(normalized_ids))
        sql = f"""
            SELECT s.person_id, i.lighting_item_id
            FROM lighting_signups s
            JOIN lighting_signup_items i ON i.signup_id = s.id
            WHERE s.signup_year = ? AND s.person_id IN ({q_marks})
            ORDER BY s.person_id ASC, i.lighting_item_id ASC
        """
        rows = cur.execute(sql, (int(signup_year), *normalized_ids)).fetchall()
        result: Dict[str, List[str]] = {pid: [] for pid in normalized_ids}
        for r in rows:
            pid = str(r["person_id"] or "").strip()
            iid = str(r["lighting_item_id"] or "").strip()
            if pid and iid:
                result.setdefault(pid, []).append(iid)
        return result

    def upsert_lighting_signup(
        self,
        signup_year: int,
        person_id: str,
        lighting_item_ids: List[str],
        note: str = "",
        allow_paid_update: bool = False,
    ) -> str:
        """
        建立或更新（覆蓋）某人某年度安燈報名。
        - 若既有資料已繳費，預設拒絕修改（allow_paid_update=True 可放寬，供業務頁差額流程使用）
        - 僅接受目前啟用中的燈別
        """
        year_value = int(signup_year)
        try:
            payload = self._prepare_lighting_signup_payload(person_id, lighting_item_ids)
        except Exception as e:
            self._log_lighting_system_event(
                f"安燈報名新增/修改失敗（年度 {year_value}，person_id {self._fmt_log_val(person_id)}，原因：{e}）",
                level="WARN",
            )
            raise
        pid = str(payload["person_id"])
        normalized_item_ids = list(payload["item_ids"])
        active_map = dict(payload["active_map"])
        total_amount = int(payload["total_amount"])
        cur = self.conn.cursor()
        now = self._now()
        note_text = (note or "").strip() or None
        person_name = self._resolve_person_name(pid) or "-"
        old_total = None
        old_item_ids: List[str] = []
        action = "LIGHTING.SIGNUP.CREATE"

        try:
            cur.execute("BEGIN;")
            existing = cur.execute(
                """
                SELECT id, COALESCE(is_paid, 0) AS is_paid
                FROM lighting_signups
                WHERE signup_year = ? AND person_id = ?
                ORDER BY
                    CASE COALESCE(signup_kind, 'INITIAL')
                      WHEN 'INITIAL' THEN 0
                      WHEN 'APPEND' THEN 1
                      ELSE 9
                    END ASC,
                    datetime(replace(COALESCE(created_at,''), '/', '-')) ASC,
                    id ASC
                LIMIT 1
                """,
                (year_value, pid),
            ).fetchone()

            if existing:
                signup_id = str(existing["id"] or "")
                if int(existing["is_paid"] or 0) == 1 and not bool(allow_paid_update):
                    self._log_lighting_system_event(
                        f"安燈報名修改失敗（signup_id {signup_id}，原因：已繳費且未允許修改）",
                        level="WARN",
                    )
                    raise ValueError("此筆安燈報名已繳費，不可直接修改")
                old_total_row = cur.execute(
                    "SELECT COALESCE(total_amount, 0) FROM lighting_signups WHERE id = ? LIMIT 1",
                    (signup_id,),
                ).fetchone()
                old_total = int((old_total_row[0] if old_total_row else 0) or 0)
                old_rows = cur.execute(
                    "SELECT lighting_item_id FROM lighting_signup_items WHERE signup_id = ? ORDER BY lighting_item_id",
                    (signup_id,),
                ).fetchall()
                old_item_ids = [str(r[0] or "").strip() for r in old_rows if str(r[0] or "").strip()]
                action = "LIGHTING.SIGNUP.UPDATE"
                cur.execute(
                    """
                    UPDATE lighting_signups
                    SET total_amount = ?, note = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (int(total_amount), note_text, now, signup_id),
                )
                cur.execute("DELETE FROM lighting_signup_items WHERE signup_id = ?", (signup_id,))
            else:
                signup_id = self._uuid()
                cur.execute(
                    """
                    INSERT INTO lighting_signups (
                        id, signup_year, person_id, group_id, signup_kind, total_amount, note, is_paid, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'INITIAL', ?, ?, 0, ?, ?)
                    """,
                    (signup_id, year_value, pid, signup_id, int(total_amount), note_text, now, now),
                )

            for iid in normalized_item_ids:
                item = active_map[iid]
                cur.execute(
                    """
                    INSERT INTO lighting_signup_items (
                        signup_id, lighting_item_id, lighting_item_name, fee_snapshot
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        signup_id,
                        iid,
                        str(item.get("name") or ""),
                        int(item.get("fee") or 0),
                    ),
                )

            cur.execute("COMMIT;")
            self._log_lighting_data_change(
                action,
                (
                    f"安燈報名{'修改' if action.endswith('UPDATE') else '新增'}（signup_id {signup_id}，年度 {year_value}，"
                    f"報名人 {person_name}（person_id {pid}），"
                    f"燈別 {self._lighting_item_ids_text(normalized_item_ids, active_map)}，"
                    f"總金額 {total_amount}，備註 {self._fmt_log_val(note_text)}"
                    + (
                        f"，原燈別 {self._lighting_item_ids_text(old_item_ids)}，原總金額 {self._fmt_log_val(old_total)}"
                        if action.endswith("UPDATE")
                        else ""
                    )
                    + "）"
                ),
            )
            return signup_id
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"安燈報名新增/修改失敗（年度 {year_value}，person_id {pid}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise

    def create_lighting_signup_append(self, signup_year: int, person_id: str, lighting_item_ids: List[str], note: str = "") -> Dict[str, Any]:
        """
        新規則（安燈）：
        已繳費後不修改原單，改為新增一筆「追加」紀錄。
        """
        year_value = int(signup_year)
        try:
            payload = self._prepare_lighting_signup_payload(person_id, lighting_item_ids)
        except Exception as e:
            self._log_lighting_system_event(
                f"新增安燈追加報名失敗（年度 {year_value}，person_id {self._fmt_log_val(person_id)}，原因：{e}）",
                level="WARN",
            )
            raise
        pid = str(payload["person_id"])
        normalized_item_ids = list(payload["item_ids"])
        active_map = dict(payload["active_map"])
        total_amount = int(payload["total_amount"])
        note_text = (note or "").strip() or None
        now = self._now()
        cur = self.conn.cursor()
        person_name = self._resolve_person_name(pid) or "-"

        existing_rows = cur.execute(
            """
            SELECT id, COALESCE(group_id, id) AS group_id
            FROM lighting_signups
            WHERE signup_year = ? AND person_id = ?
            ORDER BY
                CASE COALESCE(signup_kind, 'INITIAL')
                  WHEN 'INITIAL' THEN 0
                  WHEN 'APPEND' THEN 1
                  ELSE 9
                END ASC,
                datetime(replace(COALESCE(created_at,''), '/', '-')) ASC,
                id ASC
            """,
            (year_value, pid),
        ).fetchall()
        if existing_rows:
            group_id = str(existing_rows[0]["group_id"] or existing_rows[0]["id"] or "").strip()
            signup_kind = "APPEND"
        else:
            group_id = ""
            signup_kind = "INITIAL"

        signup_id = self._uuid()
        if not group_id:
            group_id = signup_id

        try:
            cur.execute("BEGIN;")
            cur.execute(
                """
                INSERT INTO lighting_signups (
                    id, signup_year, person_id, group_id, signup_kind, total_amount, note, is_paid, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (signup_id, year_value, pid, group_id, signup_kind, total_amount, note_text, now, now),
            )
            for iid in normalized_item_ids:
                item = active_map[iid]
                cur.execute(
                    """
                    INSERT INTO lighting_signup_items (
                        signup_id, lighting_item_id, lighting_item_name, fee_snapshot
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (signup_id, iid, str(item.get("name") or ""), int(item.get("fee") or 0)),
                )
            cur.execute("COMMIT;")
            self._log_lighting_data_change(
                "LIGHTING.SIGNUP.APPEND",
                (
                    f"新增安燈追加報名（signup_id {signup_id}，年度 {year_value}，"
                    f"報名人 {person_name}（person_id {pid}），group_id {group_id}，kind {signup_kind}，"
                    f"燈別 {self._lighting_item_ids_text(normalized_item_ids, active_map)}，"
                    f"總金額 {total_amount}，備註 {self._fmt_log_val(note_text)}）"
                ),
            )
            return {"signup_id": signup_id, "group_id": group_id, "signup_kind": signup_kind}
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"新增安燈追加報名失敗（年度 {year_value}，person_id {pid}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise

    def update_lighting_signup_items_by_signup_id(
        self,
        signup_id: str,
        lighting_item_ids: List[str],
        note: str = "",
        allow_paid_update: bool = False,
    ) -> str:
        sid = str(signup_id or "").strip()
        if not sid:
            self._log_lighting_system_event("安燈報名修改失敗（原因：signup_id 為空）", level="WARN")
            raise ValueError("signup_id 為必填")
        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT id, person_id, COALESCE(is_paid, 0) AS is_paid
            FROM lighting_signups
            WHERE id = ?
            LIMIT 1
            """,
            (sid,),
        ).fetchone()
        if not row:
            self._log_lighting_system_event(f"安燈報名修改失敗（signup_id {sid} 不存在）", level="WARN")
            raise ValueError("找不到安燈報名資料")
        if int(row["is_paid"] or 0) == 1 and not bool(allow_paid_update):
            self._log_lighting_system_event(
                f"安燈報名修改失敗（signup_id {sid} 已繳費，未允許修改）",
                level="WARN",
            )
            raise ValueError("此筆安燈報名已繳費，不可直接修改")

        try:
            payload = self._prepare_lighting_signup_payload(str(row["person_id"] or ""), lighting_item_ids)
        except Exception as e:
            self._log_lighting_system_event(
                f"安燈報名修改失敗（signup_id {sid}，原因：{e}）",
                level="WARN",
            )
            raise
        normalized_item_ids = list(payload["item_ids"])
        active_map = dict(payload["active_map"])
        total_amount = int(payload["total_amount"])
        now = self._now()
        note_text = (note or "").strip() or None
        person_id = str(row["person_id"] or "")
        person_name = self._resolve_person_name(person_id) or "-"
        before_total_row = cur.execute(
            "SELECT COALESCE(total_amount, 0) FROM lighting_signups WHERE id = ? LIMIT 1",
            (sid,),
        ).fetchone()
        before_total = int((before_total_row[0] if before_total_row else 0) or 0)
        before_item_rows = cur.execute(
            "SELECT lighting_item_id FROM lighting_signup_items WHERE signup_id = ? ORDER BY lighting_item_id",
            (sid,),
        ).fetchall()
        before_item_ids = [str(r[0] or "").strip() for r in before_item_rows if str(r[0] or "").strip()]

        try:
            cur.execute("BEGIN;")
            cur.execute(
                """
                UPDATE lighting_signups
                SET total_amount = ?, note = ?, updated_at = ?
                WHERE id = ?
                """,
                (total_amount, note_text, now, sid),
            )
            cur.execute("DELETE FROM lighting_signup_items WHERE signup_id = ?", (sid,))
            for iid in normalized_item_ids:
                item = active_map[iid]
                cur.execute(
                    """
                    INSERT INTO lighting_signup_items (
                        signup_id, lighting_item_id, lighting_item_name, fee_snapshot
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (sid, iid, str(item.get("name") or ""), int(item.get("fee") or 0)),
                )
            cur.execute("COMMIT;")
            self._log_lighting_data_change(
                "LIGHTING.SIGNUP.UPDATE_ITEMS",
                (
                    f"修改安燈報名燈別（signup_id {sid}，報名人 {person_name}（person_id {person_id}），"
                    f"原燈別 {self._lighting_item_ids_text(before_item_ids)}，"
                    f"新燈別 {self._lighting_item_ids_text(normalized_item_ids, active_map)}，"
                    f"原總金額 {before_total}，新總金額 {total_amount}，備註 {self._fmt_log_val(note_text)}）"
                ),
            )
            return sid
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"安燈報名修改失敗（signup_id {sid}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise

    def delete_lighting_signup(self, signup_year: int, signup_id: str) -> bool:
        """
        刪除指定年度的安燈報名。
        若已繳費：刪除當前選取業務紀錄前，將對應交易標記為作廢（is_voided=1）。
        """
        sid = str(signup_id or "").strip()
        if not sid:
            self._log_lighting_system_event("刪除安燈報名失敗（原因：signup_id 為空）", level="WARN")
            return False
        year_value = int(signup_year)
        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT id, COALESCE(is_paid, 0) AS is_paid
            FROM lighting_signups
            WHERE signup_year = ? AND id = ?
            LIMIT 1
            """,
            (year_value, sid),
        ).fetchone()
        if not row:
            self._log_lighting_system_event(
                f"刪除安燈報名失敗（年度 {year_value}，signup_id {sid} 不存在）",
                level="WARN",
            )
            return False
        person_id_row = cur.execute(
            "SELECT person_id FROM lighting_signups WHERE id = ? LIMIT 1",
            (sid,),
        ).fetchone()
        person_id = str((person_id_row[0] if person_id_row else "") or "")
        person_name = self._resolve_person_name(person_id) or "-"
        voided_txn_count = 0
        try:
            cur.execute("BEGIN;")
            if int(row["is_paid"] or 0) == 1 and self._table_exists("transactions"):
                cols = self._table_columns("transactions")
                if "is_voided" in cols:
                    cur.execute(
                        """
                        UPDATE transactions
                        SET is_voided = 1
                        WHERE (is_deleted = 0 OR is_deleted IS NULL)
                          AND COALESCE(source_type, '') = 'LIGHTING_SIGNUP'
                          AND COALESCE(source_id, '') = ?
                        """,
                        (sid,),
                    )
                    voided_txn_count = int(cur.rowcount or 0)
            cur.execute("DELETE FROM lighting_signup_items WHERE signup_id = ?", (sid,))
            cur.execute("DELETE FROM lighting_signups WHERE id = ? AND signup_year = ?", (sid, year_value))
            cur.execute("COMMIT;")
            self._log_lighting_data_change(
                "LIGHTING.SIGNUP.DELETE",
                (
                    f"刪除安燈報名（年度 {year_value}，signup_id {sid}，"
                    f"報名人 {person_name}（person_id {person_id or '-'}），"
                    f"已繳費 {int(row['is_paid'] or 0)}，作廢交易筆數 {voided_txn_count}）"
                ),
            )
            return True
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"刪除安燈報名失敗（年度 {year_value}，signup_id {sid}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise

    def _resolve_lighting_income_item(self) -> Optional[Dict[str, Any]]:
        if not self._table_exists("income_items"):
            return None
        cur = self.conn.cursor()
        cols = self._table_columns("income_items")
        has_is_active = "is_active" in cols
        if has_is_active:
            cur.execute(
                "SELECT * FROM income_items WHERE id = ? AND COALESCE(is_active, 1) = 1 LIMIT 1",
                (self.LIGHTING_INCOME_ITEM_ID,),
            )
        else:
            cur.execute("SELECT * FROM income_items WHERE id = ? LIMIT 1", (self.LIGHTING_INCOME_ITEM_ID,))
        row = cur.fetchone()
        return dict(row) if row else None

    def _resolve_lighting_refund_expense_item(self) -> Optional[Dict[str, Any]]:
        if not self._table_exists("expense_items"):
            return None
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM expense_items WHERE id = ? LIMIT 1", (self.LIGHTING_REFUND_EXPENSE_ITEM_ID,)).fetchone()
        return dict(row) if row else None

    def get_lighting_zodiac_suggestions(self, year: Optional[int] = None) -> Dict[str, Any]:
        target_year = int(year or date.today().year)
        zodiac_order = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
        idx = (target_year - 4) % 12
        current_zodiac = zodiac_order[idx]
        # 12 神煞（以當年太歲生肖為起點，依序每項往前一個生肖）
        star_order = [
            "太歲", "太陽", "喪門", "太陰", "五鬼", "死符",
            "歲破", "龍德", "白虎", "福德", "天狗", "病符",
        ]
        star_display_alias = {"太陰": "男制太陰女制桃花", "福德": "吉星臨照", "龍德": "紫微星拱照"}
        star_zodiac_map: Dict[str, str] = {}
        star_positions: List[Dict[str, Any]] = []
        for offset, star_name in enumerate(star_order):
            zodiac = zodiac_order[(idx - offset) % 12]
            star_zodiac_map[star_name] = zodiac
            star_positions.append({
                "order": offset + 1,
                "star": star_name,
                "zodiac": zodiac,
            })

        tai_sui_stars = ["太歲", "歲破"]
        ji_gai_star_alias = {"太陰": "男制太陰女制桃花"}
        ji_gai_stars = ["喪門", "太陰", "五鬼", "死符", "白虎", "天狗", "病符"]
        tai_sui_group = [star_zodiac_map[s] for s in tai_sui_stars]
        ji_gai_group = [star_zodiac_map[s] for s in ji_gai_stars]
        peaceful_star_pairs = [("太陽", "太陽"), ("福德", "吉星臨照"), ("龍德", "紫微星拱照")]
        peaceful_group = [star_zodiac_map[star] for star, _alias in peaceful_star_pairs]

        tai_sui_hint = "犯太歲：" + "、".join(
            [f"{star_zodiac_map[s]}（{s}）" for s in tai_sui_stars]
        )
        ji_gai_hint = "祭改：" + "、".join(
            [f"{star_zodiac_map[s]}（{ji_gai_star_alias.get(s, s)}）" for s in ji_gai_stars]
        )
        peaceful_hint = "平安無沖：" + "、".join(
            [f"{star_zodiac_map[star]}（{alias}）" for star, alias in peaceful_star_pairs]
        )
        zodiac_flow_labels = {
            zodiac: star_display_alias.get(star, star) for star, zodiac in star_zodiac_map.items()
        }
        return {
            "year": target_year,
            "year_zodiac": current_zodiac,
            "annual_star_zodiac_map": star_zodiac_map,
            "annual_star_positions": star_positions,
            "tai_sui_zodiacs": tai_sui_group,
            "ji_gai_zodiacs": ji_gai_group,
            "peaceful_zodiacs": peaceful_group,
            "tai_sui_hint": tai_sui_hint,
            "ji_gai_hint": ji_gai_hint,
            "peaceful_hint": peaceful_hint,
            "zodiac_flow_labels": zodiac_flow_labels,
        }

    def _default_lighting_hint_texts(self, year: Optional[int] = None) -> Dict[str, str]:
        info = self.get_lighting_zodiac_suggestions(year)
        return {
            "year": str(info.get("year") or date.today().year),
            "tai_sui_text": str(info.get("tai_sui_hint") or ""),
            "ji_gai_text": str(info.get("ji_gai_hint") or ""),
            "peaceful_text": str(info.get("peaceful_hint") or ""),
        }

    def get_lighting_hint_settings(self) -> Dict[str, str]:
        defaults = self._default_lighting_hint_texts()
        year_text = self.get_setting("lighting/hint_year", defaults["year"]).strip() or defaults["year"]
        tai_sui_text = self.get_setting("lighting/hint_tai_sui_text", defaults["tai_sui_text"]).strip() or defaults["tai_sui_text"]
        ji_gai_text = self.get_setting("lighting/hint_ji_gai_text", defaults["ji_gai_text"]).strip() or defaults["ji_gai_text"]
        peaceful_text = self.get_setting("lighting/hint_peaceful_text", defaults["peaceful_text"]).strip() or defaults["peaceful_text"]
        return {
            "year": year_text,
            "tai_sui_text": tai_sui_text,
            "ji_gai_text": ji_gai_text,
            "peaceful_text": peaceful_text,
        }

    def save_lighting_hint_settings(self, year: int, tai_sui_text: str, ji_gai_text: str, peaceful_text: str):
        self.set_setting("lighting/hint_year", str(int(year)))
        self.set_setting("lighting/hint_tai_sui_text", (tai_sui_text or "").strip())
        self.set_setting("lighting/hint_ji_gai_text", (ji_gai_text or "").strip())
        self.set_setting("lighting/hint_peaceful_text", (peaceful_text or "").strip())
        self._log_lighting_data_change(
            "LIGHTING.HINT.UPDATE",
            (
                f"更新安燈提示設定（年度 {int(year)}，"
                f"犯太歲提示 {self._fmt_log_val((tai_sui_text or '').strip())}，"
                f"祭改提示 {self._fmt_log_val((ji_gai_text or '').strip())}，"
                f"平安無沖提示 {self._fmt_log_val((peaceful_text or '').strip())}）"
            ),
        )

    def mark_lighting_signups_paid(self, signup_year: int, signup_ids: List[str], handler: str = "") -> Dict[str, Any]:
        normalized_ids = [str(x).strip() for x in (signup_ids or []) if str(x).strip()]
        if not normalized_ids:
            return {"paid_count": 0, "skipped_count": 0, "receipt_numbers": []}
        handler_text = (handler or "").strip()
        if not handler_text:
            self._log_lighting_system_event(
                f"安燈報名繳費失敗（年度 {int(signup_year)}，原因：經手人為空）",
                level="WARN",
            )
            raise ValueError("經手人為必填")

        income_item = self._resolve_lighting_income_item()
        if not income_item:
            self._log_lighting_system_event(
                f"安燈報名繳費失敗（年度 {int(signup_year)}，原因：找不到點燈收入項目 91）",
                level="WARN",
            )
            raise ValueError("找不到可用的點燈收入項目（91 點燈收入），請先確認類別設定")

        cur = self.conn.cursor()
        q_marks = ",".join(["?"] * len(normalized_ids))
        sql = f"""
            SELECT
                s.id AS signup_id,
                s.person_id,
                COALESCE(s.signup_kind, 'INITIAL') AS signup_kind,
                COALESCE(s.total_amount, 0) AS total_amount,
                COALESCE(s.is_paid, 0) AS is_paid,
                p.name AS person_name,
                GROUP_CONCAT(i.lighting_item_name, '、') AS lighting_summary
            FROM lighting_signups s
            JOIN people p ON p.id = s.person_id
            LEFT JOIN lighting_signup_items i ON i.signup_id = s.id
            WHERE s.signup_year = ? AND s.id IN ({q_marks})
            GROUP BY s.id
        """
        cur.execute(sql, (int(signup_year), *normalized_ids))
        rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            return {"paid_count": 0, "skipped_count": 0, "receipt_numbers": []}

        category_id = str(income_item.get("id") or "").strip()
        category_name = str(income_item.get("name") or "點燈收入").strip() or "點燈收入"
        today = datetime.now().strftime("%Y-%m-%d")
        now = self._now()
        paid_count = 0
        skipped_count = 0
        receipts: List[str] = []
        paid_details: List[str] = []
        skipped_details: List[str] = []
        try:
            cur.execute("BEGIN;")
            for row in rows:
                if int(row.get("is_paid") or 0) == 1:
                    skipped_count += 1
                    skipped_details.append(
                        f"{str(row.get('person_name') or '-')}（person_id {str(row.get('person_id') or '-')}, signup_id {str(row.get('signup_id') or '-')})"
                    )
                    continue
                signup_kind = str(row.get("signup_kind") or "INITIAL").strip().upper()
                adjustment_kind = "SUPPLEMENT" if signup_kind == "APPEND" else "PRIMARY"
                receipt = self.generate_receipt_number(today)
                note = f"[{signup_year}安燈] {str(row.get('lighting_summary') or '').strip()}".strip()
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today, category_id, category_name, int(row.get("total_amount") or 0),
                        str(row.get("person_id") or ""), str(row.get("person_name") or ""),
                        handler_text, receipt, note,
                        "LIGHTING_SIGNUP", str(row.get("signup_id") or ""), adjustment_kind, None, 1,
                    ),
                )
                txn_id = cur.lastrowid
                cur.execute(
                    "UPDATE lighting_signups SET is_paid = 1, paid_at = ?, payment_txn_id = ?, payment_receipt_number = ?, updated_at = ? WHERE id = ?",
                    (now, int(txn_id or 0), receipt, now, str(row.get("signup_id") or "")),
                )
                paid_count += 1
                receipts.append(receipt)
                paid_details.append(
                    f"{str(row.get('person_name') or '-')}（person_id {str(row.get('person_id') or '-')}, "
                    f"signup_id {str(row.get('signup_id') or '-')}, kind {signup_kind}, "
                    f"金額 {int(row.get('total_amount') or 0)}, 收據 {receipt}）"
                )
            cur.execute("COMMIT;")
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"安燈報名繳費失敗（年度 {int(signup_year)}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise
        if paid_count > 0:
            self._log_lighting_data_change(
                "LIGHTING.SIGNUP.PAY",
                (
                    f"安燈報名繳費完成（年度 {int(signup_year)}，經手人 {handler_text}，"
                    f"成功 {paid_count} 筆，略過 {skipped_count} 筆，"
                    f"繳費名單：{'；'.join(paid_details) if paid_details else '-'}，"
                    f"已繳費略過：{'；'.join(skipped_details) if skipped_details else '-'}）"
                ),
            )
        elif skipped_count > 0:
            self._log_lighting_system_event(
                f"安燈報名繳費未處理（年度 {int(signup_year)}，全部皆已繳費，略過 {skipped_count} 筆）",
                level="WARN",
            )
        return {"paid_count": paid_count, "skipped_count": skipped_count, "receipt_numbers": receipts}

    def update_paid_lighting_signup_with_adjustment(
        self,
        signup_year: int,
        person_id: str,
        lighting_item_ids: List[str],
        handler: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        """
        Phase 3（安燈先）backend：
        已繳費安燈報名修改後，自動建立差額交易（補繳/退費）。
        - 補繳：income / 91 點燈收入
        - 退費：expense / 91R 安燈退費
        """
        pid = str(person_id or "").strip()
        if not pid:
            self._log_lighting_system_event("安燈報名差額調整失敗（原因：person_id 為空）", level="WARN")
            raise ValueError("person_id 為必填")
        handler_text = (handler or "").strip()
        if not handler_text:
            self._log_lighting_system_event(
                f"安燈報名差額調整失敗（person_id {pid}，原因：經手人為空）",
                level="WARN",
            )
            raise ValueError("經手人為必填")

        cur = self.conn.cursor()
        existing = cur.execute(
            """
            SELECT
                s.id AS signup_id,
                s.person_id,
                COALESCE(s.total_amount, 0) AS total_amount,
                COALESCE(s.is_paid, 0) AS is_paid,
                s.payment_txn_id,
                p.name AS person_name
            FROM lighting_signups s
            JOIN people p ON p.id = s.person_id
            WHERE s.signup_year = ? AND s.person_id = ?
            LIMIT 1
            """,
            (int(signup_year), pid),
        ).fetchone()
        if not existing:
            self._log_lighting_system_event(
                f"安燈報名差額調整失敗（年度 {int(signup_year)}，person_id {pid}，原因：找不到安燈報名資料）",
                level="WARN",
            )
            raise ValueError("找不到安燈報名資料")

        old_total = int(existing["total_amount"] or 0)
        is_paid = int(existing["is_paid"] or 0) == 1
        signup_id = str(existing["signup_id"] or "")
        base_txn_id = existing["payment_txn_id"]
        person_name = str(existing["person_name"] or "")

        updated_signup_id = self.upsert_lighting_signup(
            signup_year,
            pid,
            lighting_item_ids,
            note=note,
            allow_paid_update=is_paid,
        )
        if updated_signup_id != signup_id:
            signup_id = updated_signup_id

        updated = cur.execute(
            "SELECT COALESCE(total_amount, 0) AS total_amount FROM lighting_signups WHERE id = ? LIMIT 1",
            (signup_id,),
        ).fetchone()
        new_total = int((updated["total_amount"] if updated else 0) or 0)
        delta = new_total - old_total

        if (not is_paid) or delta == 0:
            self._log_lighting_data_change(
                "LIGHTING.SIGNUP.ADJUST",
                (
                    f"安燈報名調整（無差額交易）（signup_id {signup_id}，"
                    f"報名人 {person_name or '-'}（person_id {pid}），"
                    f"舊金額 {old_total}，新金額 {new_total}，delta {delta}，is_paid {1 if is_paid else 0}）"
                ),
            )
            return {
                "signup_id": signup_id,
                "old_total": old_total,
                "new_total": new_total,
                "delta": delta,
                "adjustment_txn_id": None,
                "adjustment_type": None,
                "receipt_number": None,
                "is_paid": is_paid,
            }

        today = datetime.now().strftime("%Y-%m-%d")
        adjustment_txn_id = None
        adjustment_type = None
        receipt_number = None

        try:
            cur.execute("BEGIN;")
            if delta > 0:
                income_item = self._resolve_lighting_income_item()
                if not income_item:
                    self._log_lighting_system_event(
                        f"安燈報名差額調整失敗（signup_id {signup_id}，原因：找不到點燈收入項目 91）",
                        level="WARN",
                    )
                    raise ValueError("找不到可用的點燈收入項目（91 點燈收入）")
                receipt_number = self.generate_receipt_number(today)
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        str(income_item.get("id") or ""),
                        str(income_item.get("name") or "點燈收入"),
                        int(delta),
                        pid,
                        person_name,
                        handler_text,
                        receipt_number,
                        f"[{int(signup_year)}安燈差額補繳]",
                        "LIGHTING_SIGNUP",
                        signup_id,
                        "SUPPLEMENT",
                        int(base_txn_id) if base_txn_id else None,
                        1,
                    ),
                )
                adjustment_type = "SUPPLEMENT"
            else:
                refund_item = self._resolve_lighting_refund_expense_item()
                if not refund_item:
                    self._log_lighting_system_event(
                        f"安燈報名差額調整失敗（signup_id {signup_id}，原因：找不到安燈退費項目 91R）",
                        level="WARN",
                    )
                    raise ValueError("找不到可用的安燈退費項目（91R 安燈退費）")
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'expense', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        str(refund_item.get("id") or ""),
                        str(refund_item.get("name") or "安燈退費"),
                        int(abs(delta)),
                        pid,
                        person_name,
                        handler_text,
                        None,
                        f"[{int(signup_year)}安燈差額退費]",
                        "LIGHTING_SIGNUP",
                        signup_id,
                        "REFUND",
                        int(base_txn_id) if base_txn_id else None,
                        1,
                    ),
                )
                adjustment_type = "REFUND"

            adjustment_txn_id = cur.lastrowid
            cur.execute("COMMIT;")
        except Exception as e:
            cur.execute("ROLLBACK;")
            self._log_lighting_system_event(
                f"安燈報名差額調整失敗（signup_id {signup_id}，原因：交易回滾 / {e}）",
                level="WARN",
            )
            raise

        self._log_lighting_data_change(
            "LIGHTING.SIGNUP.ADJUST",
            (
                f"安燈報名差額調整完成（signup_id {signup_id}，報名人 {person_name or '-'}（person_id {pid}），"
                f"舊金額 {old_total}，新金額 {new_total}，delta {delta}，"
                f"調整型態 {adjustment_type or '-'}，交易ID {adjustment_txn_id or '-'}，"
                f"收據 {receipt_number or '-'}）"
            ),
        )

        return {
            "signup_id": signup_id,
            "old_total": old_total,
            "new_total": new_total,
            "delta": delta,
            "adjustment_txn_id": int(adjustment_txn_id) if adjustment_txn_id else None,
            "adjustment_type": adjustment_type,
            "receipt_number": receipt_number,
            "is_paid": is_paid,
        }

    def _ensure_system_income_items(self):
        """
        啟動時自動 upsert 系統保留收入項目：
        - 90 活動收入
        - 91 點燈收入
        不存在就建立，存在就略過建立（並同步名稱）。
        """
        if not self._table_exists("income_items"):
            return

        cols = self._table_columns("income_items")
        has_is_active = "is_active" in cols
        cur = self.conn.cursor()
        changed = False

        for item_id, item_name in self.SYSTEM_INCOME_ITEMS:
            row = cur.execute("SELECT id FROM income_items WHERE id = ? LIMIT 1", (item_id,)).fetchone()
            if row:
                if has_is_active:
                    cur.execute("UPDATE income_items SET name = ?, is_active = 1 WHERE id = ?", (item_name, item_id))
                else:
                    cur.execute("UPDATE income_items SET name = ? WHERE id = ?", (item_name, item_id))
                changed = True
            else:
                if has_is_active:
                    cur.execute("INSERT INTO income_items (id, name, amount, is_active) VALUES (?, ?, ?, 1)", (item_id, item_name, 0))
                else:
                    cur.execute("INSERT INTO income_items (id, name, amount) VALUES (?, ?, ?)", (item_id, item_name, 0))
                changed = True
        if changed:
            self.conn.commit()

    def _ensure_system_expense_items(self):
        if not self._table_exists("expense_items"):
            return
        cur = self.conn.cursor()
        changed = False
        for item_id, item_name in self.SYSTEM_EXPENSE_ITEMS:
            row = cur.execute("SELECT id FROM expense_items WHERE id = ? LIMIT 1", (item_id,)).fetchone()
            if row:
                cur.execute("UPDATE expense_items SET name = ? WHERE id = ?", (item_name, item_id))
                changed = True
            else:
                cur.execute("INSERT INTO expense_items (id, name, amount) VALUES (?, ?, ?)", (item_id, item_name, 0))
                changed = True
        if changed:
            self.conn.commit()

    def _ensure_setting(self, key: str, default_value: str):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(default_value), self._now()),
            )

    def get_setting(self, key: str, default_value: str = "") -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row and row[0] is not None else str(default_value)

    def set_setting(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, str(value), self._now()),
        )
        self.conn.commit()

    def get_password_reminder_days(self) -> int:
        try:
            return max(0, int(self.get_setting("security/password_reminder_days", "90")))
        except Exception:
            return 90

    def get_idle_logout_minutes(self) -> int:
        try:
            return max(0, int(self.get_setting("security/idle_logout_minutes", "15")))
        except Exception:
            return 15

    def save_security_settings(self, reminder_days: int, idle_minutes: int):
        old_reminder_days = self.get_password_reminder_days()
        old_idle_minutes = self.get_idle_logout_minutes()
        new_reminder_days = max(0, int(reminder_days))
        new_idle_minutes = max(0, int(idle_minutes))
        self.set_setting("security/password_reminder_days", str(new_reminder_days))
        self.set_setting("security/idle_logout_minutes", str(new_idle_minutes))
        self._log_account_data_change(
            "ACCOUNT.SECURITY_SETTINGS.UPDATE",
            (
                f"更新帳號安全設定（密碼提醒天數：{old_reminder_days} -> {new_reminder_days}；"
                f"閒置自動登出分鐘：{old_idle_minutes} -> {new_idle_minutes}）"
            ),
        )

    def get_login_cover_settings(self) -> Dict[str, str]:
        return {
            "title": self.get_setting("ui/login_cover_title", ""),
            "image_path": self.get_setting("ui/login_cover_image_path", ""),
        }

    def save_login_cover_settings(self, title: str, image_path: str):
        self.set_setting("ui/login_cover_title", (title or "").strip())
        self.set_setting("ui/login_cover_image_path", (image_path or "").strip())

    def get_scheduler_feature_settings(self) -> Dict[str, bool]:
        return {
            "mail_enabled": self.get_setting("scheduler/mail_enabled", "1") == "1",
            "backup_enabled": self.get_setting("scheduler/backup_enabled", "1") == "1",
        }

    def get_scheduler_config_path(self) -> str:
        return (self.get_setting("scheduler/config_path", "app/scheduler/scheduler_config.yaml") or "").strip() or "app/scheduler/scheduler_config.yaml"

    def save_scheduler_config_path(self, path: str):
        before = self.get_scheduler_config_path()
        value = (path or "").strip()
        if not value:
            value = "app/scheduler/scheduler_config.yaml"
        self.set_setting("scheduler/config_path", value)
        self._log_scheduler_data_change(
            "SCHEDULER.CONFIG_PATH.UPDATE",
            (
                "更新排程設定檔路徑（"
                f"舊路徑 {self._fmt_log_val(before)}，"
                f"新路徑 {self._fmt_log_val(value)}）"
            ),
        )

    def get_scheduler_mail_settings(self) -> Dict[str, Any]:
        username = (self.get_setting("scheduler/smtp_username", "") or "").strip()
        secret_error = ""
        pwd_set = False
        try:
            pwd_set = bool(secret_store.has_secret(self.SCHEDULER_SMTP_PASSWORD_SECRET_KEY))
        except Exception as e:
            secret_error = str(e)
            pwd_set = False
        return {
            "smtp_username": username,
            "smtp_password_set": pwd_set,
            "secret_backend": secret_store.backend_label(),
            "secret_error": secret_error,
        }

    def save_scheduler_mail_settings(self, smtp_username: str, smtp_password: str = ""):
        username = (smtp_username or "").strip()
        if not username:
            self._log_scheduler_system_event("儲存排程郵件設定失敗（原因：未輸入 Gmail 帳號）", level="WARN")
            raise ValueError("請輸入 Gmail 帳號。")
        before = self.get_scheduler_mail_settings()
        self.set_setting("scheduler/smtp_username", username)
        password_updated = False
        if (smtp_password or "").strip():
            try:
                secret_store.set_secret(self.SCHEDULER_SMTP_PASSWORD_SECRET_KEY, smtp_password)
                password_updated = True
            except Exception as e:
                self._log_scheduler_system_event(
                    f"儲存排程郵件設定失敗（帳號 {self._fmt_log_val(username)}，原因：無法寫入 {secret_store.backend_label()}：{e}）",
                    level="ERROR",
                )
                raise RuntimeError(f"無法寫入 {secret_store.backend_label()}：{e}")
        self._log_scheduler_data_change(
            "SCHEDULER.MAIL_SETTINGS.UPDATE",
            (
                "更新排程郵件設定（"
                f"舊帳號 {self._fmt_log_val(before.get('smtp_username'))}，"
                f"新帳號 {self._fmt_log_val(username)}，"
                f"密碼更新 {1 if password_updated else 0}，"
                f"密碼保存位置 {self._fmt_log_val(secret_store.backend_label())}）"
            ),
        )

    def get_scheduler_mail_credentials(self) -> Tuple[str, str]:
        username = (self.get_setting("scheduler/smtp_username", "") or "").strip()
        password = ""
        try:
            password = (secret_store.get_secret(self.SCHEDULER_SMTP_PASSWORD_SECRET_KEY) or "").strip()
        except Exception:
            password = ""
        if not username:
            username = (os.environ.get("GMAIL_USER", "") or "").strip()
        if not password:
            password = (os.environ.get("GMAIL_APP_PASSWORD", "") or "").strip()
        return username, password

    def save_scheduler_feature_settings(self, settings: Dict[str, Any]):
        if not isinstance(settings, dict):
            self._log_scheduler_system_event("儲存排程功能設定失敗（原因：settings 非 dict）", level="WARN")
            raise ValueError("settings must be a dict")
        before = self.get_scheduler_feature_settings()
        self.set_setting("scheduler/mail_enabled", "1" if bool(settings.get("mail_enabled", True)) else "0")
        self.set_setting("scheduler/backup_enabled", "1" if bool(settings.get("backup_enabled", True)) else "0")
        after = self.get_scheduler_feature_settings()
        self._log_scheduler_data_change(
            "SCHEDULER.FEATURE_FLAGS.UPDATE",
            (
                "更新排程功能旗標（"
                f"郵件排程：{int(bool(before.get('mail_enabled')))} -> {int(bool(after.get('mail_enabled')))}；"
                f"備份排程：{int(bool(before.get('backup_enabled')))} -> {int(bool(after.get('backup_enabled')))}）"
            ),
        )

    # -------------------------
    # Backup
    # -------------------------
    def get_backup_settings(self) -> Dict[str, Any]:
        def _to_int(v: str, fallback: int) -> int:
            try:
                return int(str(v))
            except Exception:
                return fallback
        drive_credentials_path = (self.get_setting("backup/drive_credentials_path", "") or "").strip()

        return {
            "enabled": self.get_setting("backup/enabled", "0") == "1",
            "frequency": (self.get_setting("backup/frequency", "daily") or "daily").strip().lower(),
            "time": (self.get_setting("backup/time", "23:00") or "23:00").strip(),
            "weekday": max(1, min(7, _to_int(self.get_setting("backup/weekday", "1"), 1))),
            "monthday": max(1, min(31, _to_int(self.get_setting("backup/monthday", "1"), 1))),
            "keep_latest": max(1, _to_int(self.get_setting("backup/keep_latest", "20"), 20)),
            "local_dir": (self.get_setting("backup/local_dir", "") or "").strip(),
            "last_run_at": (self.get_setting("backup/last_run_at", "") or "").strip(),
            "last_scheduled_run_at": (self.get_setting("backup/last_scheduled_run_at", "") or "").strip(),
            "drive_folder_id": (self.get_setting("backup/drive_folder_id", "") or "").strip(),
            "drive_credentials_path": drive_credentials_path,
            "enable_local": self.get_setting("backup/enable_local", "1") == "1",
            "enable_drive": self.get_setting("backup/enable_drive", "0") == "1",
            "use_cli_scheduler": self.get_setting("backup/use_cli_scheduler", "0") == "1",
        }

    def save_backup_settings(self, settings: Dict[str, Any]):
        if not isinstance(settings, dict):
            self._log_backup_system_event("儲存備份設定失敗（原因：settings 非 dict）", level="WARN")
            raise ValueError("settings must be a dict")
        before = self.get_backup_settings()
        self.set_setting("backup/enabled", "1" if bool(settings.get("enabled")) else "0")
        self.set_setting("backup/frequency", str(settings.get("frequency", "daily")).strip().lower())
        self.set_setting("backup/time", str(settings.get("time", "23:00")).strip())
        self.set_setting("backup/weekday", str(max(1, min(7, int(settings.get("weekday", 1))))))
        self.set_setting("backup/monthday", str(max(1, min(31, int(settings.get("monthday", 1))))))
        self.set_setting("backup/keep_latest", str(max(1, int(settings.get("keep_latest", 20)))))
        self.set_setting("backup/local_dir", str(settings.get("local_dir", "")).strip())
        self.set_setting("backup/drive_folder_id", str(settings.get("drive_folder_id", "")).strip())
        cred_path = str(settings.get("drive_credentials_path", "")).strip()
        self.set_setting("backup/drive_credentials_path", cred_path)
        self.set_setting("backup/enable_local", "1" if bool(settings.get("enable_local", True)) else "0")
        self.set_setting("backup/enable_drive", "1" if bool(settings.get("enable_drive", False)) else "0")
        self.set_setting("backup/use_cli_scheduler", "1" if bool(settings.get("use_cli_scheduler")) else "0")
        after = self.get_backup_settings()
        self._log_backup_data_change(
            "BACKUP.SETTINGS.UPDATE",
            (
                "更新備份設定（"
                f"啟用：{int(bool(before.get('enabled')))} -> {int(bool(after.get('enabled')))}；"
                f"頻率：{self._fmt_log_val(before.get('frequency'))} -> {self._fmt_log_val(after.get('frequency'))}；"
                f"時間：{self._fmt_log_val(before.get('time'))} -> {self._fmt_log_val(after.get('time'))}；"
                f"保留數：{self._fmt_log_val(before.get('keep_latest'))} -> {self._fmt_log_val(after.get('keep_latest'))}；"
                f"本機路徑：{self._fmt_log_val(before.get('local_dir'))} -> {self._fmt_log_val(after.get('local_dir'))}；"
                f"啟用本機：{int(bool(before.get('enable_local')))} -> {int(bool(after.get('enable_local')))}；"
                f"啟用Drive：{int(bool(before.get('enable_drive')))} -> {int(bool(after.get('enable_drive')))}；"
                f"CLI排程：{int(bool(before.get('use_cli_scheduler')))} -> {int(bool(after.get('use_cli_scheduler')))}"
                "）"
            ),
        )

    def _default_backup_dir(self) -> str:
        return os.path.join(os.path.dirname(DB_NAME), "backups")

    def _harden_backup_artifact_permissions(self, backup_dir: str, backup_file: str = "") -> None:
        # best-effort: 在支援 chmod 的系統收斂為最小權限
        try:
            if backup_dir and os.path.isdir(backup_dir):
                os.chmod(backup_dir, 0o700)
        except Exception:
            pass
        try:
            if backup_file and os.path.isfile(backup_file):
                os.chmod(backup_file, 0o600)
        except Exception:
            pass

    @staticmethod
    def _drive_scopes() -> List[str]:
        return ["https://www.googleapis.com/auth/drive"]

    @staticmethod
    def _read_valid_fernet_key(raw: str) -> str:
        text = (raw or "").strip()
        if not text:
            return ""
        try:
            Fernet(text.encode("utf-8"))
            return text
        except Exception:
            return ""

    def _get_or_create_cloud_backup_encryption_key(self) -> bytes:
        current = ""
        legacy = ""
        try:
            current = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT))
        except Exception:
            current = ""
        try:
            legacy = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY))
        except Exception:
            legacy = ""

        if current:
            return current.encode("utf-8")

        if legacy:
            try:
                secret_store.set_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT, legacy)
            except Exception:
                pass
            return legacy.encode("utf-8")

        new_key = Fernet.generate_key().decode("utf-8")
        secret_store.set_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT, new_key)
        return new_key.encode("utf-8")

    def _cloud_backup_decrypt_keys(self) -> List[bytes]:
        keys: List[bytes] = []
        for sk in (
            self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT,
            self.BACKUP_CLOUD_ENCRYPTION_KEY_PREVIOUS,
            self.BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY,
        ):
            try:
                k = self._read_valid_fernet_key(secret_store.get_secret(sk))
            except Exception:
                k = ""
            if k:
                kb = k.encode("utf-8")
                if kb not in keys:
                    keys.append(kb)
        return keys

    def get_cloud_backup_encryption_status(self) -> Dict[str, Any]:
        current_key = ""
        previous_key = ""
        legacy_key = ""
        try:
            current_key = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT))
        except Exception:
            current_key = ""
        try:
            previous_key = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_PREVIOUS))
        except Exception:
            previous_key = ""
        try:
            legacy_key = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY))
        except Exception:
            legacy_key = ""
        return {
            "current_set": bool(current_key or legacy_key),
            "previous_set": bool(previous_key),
            "secret_backend": secret_store.backend_label(),
        }

    def rotate_cloud_backup_encryption_key(self) -> Dict[str, Any]:
        old_current = ""
        old_legacy = ""
        try:
            old_current = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT))
        except Exception:
            old_current = ""
        try:
            old_legacy = self._read_valid_fernet_key(secret_store.get_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY))
        except Exception:
            old_legacy = ""
        old_effective = old_current or old_legacy

        new_key = Fernet.generate_key().decode("utf-8")
        if old_effective:
            secret_store.set_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_PREVIOUS, old_effective)
        secret_store.set_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT, new_key)
        try:
            secret_store.delete_secret(self.BACKUP_CLOUD_ENCRYPTION_KEY_LEGACY)
        except Exception:
            pass
        self._log_backup_data_change(
            "BACKUP.CLOUD_KEY.ROTATE",
            f"更新雲端備份加密金鑰（上一版存在：{int(bool(old_effective))}）",
        )
        return self.get_cloud_backup_encryption_status()

    def _encrypt_backup_file_for_drive(self, local_file: str) -> str:
        if not os.path.isfile(local_file):
            raise ValueError(f"找不到本機備份檔：{local_file}")
        key = self._get_or_create_cloud_backup_encryption_key()
        f = Fernet(key)
        with open(local_file, "rb") as src:
            plain = src.read()
        token = f.encrypt(plain)
        enc_path = f"{local_file}.enc"
        with open(enc_path, "wb") as dst:
            dst.write(token)
        self._harden_backup_artifact_permissions(backup_dir=os.path.dirname(enc_path), backup_file=enc_path)
        return enc_path

    def restore_database_from_encrypted_backup(self, encrypted_file: str):
        enc = (encrypted_file or "").strip()
        restore_started_at = self._now()
        pre_restore_logs: List[Tuple[str, str, str, str, int, str]] = []

        # 還原前先保留目前 backup_logs，避免整庫覆蓋後遺失 MANUAL 歷史紀錄
        try:
            if self._table_exists("backup_logs"):
                cur = self.conn.cursor()
                rows = cur.execute(
                    """
                    SELECT created_at, trigger_mode, status, backup_file, file_size_bytes, error_message
                    FROM backup_logs
                    ORDER BY id ASC
                    """
                ).fetchall()
                pre_restore_logs = [
                    (
                        str(r[0] or ""),
                        str(r[1] or ""),
                        str(r[2] or ""),
                        str(r[3] or ""),
                        int(r[4] or 0),
                        str(r[5] or ""),
                    ) for r in rows
                ]
        except Exception:
            pre_restore_logs = []

        if not enc:
            raise ValueError("請選擇加密備份檔（.db.enc）")
        if not os.path.isfile(enc):
            raise ValueError(f"加密備份檔不存在：{enc}")

        keys = self._cloud_backup_decrypt_keys()
        if not keys:
            raise RuntimeError("找不到可用的雲端加密金鑰，請先確認金鑰設定。")

        with open(enc, "rb") as f:
            token = f.read()

        plain = b""
        last_err = None
        for kb in keys:
            try:
                plain = Fernet(kb).decrypt(token)
                break
            except Exception as e:
                last_err = e
        if not plain:
            raise RuntimeError(f"解密失敗，可能是金鑰不相符或檔案毀損：{last_err}")

        temp_db = f"{self.db_path}.restore_tmp.db"
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception:
                pass
        try:
            with open(temp_db, "wb") as out:
                out.write(plain)
            self._harden_backup_artifact_permissions(backup_dir=os.path.dirname(temp_db), backup_file=temp_db)

            src_conn = sqlite3.connect(temp_db)
            try:
                self.conn.commit()
                src_conn.backup(self.conn)
                self.conn.commit()
            finally:
                src_conn.close()
        except Exception as e:
            try:
                self._insert_backup_log(
                    created_at=restore_started_at,
                    trigger_mode="RESTORE",
                    status="FAILED",
                    backup_file=enc,
                    file_size_bytes=0,
                    error_message=str(e),
                )
            except Exception:
                pass
            self._log_backup_system_event(f"還原加密備份失敗（檔案 {self._fmt_log_val(enc)}，原因：{e}）", level="WARN")
            raise
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass

        # 還原後把「還原前」的 backup_logs 合併回來，避免 MANUAL 記錄被舊備份覆蓋掉
        try:
            if pre_restore_logs and self._table_exists("backup_logs"):
                cur = self.conn.cursor()
                existing_rows = cur.execute(
                    """
                    SELECT created_at, trigger_mode, status, backup_file, file_size_bytes, error_message
                    FROM backup_logs
                    """
                ).fetchall()
                existing_set = {
                    (
                        str(r[0] or ""),
                        str(r[1] or ""),
                        str(r[2] or ""),
                        str(r[3] or ""),
                        int(r[4] or 0),
                        str(r[5] or ""),
                    ) for r in existing_rows
                }
                to_insert = [r for r in pre_restore_logs if r not in existing_set]
                if to_insert:
                    cur.executemany(
                        """
                        INSERT INTO backup_logs (created_at, trigger_mode, status, backup_file, file_size_bytes, error_message)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        to_insert,
                    )
                    self.conn.commit()
        except Exception:
            pass

        try:
            self._insert_backup_log(
                created_at=restore_started_at,
                trigger_mode="RESTORE",
                status="SUCCESS",
                backup_file=enc,
                file_size_bytes=os.path.getsize(enc) if os.path.isfile(enc) else 0,
                error_message="",
            )
        except Exception:
            pass
        self._log_backup_data_change("BACKUP.RESTORE.ENCRYPTED.SUCCESS", f"還原加密備份成功（檔案 {self._fmt_log_val(enc)}）")

    def _parse_hhmm(self, hhmm: str) -> Tuple[int, int]:
        s = (hhmm or "").strip()
        m = re.match(r"^(\d{1,2}):(\d{2})$", s)
        if not m:
            return (23, 0)
        h = max(0, min(23, int(m.group(1))))
        mm = max(0, min(59, int(m.group(2))))
        return (h, mm)

    def _insert_backup_log(
        self,
        created_at: str,
        trigger_mode: str,
        status: str,
        backup_file: str = "",
        file_size_bytes: int = 0,
        error_message: str = "",
    ):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO backup_logs (created_at, trigger_mode, status, backup_file, file_size_bytes, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (created_at, trigger_mode, status, backup_file, int(file_size_bytes or 0), error_message or ""),
        )
        self.conn.commit()

    def create_local_backup(self, manual: bool = False, now: Optional[datetime] = None) -> Dict[str, Any]:
        now_dt = now or datetime.now()
        created_at = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        settings = self.get_backup_settings()
        enable_local = bool(settings.get("enable_local"))
        enable_drive = bool(settings.get("enable_drive"))
        if not enable_local and not enable_drive:
            self._log_backup_system_event(
                f"執行備份失敗（trigger {'MANUAL' if manual else 'SCHEDULED'}，原因：未啟用任何備份目的地）",
                level="WARN",
            )
            raise ValueError("請至少啟用一種備份目的地（本機或 Google Drive）")

        return self._create_backup_with_targets(
            manual=manual,
            now=now_dt,
            created_at=created_at,
            settings=settings,
            enable_local=enable_local,
            enable_drive=enable_drive,
        )

    def _compose_backup_log_file_display(
        self,
        local_backup_file: str,
        enable_local: bool,
        enable_drive: bool,
        drive_folder_id: str = "",
        drive_folder_name: str = "",
        drive_file_id: str = "",
        drive_file_name: str = "",
    ) -> str:
        parts = []
        if enable_local and local_backup_file:
            parts.append(f"LOCAL:{local_backup_file}")
        if enable_drive:
            folder = (drive_folder_name or "").strip() or ((drive_folder_id or "").strip() or "(root)")
            file_name = (drive_file_name or "").strip() or ((drive_file_id or "").strip() or "unknown")
            parts.append(f"DRIVE:{folder}/{file_name}")
        return " | ".join(parts) if parts else (local_backup_file or "")

    def _create_backup_with_targets(
        self,
        manual: bool,
        now: datetime,
        created_at: str,
        settings: Dict[str, Any],
        enable_local: bool,
        enable_drive: bool,
    ) -> Dict[str, Any]:
        trigger = "MANUAL" if manual else "SCHEDULED"
        backup_dir = settings["local_dir"] or self._default_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        self._harden_backup_artifact_permissions(backup_dir=backup_dir)

        filename = f"temple_backup_{now.strftime('%Y%m%d_%H%M%S')}.db"
        backup_file = os.path.join(backup_dir, filename)
        drive_upload_file = ""
        drive_display_name = os.path.basename(backup_file)

        try:
            dst_conn = sqlite3.connect(backup_file)
            try:
                self.conn.backup(dst_conn)
            finally:
                dst_conn.close()
            self._harden_backup_artifact_permissions(backup_dir=backup_dir, backup_file=backup_file)

            size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0

            drive_file_id = ""
            drive_folder_name = ""
            if enable_drive:
                drive_upload_file = self._encrypt_backup_file_for_drive(backup_file)
                drive_display_name = os.path.basename(drive_upload_file)
                drive_file_id, drive_folder_name = self._upload_backup_to_drive(
                    drive_upload_file,
                    folder_id=settings.get("drive_folder_id", ""),
                    oauth_client_secret_path=settings.get("drive_credentials_path", ""),
                    keep_latest=int(settings.get("keep_latest", 20)),
                )

            if enable_local:
                self._prune_local_backups(backup_dir, settings["keep_latest"])
            else:
                try:
                    os.remove(backup_file)
                except Exception:
                    pass

            backup_file_display = self._compose_backup_log_file_display(
                local_backup_file=backup_file,
                enable_local=enable_local,
                enable_drive=enable_drive,
                drive_folder_id=settings.get("drive_folder_id", ""),
                drive_folder_name=drive_folder_name,
                drive_file_id=drive_file_id,
                drive_file_name=drive_display_name,
            )
            self._insert_backup_log(created_at, trigger, "SUCCESS", backup_file_display, size, "")
            self._log_backup_data_change(
                "BACKUP.RUN.SUCCESS",
                (
                    f"備份成功（trigger {trigger}，時間 {created_at}，"
                    f"目的地 本機:{int(enable_local)} / Drive:{int(enable_drive)}，"
                    f"檔案 {self._fmt_log_val(backup_file_display)}，大小 {size} bytes）"
                ),
            )
            return {
                "created_at": created_at,
                "status": "SUCCESS",
                "backup_file": backup_file,
                "file_size_bytes": size,
                "drive_file_id": drive_file_id,
            }
        except Exception as e:
            backup_file_display = self._compose_backup_log_file_display(
                local_backup_file=backup_file,
                enable_local=enable_local,
                enable_drive=enable_drive,
                drive_folder_id=settings.get("drive_folder_id", ""),
                drive_folder_name="",
                drive_file_id="",
                drive_file_name=drive_display_name if drive_display_name else (os.path.basename(backup_file) if backup_file else ""),
            )
            self._insert_backup_log(created_at, trigger, "FAILED", backup_file_display, 0, str(e))
            self._log_backup_system_event(
                (
                    f"備份失敗（trigger {trigger}，時間 {created_at}，"
                    f"目的地 本機:{int(enable_local)} / Drive:{int(enable_drive)}，"
                    f"檔案 {self._fmt_log_val(backup_file_display)}，原因：{e}）"
                ),
                level="WARN",
            )
            raise
        finally:
            if drive_upload_file:
                try:
                    os.remove(drive_upload_file)
                except Exception:
                    pass

    def _upload_backup_to_drive(
        self,
        local_file: str,
        folder_id: str,
        oauth_client_secret_path: str,
        keep_latest: int,
    ) -> Tuple[str, str]:
        service = self._build_drive_service_oauth(
            oauth_client_secret_path=oauth_client_secret_path,
            interactive=False,
        )
        body = {"name": os.path.basename(local_file)}
        if folder_id:
            body["parents"] = [folder_id]
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(local_file, mimetype="application/octet-stream", resumable=False)
        res = service.files().create(
            body=body,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        folder_name = ""
        folder_id_clean = (folder_id or "").strip()
        if folder_id_clean:
            try:
                folder_meta = service.files().get(
                    fileId=folder_id_clean,
                    fields="name",
                    supportsAllDrives=True,
                ).execute()
                folder_name = str(folder_meta.get("name") or "")
            except Exception:
                folder_name = ""
        else:
            folder_name = "(root)"

        self._prune_drive_backups(service, folder_id=folder_id, keep_latest=keep_latest)
        return str(res.get("id") or ""), folder_name

    def authorize_google_drive_oauth(self, oauth_client_secret_path: str) -> Dict[str, str]:
        try:
            service = self._build_drive_service_oauth(
                oauth_client_secret_path=(oauth_client_secret_path or "").strip(),
                interactive=True,
            )
            about = service.about().get(fields="user(emailAddress)").execute()
            email = str((about.get("user") or {}).get("emailAddress") or "")
            self._log_backup_data_change(
                "BACKUP.OAUTH.AUTHORIZED",
                f"Google Drive 授權成功（email {self._fmt_log_val(email)}）",
            )
            return {"email": email}
        except Exception as e:
            self._log_backup_system_event(
                f"Google Drive 授權失敗（原因：{e}）",
                level="WARN",
            )
            raise

    def _build_drive_service_oauth(
        self,
        oauth_client_secret_path: str,
        interactive: bool,
    ):
        if not oauth_client_secret_path:
            raise ValueError("請先設定 OAuth credentials.json 路徑")
        if not os.path.isfile(oauth_client_secret_path):
            raise ValueError(f"OAuth 憑證檔不存在：{oauth_client_secret_path}")

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except Exception:
            raise RuntimeError(
                "缺少 Google OAuth 套件，請安裝：pip install google-api-python-client google-auth google-auth-oauthlib"
            )

        creds = None
        try:
            token_json = (secret_store.get_secret(self.BACKUP_DRIVE_OAUTH_TOKEN_SECRET_KEY) or "").strip()
        except Exception:
            token_json = ""
        if token_json:
            try:
                creds = Credentials.from_authorized_user_info(json.loads(token_json), self._drive_scopes())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif interactive:
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_secret_path, self._drive_scopes())
                try:
                    creds = flow.run_local_server(
                        port=0,
                        access_type="offline",
                        prompt="consent",
                        timeout_seconds=180,
                    )
                except Exception as e:
                    raise RuntimeError(f"Google 授權逾時或失敗：{e}")
            else:
                raise ValueError("尚未完成 Google OAuth 授權，請先在資料備份頁按「Google 授權」")

        try:
            secret_store.set_secret(self.BACKUP_DRIVE_OAUTH_TOKEN_SECRET_KEY, creds.to_json())
        except Exception as e:
            raise RuntimeError(f"無法寫入 {secret_store.backend_label()}（Google OAuth Token）：{e}")

        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _prune_drive_backups(self, service, folder_id: str, keep_latest: int):
        keep = max(1, int(keep_latest or 1))
        q = "name contains 'temple_backup_' and (name contains '.db.enc' or name contains '.db') and trashed = false"
        if folder_id:
            q += f" and '{folder_id}' in parents"
        files = []
        page_token = None
        while True:
            resp = service.files().list(
                q=q,
                spaces="drive",
                fields="nextPageToken, files(id,name,createdTime)",
                orderBy="createdTime desc",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=200,
                pageToken=page_token,
            ).execute()
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        for f in files[keep:]:
            service.files().delete(fileId=f["id"], supportsAllDrives=True).execute()

    def _prune_local_backups(self, backup_dir: str, keep_latest: int):
        keep = max(1, int(keep_latest or 1))
        files: List[str] = []
        for name in os.listdir(backup_dir):
            if not name.startswith("temple_backup_") or not name.endswith(".db"):
                continue
            files.append(os.path.join(backup_dir, name))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for p in files[keep:]:
            try:
                os.remove(p)
            except Exception:
                pass

    def list_backup_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        lim = max(1, int(limit or 100))
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, created_at, trigger_mode, status, backup_file, file_size_bytes, error_message
            FROM backup_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        )
        return [dict(r) for r in cur.fetchall()]

    def should_run_scheduled_backup(self, now: Optional[datetime] = None) -> bool:
        s = self.get_backup_settings()
        if not s.get("enabled"):
            return False

        now_dt = now or datetime.now()
        hh, mm = self._parse_hhmm(s.get("time", "23:00"))
        if (now_dt.hour, now_dt.minute) < (hh, mm):
            return False

        freq = (s.get("frequency") or "daily").lower()
        if freq == "weekly" and now_dt.isoweekday() != int(s.get("weekday", 1)):
            return False
        if freq == "monthly" and now_dt.day != int(s.get("monthday", 1)):
            return False

        # 排程判斷只看「排程執行時間」，手動備份不應阻擋自動排程
        last_run_text = s.get("last_scheduled_run_at") or ""
        if not last_run_text:
            return True
        try:
            last_dt = datetime.strptime(last_run_text, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return True

        if freq == "daily":
            return last_dt.date() != now_dt.date()
        if freq == "weekly":
            return last_dt.isocalendar()[:2] != now_dt.isocalendar()[:2]
        if freq == "monthly":
            return (last_dt.year, last_dt.month) != (now_dt.year, now_dt.month)
        return last_dt.date() != now_dt.date()

    def mark_backup_run(self, now: Optional[datetime] = None, scheduled: bool = False):
        dt = now or datetime.now()
        ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        self.set_setting("backup/last_run_at", ts)
        if bool(scheduled):
            self.set_setting("backup/last_scheduled_run_at", ts)

    def run_scheduled_backup_once(self, now: Optional[datetime] = None) -> bool:
        """
        執行一次排程判斷：
        - 若未達條件：回傳 False
        - 若達條件並完成備份：回傳 True
        """
        if not self.should_run_scheduled_backup(now=now):
            self._log_backup_system_event(
                f"排程備份略過（時間 {self._fmt_log_val((now or datetime.now()).strftime('%Y-%m-%d %H:%M:%S'))}，原因：未達觸發條件）",
                level="INFO",
            )
            return False
        self.create_local_backup(manual=False, now=now)
        self.mark_backup_run(now=now, scheduled=True)
        return True

    def log_security_event(self, actor_username: str, action: str, target_username: Optional[str], detail: str = ""):
        cur = self.conn.cursor()
        now = self._now()
        cur.execute(
            """
            INSERT INTO audit_events (
                event_type, actor_username, target_type, target_id, result, reason, detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._map_security_action_to_event_type(action),
                actor_username or "",
                "USER" if (target_username or "") else "SYSTEM",
                target_username or None,
                "SUCCESS",
                "",
                detail or "",
                now,
            ),
        )
        self.conn.commit()

    def list_users(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT username, COALESCE(NULLIF(display_name,''), username) AS display_name,
                   role, COALESCE(is_active, 1) AS is_active,
                   password_changed_at, created_at, last_login_at
            FROM users
            ORDER BY username COLLATE NOCASE ASC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    def _validate_password_policy(self, username: str, password: str):
        username = (username or "").strip()
        password = str(password or "")
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise ValueError(f"password must be at least {self.MIN_PASSWORD_LENGTH} characters")
        if username and password == username:
            raise ValueError("password must not be the same as username")

    def verify_user_password(self, username: str, password: str, require_active: bool = True) -> bool:
        username = (username or "").strip()
        if not username:
            return False
        cur = self.conn.cursor()
        cur.execute(
            "SELECT password_hash, COALESCE(is_active, 1) FROM users WHERE username = ?",
            (username,),
        )
        row = cur.fetchone()
        if not row:
            return False
        if require_active and int(row[1] or 0) != 1:
            return False
        stored_hash = row[0]
        if not stored_hash:
            return False
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        try:
            import bcrypt
            return bool(bcrypt.checkpw(str(password or "").encode("utf-8"), stored_hash))
        except Exception:
            return False

    def create_user_account(self, actor_username: str, username: str, password: str, role: str, display_name: str = ""):
        username = (username or "").strip()
        display_name = (display_name or "").strip()
        role = (role or "").strip()
        if not username:
            self._log_account_system_event("新增帳號失敗（原因：username 為空）", level="WARN")
            raise ValueError("username is required")
        if not display_name:
            self._log_account_system_event(f"新增帳號失敗（帳號 {username}，原因：display_name 為空）", level="WARN")
            raise ValueError("display_name is required")
        try:
            self._validate_password_policy(username, password)
        except Exception as e:
            self._log_account_system_event(
                f"新增帳號失敗（帳號 {username}，原因：密碼政策不符，{e}）",
                level="WARN",
            )
            raise
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if cur.fetchone():
            self._log_account_system_event(f"新增帳號失敗（帳號 {username} 已存在）", level="WARN")
            raise ValueError("username already exists")
        import bcrypt

        try:
            pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            now = self._now()
            cur.execute(
                """
                INSERT INTO users (id, username, display_name, password_hash, role, created_at, updated_at, is_active, password_changed_at, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
                """,
                (self._uuid(), username, display_name, pw_hash, role, now, now, now),
            )
            self.conn.commit()
        except Exception as e:
            self._log_account_system_event(
                f"新增帳號失敗（帳號 {username}，原因：{e}）",
                level="ERROR",
            )
            raise
        self._log_account_data_change(
            "ACCOUNT.USER.CREATE",
            (
                f"新增帳號（操作者 {self._fmt_log_val(actor_username)}，帳號 {username}，姓名 {display_name}，"
                f"角色 {self._fmt_log_val(role)}，狀態 啟用）"
            ),
        )
        self.log_security_event(actor_username, "create_user", username, f"role={role},display_name={display_name}")

    def reset_user_password(self, actor_username: str, target_username: str, new_password: str, mode: str = "manual"):
        target_username = (target_username or "").strip()
        try:
            self._validate_password_policy(target_username, new_password)
        except Exception as e:
            self._log_account_system_event(
                f"重設密碼失敗（目標帳號 {self._fmt_log_val(target_username)}，原因：密碼政策不符，{e}）",
                level="WARN",
            )
            raise
        cur = self.conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=?", (target_username,))
        if not cur.fetchone():
            self._log_account_system_event(
                f"重設密碼失敗（目標帳號 {target_username} 不存在）",
                level="WARN",
            )
            raise ValueError("target user not found")
        import bcrypt

        try:
            pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            now = self._now()
            cur.execute(
                """
                UPDATE users
                SET password_hash=?, password_changed_at=?, updated_at=?
                WHERE username=?
                """,
                (pw_hash, now, now, target_username),
            )
            self.conn.commit()
        except Exception as e:
            self._log_account_system_event(
                f"重設密碼失敗（目標帳號 {target_username}，原因：{e}）",
                level="ERROR",
            )
            raise
        self._log_account_data_change(
            "ACCOUNT.USER.RESET_PASSWORD",
            (
                f"重設帳號密碼（操作者 {self._fmt_log_val(actor_username)}，目標帳號 {target_username}，"
                f"模式 {self._fmt_log_val(mode)}）"
            ),
        )
        self.log_security_event(actor_username, "reset_password", target_username, f"mode={mode}")

    def toggle_user_active(self, actor_username: str, target_username: str, is_active: bool):
        cur = self.conn.cursor()
        cur.execute("SELECT role, COALESCE(is_active,1) FROM users WHERE username=?", (target_username,))
        row = cur.fetchone()
        if not row:
            self._log_account_system_event(
                f"帳號啟用/停用失敗（目標帳號 {self._fmt_log_val(target_username)} 不存在）",
                level="WARN",
            )
            raise ValueError("target user not found")
        target_role = row[0]
        old_active = int(row[1] or 0)
        if not is_active and target_role == "管理員":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='管理員' AND COALESCE(is_active,1)=1")
            active_admin_count = int(cur.fetchone()[0] or 0)
            if active_admin_count <= 1:
                self._log_account_system_event(
                    f"帳號停用失敗（目標帳號 {target_username}，原因：最後一位啟用中的管理員不可停用）",
                    level="WARN",
                )
                raise ValueError("至少需要保留一位啟用中的管理員")
        now = self._now()
        try:
            cur.execute(
                "UPDATE users SET is_active=?, updated_at=? WHERE username=?",
                (1 if is_active else 0, now, target_username),
            )
            self.conn.commit()
        except Exception as e:
            self._log_account_system_event(
                f"帳號啟用/停用失敗（目標帳號 {target_username}，原因：{e}）",
                level="ERROR",
            )
            raise
        self._log_account_data_change(
            "ACCOUNT.USER.TOGGLE_ACTIVE",
            (
                f"帳號狀態變更（操作者 {self._fmt_log_val(actor_username)}，目標帳號 {target_username}，"
                f"角色 {self._fmt_log_val(target_role)}，"
                f"狀態：{'啟用' if old_active == 1 else '停用'} -> {'啟用' if is_active else '停用'}）"
            ),
        )
        action = "enable_user" if is_active else "disable_user"
        self.log_security_event(actor_username, action, target_username, "")

    def delete_user_account(self, actor_username: str, target_username: str):
        target_username = (target_username or "").strip()
        if not target_username:
            self._log_account_system_event("刪除帳號失敗（原因：target user 為空）", level="WARN")
            raise ValueError("target user is required")
        cur = self.conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=?", (target_username,))
        row = cur.fetchone()
        if not row:
            self._log_account_system_event(
                f"刪除帳號失敗（目標帳號 {target_username} 不存在）",
                level="WARN",
            )
            raise ValueError("target user not found")
        target_role = row[0]
        if target_role == "管理員":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='管理員'")
            admin_count = int(cur.fetchone()[0] or 0)
            if admin_count <= 1:
                self._log_account_system_event(
                    f"刪除帳號失敗（目標帳號 {target_username}，原因：最後一位管理員不可刪除）",
                    level="WARN",
                )
                raise ValueError("至少需要保留一位管理員，無法刪除最後一位管理員")
        try:
            cur.execute("DELETE FROM users WHERE username=?", (target_username,))
            self.conn.commit()
        except Exception as e:
            self._log_account_system_event(
                f"刪除帳號失敗（目標帳號 {target_username}，原因：{e}）",
                level="ERROR",
            )
            raise
        self._log_account_data_change(
            "ACCOUNT.USER.DELETE",
            (
                f"刪除帳號（操作者 {self._fmt_log_val(actor_username)}，目標帳號 {target_username}，"
                f"角色 {self._fmt_log_val(target_role)}）"
            ),
        )
        self.log_security_event(actor_username, "delete_user", target_username, "")

    def update_last_login(self, username: str):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET last_login_at=?, updated_at=? WHERE username=?", (self._now(), self._now(), username))
        self.conn.commit()

    def get_password_reminder_message(self, username: str) -> str:
        days_threshold = self.get_password_reminder_days()
        if days_threshold <= 0:
            return ""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COALESCE(password_changed_at, created_at) AS base_time FROM users WHERE username=?",
            (username,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return ""
        try:
            base = datetime.strptime(str(row[0]), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
        days = (datetime.now() - base).days
        if days >= days_threshold:
            return f"提醒：此帳號已 {days} 天未變更密碼。"
        return ""


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
            self._log_people_system_event(
                f"新增戶長失敗（原因：缺少必填欄位，{'; '.join(missing)}）",
                level="WARN",
            )
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
        optional_cols = {"phone_home", "zip_code", "note", "lunar_is_leap", "zodiac"}
        for col in optional_cols:
            v = person_payload.get(col, None)
            if isinstance(v, str):
                v = v.strip()
            if v not in (None, ""):
                data[col] = v
        age_offset = self._derive_age_offset(cleaned_required["birthday_ad"], person_payload.get("age"))
        if age_offset is not None:
            data["age_offset"] = age_offset

        # 3) 寫入 DB
        cur = self.conn.cursor()
        keys = list(data.keys())
        cur.execute(
            f"INSERT INTO people ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            tuple(data[k] for k in keys),
        )
        self.conn.commit()
        self._log_people_data_change(
            "PEOPLE.HOUSEHOLD.CREATE",
            (
                f"新增戶長資料（person_id {person_id}，household_id {household_id}，"
                f"{self._build_people_profile_detail(data)}）"
            ),
        )
        return person_id, household_id

    def create_people(self, household_id: str, person_payload: dict) -> str:
        """
        在指定戶長底下新增成員 (people: role=MEMBER)
        return: person_id
        """

        head_person_id = (household_id or "").strip()
        if not head_person_id:
            self._log_people_system_event("新增戶員失敗（原因：head_person_id 為空）", level="WARN")
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
            (head_person_id,),
        ).fetchone()

        if not row:
            self._log_people_system_event(
                f"新增戶員失敗（head_person_id {head_person_id} 不存在或非 ACTIVE 戶長）",
                level="WARN",
            )
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
            self._log_people_system_event(
                f"新增戶員失敗（head_person_id {head_person_id}，原因：缺少必填欄位）",
                level="WARN",
            )
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
            "zodiac",
        }
        for col in optional_cols:
            v = person_payload.get(col, None)
            if isinstance(v, str):
                v = v.strip()
            if v not in (None, ""):
                data[col] = v
        age_offset = self._derive_age_offset(cleaned_required["birthday_ad"], person_payload.get("age"))
        if age_offset is not None:
            data["age_offset"] = age_offset

        # 4) 寫入 DB
        keys = list(data.keys())
        cur.execute(
            f"INSERT INTO people ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
            tuple(data[k] for k in keys),
        )
        self.conn.commit()
        self._log_people_data_change(
            "PEOPLE.MEMBER.CREATE",
            (
                f"新增戶員資料（person_id {person_id}，household_id {household_id}，"
                f"{self._build_people_profile_detail(data)}）"
            ),
        )

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
            p.age_offset,
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
                "age_offset": r[10],
                "phone_home": r[11],
                "phone_mobile": r[12],
                "address": r[13],
                "note": r[14],
            })
        return [self._apply_effective_age(x) for x in result]


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
            age_offset,
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
                "age_offset": r[11],
                "zodiac": r[12],
                "phone_home": r[13],
                "phone_mobile": r[14],
                "address": r[15],
                "zip_code": r[16],
                "note": r[17],
                "joined_at": r[18],
            })
        return [self._apply_effective_age(x) for x in result]

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
            "age",
            "age_offset",
            "zodiac",
            "phone_home",
            "phone_mobile",
            "address",
            "zip_code",
            "note",
        }
        person_id = (person_id or "").strip()
        if not person_id:
            self._log_people_system_event("修改信眾失敗（原因：person_id 為空）", level="WARN")
            raise ValueError("person_id is required")

        if payload is None or not isinstance(payload, dict):
            self._log_people_system_event(
                f"修改信眾失敗（person_id {person_id}，原因：payload 非 dict）",
                level="WARN",
            )
            raise ValueError("payload must be a dict")

        # 1) 先確認 person 存在（同時拿既有生日，供年齡校正計算）
        cur = self.conn.cursor()
        existing = cur.execute(
            """
            SELECT
                household_id, role_in_household,
                name, gender, birthday_ad, birthday_lunar, lunar_is_leap,
                birth_time, age, age_offset, zodiac, phone_home, phone_mobile,
                address, zip_code, note
            FROM people
            WHERE id = ?
            """,
            (person_id,),
        ).fetchone()
        if not existing:
            self._log_people_system_event(f"修改信眾失敗（person_id {person_id} 不存在）", level="WARN")
            raise ValueError("person not found")
        existing_birthday_ad = existing["birthday_ad"]

        # 2) 過濾出允許更新的欄位
        updates: Dict[str, Any] = {}
        for k, v in payload.items():
            if k not in UPDATABLE_FIELDS:
                continue

            # 統一處理字串
            if isinstance(v, str):
                v = v.strip()

            # 預設空字串視為「不更新」；但電話欄位允許清空
            if v == "" and k not in {"phone_mobile", "phone_home"}:
                continue

            # lunar_is_leap 建議確保是 0/1（但不強制也可）
            if k == "lunar_is_leap" and v not in (None, ""):
                try:
                    v = int(v)
                except Exception:
                    self._log_people_system_event(
                        f"修改信眾失敗（person_id {person_id}，欄位 農曆生日為閏月 格式錯誤）",
                        level="WARN",
                    )
                    raise ValueError("lunar_is_leap must be 0 or 1")
                if v not in (0, 1):
                    self._log_people_system_event(
                        f"修改信眾失敗（person_id {person_id}，欄位 農曆生日為閏月 只允許 0/1）",
                        level="WARN",
                    )
                    raise ValueError("lunar_is_leap must be 0 or 1")

            if k == "age" and v not in (None, ""):
                try:
                    v = int(v)
                except Exception:
                    self._log_people_system_event(
                        f"修改信眾失敗（person_id {person_id}，欄位 年齡 非整數）",
                        level="WARN",
                    )
                    raise ValueError("age must be an integer")
                if v < 0 or v > 150:
                    self._log_people_system_event(
                        f"修改信眾失敗（person_id {person_id}，欄位 年齡 超出範圍）",
                        level="WARN",
                    )
                    raise ValueError("age must be between 0 and 150")
                birthday_for_age = payload.get("birthday_ad", existing_birthday_ad)
                offset = self._derive_age_offset(birthday_for_age, v)
                updates["age_offset"] = 0 if offset is None else int(offset)

            updates[k] = v

        if not updates:
            self._log_people_system_event(f"修改信眾失敗（person_id {person_id} 無可更新欄位）", level="WARN")
            raise ValueError("no updatable fields in payload")

        # 2.5) 電話規則：聯絡電話/手機號碼至少一個有值
        if "phone_mobile" in updates or "phone_home" in updates:
            new_mobile = updates["phone_mobile"] if "phone_mobile" in updates else (existing["phone_mobile"] or "")
            new_home = updates["phone_home"] if "phone_home" in updates else (existing["phone_home"] or "")
            if not str(new_mobile).strip() and not str(new_home).strip():
                self._log_people_system_event(
                    f"修改信眾失敗（person_id {person_id}，原因：聯絡電話與手機號碼不可同時為空）",
                    level="WARN",
                )
                raise ValueError("聯絡電話與手機號碼不可同時為空，請至少保留一個")

        # 3) 組 SQL
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        sql = f"UPDATE people SET {set_clause} WHERE id = ?"

        params = list(updates.values()) + [person_id]
        cur.execute(sql, tuple(params))
        self.conn.commit()
        if cur.rowcount > 0:
            label_map = {
                "name": "姓名",
                "gender": "性別",
                "birthday_ad": "國曆生日",
                "birthday_lunar": "農曆生日",
                "lunar_is_leap": "農曆生日為閏月",
                "birth_time": "出生時辰",
                "age": "年齡",
                "zodiac": "生肖",
                "phone_home": "聯絡電話",
                "phone_mobile": "手機號碼",
                "address": "地址",
                "zip_code": "郵遞區號",
                "note": "備註",
            }
            change_parts = []
            for field in sorted(updates.keys()):
                if field == "age_offset":
                    continue
                old_v = self._fmt_log_val(existing[field])
                new_v = self._fmt_log_val(updates[field])
                if old_v == new_v:
                    continue
                change_parts.append(
                    f"{label_map.get(field, field)}：{old_v} -> {new_v}"
                )
            changes_text = "；".join(change_parts) if change_parts else "欄位值無異動"
            before_profile = {
                "name": existing["name"],
                "gender": existing["gender"],
                "birthday_ad": existing["birthday_ad"],
                "birthday_lunar": existing["birthday_lunar"],
                "lunar_is_leap": existing["lunar_is_leap"],
                "birth_time": existing["birth_time"],
                "phone_mobile": existing["phone_mobile"],
                "phone_home": existing["phone_home"],
                "address": existing["address"],
                "zip_code": existing["zip_code"],
                "age": existing["age"],
                "zodiac": existing["zodiac"],
                "note": existing["note"],
            }
            after_profile = dict(before_profile)
            for field, value in updates.items():
                if field == "age_offset":
                    continue
                after_profile[field] = value
            self._log_people_data_change(
                "PEOPLE.UPDATE",
                (
                    f"修改信眾資料（person_id {person_id}，household_id {existing['household_id']}，"
                    f"角色 {existing['role_in_household']}，變更：{changes_text}；"
                    f"原資料：{self._build_people_profile_detail(before_profile)}；"
                    f"新資料：{self._build_people_profile_detail(after_profile)}）"
                ),
            )

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
            self._log_people_system_event("分戶失敗（原因：member_person_id 為空）", level="WARN")
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
            self._log_people_system_event(f"分戶失敗（person_id {member_person_id} 不存在）", level="WARN")
            raise ValueError("person not found")

        _id, old_household_id, role, status = row

        if role != "MEMBER":
            self._log_people_system_event(f"分戶失敗（person_id {member_person_id} 不是戶員）", level="WARN")
            raise ValueError("only MEMBER can be split to a new household")

        if require_active and status != "ACTIVE":
            self._log_people_system_event(f"分戶失敗（person_id {member_person_id} 非 ACTIVE）", level="WARN")
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
            self._log_people_system_event(
                f"分戶失敗（person_id {member_person_id}，來源戶 {old_household_id} 無戶長）",
                level="WARN",
            )
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
            self._log_people_data_change(
                "PEOPLE.HOUSEHOLD.SPLIT",
                f"分戶完成（person_id {member_person_id}，原戶 {old_household_id}，新戶 {new_household_id}）",
            )

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
            self._log_people_system_event("變更戶長失敗（原因：member_person_id 為空）", level="WARN")
            raise ValueError("member_person_id is required")
        if not target_head_person_id:
            self._log_people_system_event("變更戶長失敗（原因：target_head_person_id 為空）", level="WARN")
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
            self._log_people_system_event(f"變更戶長失敗（member_person_id {member_person_id} 不存在）", level="WARN")
            raise ValueError("member not found")

        if m["role_in_household"] != "MEMBER":
            self._log_people_system_event(f"變更戶長失敗（person_id {member_person_id} 不是戶員）", level="WARN")
            raise ValueError("only MEMBER can be transferred")

        if require_active and m["status"] != "ACTIVE":
            self._log_people_system_event(f"變更戶長失敗（person_id {member_person_id} 非 ACTIVE）", level="WARN")
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
            self._log_people_system_event(
                f"變更戶長失敗（target_head_person_id {target_head_person_id} 不存在或非戶長）",
                level="WARN",
            )
            raise ValueError("target head not found")

        if require_active and t["status"] != "ACTIVE":
            self._log_people_system_event(
                f"變更戶長失敗（target_head_person_id {target_head_person_id} 非 ACTIVE）",
                level="WARN",
            )
            raise ValueError("target head is not ACTIVE")

        target_household_id = t["household_id"]

        if target_household_id == source_household_id:
            self._log_people_system_event(
                f"變更戶長失敗（person_id {member_person_id} 已在目標戶 {target_household_id}）",
                level="WARN",
            )
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
            self._log_people_data_change(
                "PEOPLE.HOUSEHOLD.TRANSFER",
                f"變更戶長完成（person_id {member_person_id}，來源戶 {source_household_id}，目標戶 {target_household_id}，目標戶長 {target_head_person_id}）",
            )
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
            self._log_people_system_event("停用信眾失敗（原因：person_id 為空）", level="WARN")
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
            self._log_people_system_event(f"停用信眾失敗（person_id {person_id} 不存在）", level="WARN")
            raise ValueError("person not found")

        role, status, household_id = row

        # 2) 若已停用，直接回傳 0（你也可以選擇回傳 1 視為 idempotent）
        if status == "INACTIVE":
            return 0

        # 3) 安全：預設不允許停用戶長
        if role == "HEAD" and not allow_head:
            self._log_people_system_event(f"停用信眾失敗（person_id {person_id} 為戶長，不允許直接停用）", level="WARN")
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
        if cur.rowcount > 0:
            self._log_people_data_change(
                "PEOPLE.STATUS.DEACTIVATE",
                f"停用信眾（person_id {person_id}，household_id {household_id}，角色 {role}）",
            )
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
            self._log_people_system_event("刪除戶籍失敗（原因：household_id 為空）", level="WARN")
            raise ValueError("household_id is required")
        if not head_person_id:
            self._log_people_system_event("刪除戶籍失敗（原因：head_person_id 為空）", level="WARN")
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
            self._log_people_system_event(
                f"刪除戶籍失敗（head_person_id {head_person_id} 不存在於 household_id {household_id}）",
                level="WARN",
            )
            raise ValueError("head person not found in this household")

        if require_active and head["status"] != "ACTIVE":
            self._log_people_system_event(
                f"刪除戶籍失敗（head_person_id {head_person_id} 非 ACTIVE）",
                level="WARN",
            )
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
            self._log_people_system_event(
                f"刪除戶籍失敗（household_id {household_id} 尚有 {int(cnt)} 位 ACTIVE 戶員）",
                level="WARN",
            )
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
        if cur.rowcount > 0:
            self._log_people_data_change(
                "PEOPLE.HEAD.DEACTIVATE",
                f"刪除戶籍（停用戶長）（head_person_id {head_person_id}，household_id {household_id}）",
            )
        return cur.rowcount

    def reactivate_person(self, person_id: str) -> int:
        """
        恢復停用的人員（status: INACTIVE -> ACTIVE）
        - MEMBER：可直接恢復
        - HEAD：同戶不得已有另一位 ACTIVE HEAD
        return: rowcount（正常 1；原本已 ACTIVE 會是 0）
        """
        person_id = (person_id or "").strip()
        if not person_id:
            self._log_people_system_event("恢復信眾失敗（原因：person_id 為空）", level="WARN")
            raise ValueError("person_id is required")

        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT household_id, role_in_household, status
            FROM people
            WHERE id = ?
            """,
            (person_id,),
        ).fetchone()
        if not row:
            self._log_people_system_event(f"恢復信眾失敗（person_id {person_id} 不存在）", level="WARN")
            raise ValueError("person not found")

        household_id, role, status = row
        if status == "ACTIVE":
            return 0

        if role == "HEAD":
            active_head_cnt = cur.execute(
                """
                SELECT COUNT(1)
                FROM people
                WHERE household_id = ?
                  AND role_in_household = 'HEAD'
                  AND status = 'ACTIVE'
                """,
                (household_id,),
            ).fetchone()[0]
            if int(active_head_cnt or 0) > 0:
                self._log_people_system_event(
                    f"恢復信眾失敗（person_id {person_id}：同戶已有啟用中的戶長）",
                    level="WARN",
                )
                raise ValueError("此戶已有啟用中的戶長，無法恢復原戶長")
        else:
            active_head_cnt = cur.execute(
                """
                SELECT COUNT(1)
                FROM people
                WHERE household_id = ?
                  AND role_in_household = 'HEAD'
                  AND status = 'ACTIVE'
                """,
                (household_id,),
            ).fetchone()[0]
            if int(active_head_cnt or 0) == 0:
                self._log_people_system_event(
                    f"恢復信眾失敗（person_id {person_id}：同戶無啟用中的戶長）",
                    level="WARN",
                )
                raise ValueError("此戶無啟用中的戶長，請先恢復戶長")

        cur.execute(
            """
            UPDATE people
            SET status = 'ACTIVE'
            WHERE id = ?
              AND status = 'INACTIVE'
            """,
            (person_id,),
        )
        self.conn.commit()
        if cur.rowcount > 0:
            self._log_people_data_change(
                "PEOPLE.STATUS.REACTIVATE",
                f"恢復信眾（person_id {person_id}，household_id {household_id}，角色 {role}）",
            )
        return cur.rowcount

    # -------------------------
    # Activities
    # -------------------------

    ACTIVITY_STATUS_ACTIVE = 1
    ACTIVITY_STATUS_DELETED = 0

    def _activity_id_exists(self, activity_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM activities WHERE id = ? LIMIT 1", (activity_id,))
        return cursor.fetchone() is not None

    def generate_activity_id(self) -> str:
        """產生新 schema 使用的活動 ID（YYYYMMDDHHMMSS）"""
        return generate_activity_id_safe(self._activity_id_exists)

    def insert_activity(self, data: dict):
        """
        相容舊 payload 入口（activity_name/start_date/scheme_rows），
        寫入新 schema：activities + activity_plans。
        """
        activity_id = self.insert_activity_new({
            "name": data.get("activity_name") or data.get("name") or "",
            "activity_start_date": data.get("start_date") or data.get("activity_start_date") or "",
            "activity_end_date": data.get("end_date") or data.get("activity_end_date") or "",
            "note": data.get("content") or data.get("note") or "",
            "status": 1,
        })
        rows = data.get("scheme_rows") or []
        if rows:
            cur = self.conn.cursor()
            now_text = self._now()
            for idx, row in enumerate(rows):
                plan_id = new_plan_id(activity_id)
                cur.execute(
                    """
                    INSERT INTO activity_plans
                    (id, activity_id, name, items, price_type, fixed_price, note, sort_order, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'FIXED', ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        plan_id,
                        activity_id,
                        (row.get("scheme_name") or "").strip(),
                        (row.get("scheme_item") or "").strip(),
                        int(row.get("amount") or 0),
                        "",
                        idx,
                        now_text,
                        now_text,
                    ),
                )
            self.conn.commit()
        return activity_id


    def update_activity(self, activity_id: str, data: dict = None):
        if data is None and isinstance(activity_id, dict):
            data = activity_id
            activity_id = data.get("activity_id") or data.get("id")
        if data is None:
            data = {}

        cursor = self.conn.cursor()
        now_text = self._now()
        cursor.execute(
            """
            UPDATE activities
            SET
                name = ?,
                activity_start_date = ?,
                activity_end_date = ?,
                note = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("name"),
                data.get("activity_start_date"),
                data.get("activity_end_date"),
                data.get("note", ""),
                int(data.get("status", 1)),
                now_text,
                activity_id,
            ),
        )
        self.conn.commit()
        if cursor.rowcount > 0:
            self._log_activity_data_change(
                "ACTIVITY.UPDATE",
                (
                    f"更新活動（activity_id {activity_id}，名稱 {data.get('name') or '-'}，"
                    f"活動日期 {data.get('activity_start_date') or '-'} ~ {data.get('activity_end_date') or '-'}）"
                ),
            )
        else:
            self._log_activity_system_event(
                f"活動更新失敗（activity_id {activity_id} 不存在或已刪除）",
                level="WARN",
            )

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
        軟刪除活動：把 activities.status 設為 -1
        - DB 保留 activities / plans / signups / signup_plans
        - UI 查詢時會排除 status = -1 的資料
        """
        cur = self.conn.cursor()
        now_text = self._now()
        cur.execute("""
            UPDATE activities
            SET status = -1,
                updated_at = ?
            WHERE id = ?
            AND COALESCE(status, 1) != -1
        """, (now_text, activity_id))
        self.conn.commit()
        ok = cur.rowcount > 0
        if ok:
            self._log_activity_data_change(
                "ACTIVITY.DELETE",
                f"刪除活動（軟刪除）（activity_id {activity_id}）",
            )
        else:
            self._log_activity_system_event(
                f"活動刪除失敗（activity_id {activity_id} 不存在或已刪除）",
                level="WARN",
            )
        return ok



    def get_all_activities(self, active_only: bool = False):
        cursor = self.conn.cursor()

        if active_only:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE COALESCE(status, 1) = 1
                ORDER BY activity_start_date DESC, created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE COALESCE(status, 1) != -1
                ORDER BY activity_start_date DESC, created_at DESC
            """)

        return [dict(row) for row in cursor.fetchall()]


    def _period_date_range(self, period_filter: str) -> tuple[Optional[str], Optional[str]]:
        p = (period_filter or "all").strip().lower()
        today = date.today()
        if p == "week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        if p == "month":
            start = today.replace(day=1)
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1, day=1)
            else:
                next_month = start.replace(month=start.month + 1, day=1)
            end = next_month - timedelta(days=1)
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        if p == "next_month":
            this_month_start = today.replace(day=1)
            if this_month_start.month == 12:
                start = this_month_start.replace(year=this_month_start.year + 1, month=1, day=1)
            else:
                start = this_month_start.replace(month=this_month_start.month + 1, day=1)
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1, day=1)
            else:
                next_month = start.replace(month=start.month + 1, day=1)
            end = next_month - timedelta(days=1)
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        return None, None

    def get_activities_for_manage(
        self,
        keyword: str = "",
        period_filter: str = "all",
        include_ended: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict]:
        """
        活動管理頁專用查詢：
        - 預設排除已結束（status=0 或 end_date < today）
        - 可選 period_filter: all/week/month（依活動開始日期）
        - keyword: 名稱 / 起日 / 迄日
        """
        cursor = self.conn.cursor()
        params: List[Any] = []
        query = """
            SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
            FROM activities
            WHERE COALESCE(status, 1) != -1
        """

        if not include_ended:
            query += """
                AND COALESCE(status, 1) != 0
                AND (
                    activity_end_date IS NULL
                    OR TRIM(activity_end_date) = ''
                    OR date(replace(activity_end_date, '/', '-')) IS NULL
                    OR date(replace(activity_end_date, '/', '-')) >= date('now', 'localtime')
                )
            """

        start_d, end_d = self._period_date_range(period_filter)
        if start_date:
            start_d = start_date
        if end_date:
            end_d = end_date

        if start_d and end_d:
            query += """
                AND date(replace(activity_start_date, '/', '-')) BETWEEN ? AND ?
            """
            params.extend([start_d, end_d])
        elif start_d:
            query += """
                AND date(replace(activity_start_date, '/', '-')) >= ?
            """
            params.append(start_d)
        elif end_d:
            query += """
                AND date(replace(activity_start_date, '/', '-')) <= ?
            """
            params.append(end_d)

        kw = (keyword or "").strip()
        if kw:
            like = f"%{kw}%"
            query += """
                AND (name LIKE ? OR activity_start_date LIKE ? OR activity_end_date LIKE ?)
            """
            params.extend([like, like, like])

        query += """
            ORDER BY
                COALESCE(
                    date(replace(activity_start_date, '/', '-')),
                    replace(activity_start_date, '/', '-')
                ) DESC,
                datetime(created_at) DESC
        """
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]


    def search_activities(
        self,
        keyword: str,
        active_only: bool = False,
        period_filter: str = "all",
        include_ended: Optional[bool] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        keyword 搜尋：活動名稱 / 起日 / 迄日
        - active_only=True  : status = 1
        - active_only=False : status != -1
        """
        if include_ended is not None:
            return self.get_activities_for_manage(
                keyword=keyword,
                period_filter=period_filter,
                include_ended=bool(include_ended),
                start_date=start_date,
                end_date=end_date,
            )
        cursor = self.conn.cursor()
        like = f"%{(keyword or '').strip()}%"

        if active_only:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE COALESCE(status, 1) = 1
                AND (name LIKE ? OR activity_start_date LIKE ? OR activity_end_date LIKE ?)
                ORDER BY activity_start_date DESC, created_at DESC
            """, (like, like, like))
        else:
            cursor.execute("""
                SELECT id, name, activity_start_date, activity_end_date, note, status, created_at, updated_at
                FROM activities
                WHERE COALESCE(status, 1) != -1
                AND (name LIKE ? OR activity_start_date LIKE ? OR activity_end_date LIKE ?)
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
            parsed_items = self._parse_plan_items(items)
            display_items = self._format_plan_items(parsed_items)
            raw_items_text = str(items or "").strip()
            if raw_items_text == "[]":
                raw_items_text = ""

            result.append({
                "id": r.get("id"),
                "activity_id": r.get("activity_id"),
                "name": r.get("name") or "",
                "items": display_items or raw_items_text,
                "items_raw": raw_items_text,
                "plan_items": parsed_items,
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
            self._log_activity_system_event(
                f"新增活動方案失敗（activity_id {activity_id}，原因：無法產生唯一方案 ID）",
                level="WARN",
            )
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
        now_text = self._now()
        cursor.execute("""
            INSERT INTO activity_plans
            (id, activity_id, name, items,
             price_type, fixed_price, suggested_price, min_price,
             note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            activity_id,
            name,
            items,
            price_type,
            fixed_price,
            suggested_price,
            min_price,
            note,
            now_text,
            now_text,
        ))

        conn.commit()
        conn.close()
        self._log_activity_data_change(
            "ACTIVITY.PLAN.CREATE",
            (
                f"新增活動方案（plan_id {plan_id}，activity_id {activity_id}，名稱 {name or '-'}，"
                f"計費 {price_type}，固定金額 {fixed_price if fixed_price is not None else '-'}）"
            ),
        )
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
            if isinstance(plan.get("plan_items"), list):
                items = self._serialize_plan_items(plan.get("plan_items") or [])
            else:
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
            set_parts.append("updated_at = ?")
            params.append(self._now())

        if not set_parts:
            self._log_activity_system_event(
                f"更新活動方案失敗（plan_id {plan_id}，原因：schema 無可更新欄位）",
                level="WARN",
            )
            raise RuntimeError("activity_plans schema has no updatable columns")

        sql = f"UPDATE activity_plans SET {', '.join(set_parts)} WHERE id = ?"
        params.append(plan_id)

        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        ok = cur.rowcount > 0
        if ok:
            self._log_activity_data_change(
                "ACTIVITY.PLAN.UPDATE",
                f"更新活動方案（plan_id {plan_id}，名稱 {payload.get('name') or '-'}）",
            )
        else:
            self._log_activity_system_event(
                f"更新活動方案失敗（plan_id {plan_id} 不存在）",
                level="WARN",
            )
        return ok

    def delete_activity_plan(self, plan_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM activity_plans WHERE id = ?", (plan_id,))
        self.conn.commit()
        ok = cursor.rowcount > 0
        if ok:
            self._log_activity_data_change(
                "ACTIVITY.PLAN.DELETE",
                f"刪除活動方案（plan_id {plan_id}）",
            )
        else:
            self._log_activity_system_event(
                f"刪除活動方案失敗（plan_id {plan_id} 不存在）",
                level="WARN",
            )
        return ok

    def _table_columns(self, table: str) -> set[str]:
        """Return a set of column names for a sqlite table."""
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}

    @staticmethod
    def _parse_plan_items(items_raw: Any) -> List[Dict[str, Any]]:
        text = str(items_raw or "").strip()
        if not text:
            return []

        if text.startswith("["):
            try:
                arr = json.loads(text)
                result: List[Dict[str, Any]] = []
                for x in arr or []:
                    name = str((x or {}).get("name", "")).strip()
                    if not name:
                        continue
                    try:
                        qty = int((x or {}).get("qty", 1))
                    except Exception:
                        qty = 1
                    result.append({"name": name, "qty": max(1, qty)})
                return result
            except Exception:
                pass

        parts = re.split(r"[\/、,\n]+", text)
        result: List[Dict[str, Any]] = []
        for p in parts:
            token = p.strip()
            if not token:
                continue
            m = re.match(r"^(.*?)(?:[xX＊*×]\s*(\d+))?$", token)
            if not m:
                continue
            name = (m.group(1) or "").strip()
            if not name:
                continue
            qty = int(m.group(2) or 1)
            result.append({"name": name, "qty": max(1, qty)})
        return result

    @staticmethod
    def _format_plan_items(items: List[Dict[str, Any]]) -> str:
        if not items:
            return ""
        return "、".join([f"{x.get('name','')}×{int(x.get('qty',1) or 1)}" for x in items if x.get("name")])

    @staticmethod
    def _serialize_plan_items(items: List[Dict[str, Any]]) -> str:
        clean: List[Dict[str, Any]] = []
        for x in items or []:
            name = str((x or {}).get("name", "")).strip()
            if not name:
                continue
            try:
                qty = int((x or {}).get("qty", 1))
            except Exception:
                qty = 1
            clean.append({"name": name, "qty": max(1, qty)})
        return json.dumps(clean, ensure_ascii=False)
    
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
        parsed_items = self._parse_plan_items(items)
        raw_items_text = str(items or "").strip()
        if raw_items_text == "[]":
            raw_items_text = ""

        return {
            "id": r.get("id"),
            "activity_id": r.get("activity_id"),
            "name": r.get("name") or "",
            "items": self._format_plan_items(parsed_items) or raw_items_text,
            "items_raw": raw_items_text,
            "plan_items": parsed_items,
            "fee_type": fee_type,
            "amount": amount,
            "note": r.get("note") or "",
            "_raw": r,
        }


    # -------------------------
    # Signups (核心)
    # -------------------------
    def create_activity_signup(
        self,
        activity_id: str,
        person_id: str,
        selected_plans: list,
        note: str = None,
        group_id: str = "",
        signup_kind: str = "INITIAL",
    ) -> str:
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
        kind = str(signup_kind or "INITIAL").strip().upper()
        if kind not in {"INITIAL", "APPEND"}:
            kind = "INITIAL"
        resolved_group_id = str(group_id or "").strip() or signup_id
        now = self._now()
        cursor = self.conn.cursor()
        person_name = self._resolve_person_name(person_id)
        activity_name = self._resolve_activity_name(activity_id)

        try:
            cursor.execute("BEGIN;")

            # 1) insert signup 主檔（total_amount 先 0）
            cursor.execute("""
                INSERT INTO activity_signups (
                    id, activity_id, person_id, group_id, signup_kind, signup_time, note, total_amount, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (signup_id, activity_id, person_id, resolved_group_id, kind, now, note, 0, now, now))

            # 2) 逐筆寫明細 + 計算總額
            total_amount = 0
            plan_log_parts = []

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

                part = f"plan_id {plan_id} qty {qty} line_total {int(line_total)}"
                if amount_override_db is not None:
                    part += f" amount_override {int(amount_override_db)}"
                plan_log_parts.append(part)

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
            self._log_activity_data_change(
                "ACTIVITY.SIGNUP.CREATE",
                (
                    f"新增活動報名（signup_id {signup_id}，activity_id {activity_id}，活動 {activity_name or '-'}，"
                    f"報名人 {person_name or '-'}（person_id {person_id}），group_id {resolved_group_id}，"
                    f"kind {kind}，總金額 {total_amount}，方案筆數 {len(selected_plans or [])}，"
                    f"方案明細：{'；'.join(plan_log_parts) if plan_log_parts else '-'}）"
                ),
            )
            return signup_id

        except Exception as e:
            cursor.execute("ROLLBACK;")
            self._log_activity_system_event(
                f"新增活動報名失敗（activity_id {activity_id}，活動 {activity_name or '-'}，"
                f"報名人 {person_name or '-'}（person_id {person_id}），原因：{e}）",
                level="WARN",
            )
            raise e

    def create_activity_signup_append(self, activity_id: str, person_id: str, selected_plans: list, note: str = None) -> Dict[str, Any]:
        """
        新規則（活動）：
        已繳費後不修改原單，改為新增一筆「追加」紀錄（右側按鈕使用）。
        """
        aid = str(activity_id or "").strip()
        pid = str(person_id or "").strip()
        if not aid or not pid:
            self._log_activity_system_event(
                "新增活動追加報名失敗（原因：activity_id / person_id 為空）",
                level="WARN",
            )
            raise ValueError("activity_id / person_id 為必填")
        cur = self.conn.cursor()
        rows = cur.execute(
            """
            SELECT id, COALESCE(group_id, id) AS group_id
            FROM activity_signups
            WHERE activity_id = ? AND person_id = ?
            ORDER BY
                CASE COALESCE(signup_kind, 'INITIAL')
                  WHEN 'INITIAL' THEN 0
                  WHEN 'APPEND' THEN 1
                  ELSE 9
                END ASC,
                datetime(replace(COALESCE(signup_time, created_at), '/', '-')) ASC,
                datetime(replace(COALESCE(created_at, ''), '/', '-')) ASC,
                id ASC
            """,
            (aid, pid),
        ).fetchall()
        group_id = str(rows[0]["group_id"] or rows[0]["id"] or "").strip() if rows else ""
        signup_kind = "APPEND" if rows else "INITIAL"
        signup_id = self.create_activity_signup(
            activity_id=aid,
            person_id=pid,
            selected_plans=selected_plans,
            note=note,
            group_id=group_id,
            signup_kind=signup_kind,
        )
        self._log_activity_data_change(
            "ACTIVITY.SIGNUP.APPEND",
            (
                f"新增活動追加報名（signup_id {signup_id}，activity_id {aid}，person_id {pid}，"
                f"group_id {(group_id or signup_id)}，kind {signup_kind}）"
            ),
        )
        return {"signup_id": signup_id, "group_id": (group_id or signup_id), "signup_kind": signup_kind}

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


    def get_activity_signups(self, activity_id):
        sql = """
        SELECT
            s.id AS signup_id,
            s.person_id AS person_id,
            COALESCE(s.group_id, s.id) AS group_id,
            COALESCE(s.signup_kind, 'INITIAL') AS signup_kind,
            p.name AS person_name,
            p.phone_mobile AS person_phone,
            p.address AS person_address,
            p.birthday_ad AS person_birthday_ad,
            p.birthday_lunar AS person_birthday_lunar,
            COALESCE(p.lunar_is_leap, 0) AS person_lunar_is_leap,
            s.total_amount,
            COALESCE(s.is_paid, 0) AS is_paid,
            s.paid_at,
            s.payment_receipt_number,
            GROUP_CONCAT(
                CASE
                    WHEN ap.price_type = 'FREE'
                        THEN ap.name || COALESCE(CAST(sp.line_total AS TEXT), '0') || '元'
                    ELSE ap.name || '×' || COALESCE(CAST(sp.qty AS TEXT), '0')
                END,
                '、'
            ) AS plan_summary,
            SUM(CASE WHEN ap.price_type = 'FREE' THEN sp.line_total ELSE 0 END) AS donation_amount
        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        JOIN activity_signup_plans sp ON sp.signup_id = s.id
        JOIN activity_plans ap ON ap.id = sp.plan_id
        WHERE s.activity_id = ?
        GROUP BY s.id
        ORDER BY
            COALESCE(s.group_id, s.id) ASC,
            CASE COALESCE(s.signup_kind, 'INITIAL')
              WHEN 'INITIAL' THEN 0
              WHEN 'APPEND' THEN 1
              ELSE 9
            END ASC,
            datetime(replace(COALESCE(s.signup_time, s.created_at), '/', '-')) ASC,
            datetime(replace(s.created_at, '/', '-')) ASC,
            s.id ASC
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

    def _resolve_activity_income_item(self) -> Optional[Dict[str, Any]]:
        if not self._table_exists("income_items"):
            return None
        cur = self.conn.cursor()
        cols = self._table_columns("income_items")
        has_is_active = "is_active" in cols
        if has_is_active:
            cur.execute(
                "SELECT * FROM income_items WHERE id = ? AND COALESCE(is_active, 1) = 1 LIMIT 1",
                (self.ACTIVITY_INCOME_ITEM_ID,),
            )
        else:
            cur.execute("SELECT * FROM income_items WHERE id = ? LIMIT 1", (self.ACTIVITY_INCOME_ITEM_ID,))
        row = cur.fetchone()
        return dict(row) if row else None

    def _resolve_activity_refund_expense_item(self) -> Optional[Dict[str, Any]]:
        if not self._table_exists("expense_items"):
            return None
        cur = self.conn.cursor()
        row = cur.execute("SELECT * FROM expense_items WHERE id = ? LIMIT 1", (self.ACTIVITY_REFUND_EXPENSE_ITEM_ID,)).fetchone()
        return dict(row) if row else None

    def mark_activity_signups_paid(self, activity_id: str, signup_ids: List[str], handler: str = "") -> Dict[str, Any]:
        aid = (activity_id or "").strip()
        normalized_ids = [str(x).strip() for x in (signup_ids or []) if str(x).strip()]
        if not aid:
            self._log_activity_system_event("活動報名繳費失敗（原因：activity_id 為空）", level="WARN")
            raise ValueError("activity_id is required")
        if not normalized_ids:
            return {"paid_count": 0, "skipped_count": 0, "receipt_numbers": []}
        handler_text = (handler or "").strip()
        if not handler_text:
            self._log_activity_system_event(
                f"活動報名繳費失敗（activity_id {aid}，原因：經手人為空）",
                level="WARN",
            )
            raise ValueError("經手人為必填")

        income_item = self._resolve_activity_income_item()
        if not income_item:
            self._log_activity_system_event(
                f"活動報名繳費失敗（activity_id {aid}，原因：找不到活動收入項目 90）",
                level="WARN",
            )
            raise ValueError("找不到可用的收入項目，請先到類別設定建立收入項目")

        category_id = str(income_item.get("id") or "").strip()
        category_name = str(income_item.get("name") or "活動收入").strip() or "活動收入"
        if not category_id:
            self._log_activity_system_event(
                f"活動報名繳費失敗（activity_id {aid}，原因：收入項目 category_id 缺失）",
                level="WARN",
            )
            raise ValueError("收入項目設定不完整，缺少 category_id")

        cur = self.conn.cursor()
        q_marks = ",".join(["?"] * len(normalized_ids))
        sql = f"""
        SELECT
               s.id AS signup_id,
               s.person_id,
               COALESCE(s.signup_kind, 'INITIAL') AS signup_kind,
               COALESCE(s.total_amount, 0) AS total_amount,
               COALESCE(s.is_paid, 0) AS is_paid,
               p.name AS person_name,
               a.name AS activity_name,
               a.activity_end_date,
               GROUP_CONCAT(
                   CASE
                       WHEN ap.price_type = 'FREE'
                           THEN ap.name || COALESCE(CAST(sp.line_total AS TEXT), '0') || '元'
                       ELSE ap.name || '×' || COALESCE(CAST(sp.qty AS TEXT), '0')
                   END,
                   '、'
               ) AS plan_summary
        FROM activity_signups s
        JOIN people p ON p.id = s.person_id
        JOIN activities a ON a.id = s.activity_id
        LEFT JOIN activity_signup_plans sp ON sp.signup_id = s.id
        LEFT JOIN activity_plans ap ON ap.id = sp.plan_id
        WHERE s.activity_id = ? AND s.id IN ({q_marks})
        GROUP BY s.id
        """
        cur.execute(sql, (aid, *normalized_ids))
        rows = [dict(r) for r in cur.fetchall()]

        if not rows:
            return {"paid_count": 0, "skipped_count": 0, "receipt_numbers": []}

        paid_count = 0
        skipped_count = 0
        receipt_numbers: List[str] = []
        paid_details: List[str] = []
        skipped_details: List[str] = []
        now = self._now()
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            cur.execute("BEGIN;")
            for row in rows:
                if int(row.get("is_paid") or 0) == 1:
                    skipped_count += 1
                    skipped_details.append(
                        f"{str(row.get('person_name') or '-')}（person_id {str(row.get('person_id') or '-')}, signup_id {str(row.get('signup_id') or '-')})"
                    )
                    continue
                signup_kind = str(row.get("signup_kind") or "INITIAL").strip().upper()
                adjustment_kind = "SUPPLEMENT" if signup_kind == "APPEND" else "PRIMARY"

                receipt = self.generate_receipt_number(today)
                plan_summary = str(row.get("plan_summary") or "").strip()
                activity_name = str(row.get("activity_name") or "").strip()
                activity_end_date = str(row.get("activity_end_date") or "").strip()
                activity_label = f"{activity_end_date} {activity_name}".strip() if activity_end_date else activity_name
                note = f"[{activity_label}] {plan_summary}".strip() if plan_summary else f"[{activity_label}]"
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        category_id,
                        category_name,
                        int(row.get("total_amount") or 0),
                        str(row.get("person_id") or ""),
                        str(row.get("person_name") or ""),
                        handler_text,
                        receipt,
                        note,
                        "ACTIVITY_SIGNUP",
                        str(row.get("signup_id") or ""),
                        adjustment_kind,
                        None,
                        1,
                    ),
                )
                txn_id = cur.lastrowid
                cur.execute(
                    """
                    UPDATE activity_signups
                    SET is_paid = 1,
                        paid_at = ?,
                        payment_txn_id = ?,
                        payment_receipt_number = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, int(txn_id or 0), receipt, now, str(row.get("signup_id") or "")),
                )
                paid_count += 1
                receipt_numbers.append(receipt)
                paid_details.append(
                    f"{str(row.get('person_name') or '-')}（person_id {str(row.get('person_id') or '-')}, "
                    f"signup_id {str(row.get('signup_id') or '-')}, kind {signup_kind}, "
                    f"金額 {int(row.get('total_amount') or 0)}, 收據 {receipt}）"
                )

            cur.execute("COMMIT;")
        except Exception:
            cur.execute("ROLLBACK;")
            self._log_activity_system_event(
                f"活動報名繳費失敗（activity_id {aid}，原因：交易回滾）",
                level="WARN",
            )
            raise

        if paid_count > 0:
            activity_name = str(rows[0].get("activity_name") or "").strip() if rows else ""
            self._log_activity_data_change(
                "ACTIVITY.SIGNUP.PAY",
                (
                    f"活動報名繳費完成（activity_id {aid}，活動 {activity_name or '-'}，經手人 {handler_text}，"
                    f"成功 {paid_count} 筆，略過 {skipped_count} 筆，"
                    f"繳費名單：{'；'.join(paid_details) if paid_details else '-'}，"
                    f"已繳費略過：{'；'.join(skipped_details) if skipped_details else '-'}）"
                ),
            )
        elif skipped_count > 0:
            self._log_activity_system_event(
                f"活動報名繳費未處理（activity_id {aid}，全部皆已繳費，略過 {skipped_count} 筆）",
                level="WARN",
            )

        return {
            "paid_count": paid_count,
            "skipped_count": skipped_count,
            "receipt_numbers": receipt_numbers,
        }

    def update_paid_activity_signup_with_adjustment(
        self,
        signup_id: str,
        qty_by_plan_id: dict,
        free_amount_by_plan_id: dict,
        handler: str = "",
    ) -> Dict[str, Any]:
        """
        Phase 3（活動 backend）：
        已繳費活動報名修改後，自動建立差額交易（補繳/退費）。
        - 補繳：income / 90 活動收入
        - 退費：expense / 90R 活動退費
        """
        sid = str(signup_id or "").strip()
        if not sid:
            self._log_activity_system_event("活動報名差額調整失敗（原因：signup_id 為空）", level="WARN")
            raise ValueError("signup_id 為必填")
        handler_text = (handler or "").strip()
        if not handler_text:
            self._log_activity_system_event(
                f"活動報名差額調整失敗（signup_id {sid}，原因：經手人為空）",
                level="WARN",
            )
            raise ValueError("經手人為必填")

        cur = self.conn.cursor()
        existing = cur.execute(
            """
            SELECT
                s.id AS signup_id,
                s.activity_id,
                s.person_id,
                COALESCE(s.total_amount, 0) AS total_amount,
                COALESCE(s.is_paid, 0) AS is_paid,
                s.payment_txn_id,
                p.name AS person_name,
                a.name AS activity_name,
                a.activity_end_date
            FROM activity_signups s
            JOIN people p ON p.id = s.person_id
            LEFT JOIN activities a ON a.id = s.activity_id
            WHERE s.id = ?
            LIMIT 1
            """,
            (sid,),
        ).fetchone()
        if not existing:
            self._log_activity_system_event(
                f"活動報名差額調整失敗（signup_id {sid} 不存在）",
                level="WARN",
            )
            raise ValueError("找不到活動報名資料")

        old_total = int(existing["total_amount"] or 0)
        is_paid = int(existing["is_paid"] or 0) == 1
        base_txn_id = existing["payment_txn_id"]
        person_id = str(existing["person_id"] or "")
        person_name = str(existing["person_name"] or "")
        activity_name = str(existing["activity_name"] or "")
        activity_end_date = str(existing["activity_end_date"] or "")
        activity_label = f"{activity_end_date} {activity_name}".strip() if activity_end_date else activity_name

        ok = self.update_activity_signup_items(sid, qty_by_plan_id or {}, free_amount_by_plan_id or {})
        if not ok:
            self._log_activity_system_event(
                f"活動報名差額調整失敗（signup_id {sid}，原因：報名資料未更新）",
                level="WARN",
            )
            raise ValueError("報名資料未更新")

        updated = cur.execute(
            """
            SELECT COALESCE(total_amount, 0) AS total_amount
            FROM activity_signups
            WHERE id = ?
            LIMIT 1
            """,
            (sid,),
        ).fetchone()
        new_total = int((updated["total_amount"] if updated else 0) or 0)
        delta = new_total - old_total

        if (not is_paid) or delta == 0:
            self._log_activity_data_change(
                "ACTIVITY.SIGNUP.ADJUST",
                (
                    f"活動報名調整（無差額交易）（signup_id {sid}，舊金額 {old_total}，新金額 {new_total}，"
                    f"delta {delta}，is_paid {1 if is_paid else 0}）"
                ),
            )
            return {
                "signup_id": sid,
                "old_total": old_total,
                "new_total": new_total,
                "delta": delta,
                "adjustment_txn_id": None,
                "adjustment_type": None,
                "receipt_number": None,
                "is_paid": is_paid,
            }

        today = datetime.now().strftime("%Y-%m-%d")
        adjustment_txn_id = None
        adjustment_type = None
        receipt_number = None

        try:
            cur.execute("BEGIN;")
            if delta > 0:
                income_item = self._resolve_activity_income_item()
                if not income_item:
                    self._log_activity_system_event(
                        f"活動報名差額調整失敗（signup_id {sid}，原因：找不到活動收入項目 90）",
                        level="WARN",
                    )
                    raise ValueError("找不到可用的活動收入項目（90 活動收入）")
                receipt_number = self.generate_receipt_number(today)
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        str(income_item.get("id") or ""),
                        str(income_item.get("name") or "活動收入"),
                        int(delta),
                        person_id,
                        person_name,
                        handler_text,
                        receipt_number,
                        f"[{activity_label}差額補繳]",
                        "ACTIVITY_SIGNUP",
                        sid,
                        "SUPPLEMENT",
                        int(base_txn_id) if base_txn_id else None,
                        1,
                    ),
                )
                adjustment_type = "SUPPLEMENT"
            else:
                refund_item = self._resolve_activity_refund_expense_item()
                if not refund_item:
                    self._log_activity_system_event(
                        f"活動報名差額調整失敗（signup_id {sid}，原因：找不到活動退費項目 90R）",
                        level="WARN",
                    )
                    raise ValueError("找不到可用的活動退費項目（90R 活動退費）")
                cur.execute(
                    """
                    INSERT INTO transactions (
                        date, type, category_id, category_name, amount,
                        payer_person_id, payer_name, handler, receipt_number, note,
                        source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
                    ) VALUES (?, 'expense', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today,
                        str(refund_item.get("id") or ""),
                        str(refund_item.get("name") or "活動退費"),
                        int(abs(delta)),
                        person_id,
                        person_name,
                        handler_text,
                        None,
                        f"[{activity_label}差額退費]",
                        "ACTIVITY_SIGNUP",
                        sid,
                        "REFUND",
                        int(base_txn_id) if base_txn_id else None,
                        1,
                    ),
                )
                adjustment_type = "REFUND"

            adjustment_txn_id = cur.lastrowid
            cur.execute("COMMIT;")
        except Exception:
            cur.execute("ROLLBACK;")
            self._log_activity_system_event(
                f"活動報名差額調整失敗（signup_id {sid}，原因：交易回滾）",
                level="WARN",
            )
            raise

        self._log_activity_data_change(
            "ACTIVITY.SIGNUP.ADJUST",
            (
                f"活動報名差額調整完成（signup_id {sid}，舊金額 {old_total}，新金額 {new_total}，"
                f"delta {delta}，調整型態 {adjustment_type or '-'}，交易ID {adjustment_txn_id or '-'}，"
                f"收據 {receipt_number or '-'}）"
            ),
        )

        return {
            "signup_id": sid,
            "old_total": old_total,
            "new_total": new_total,
            "delta": delta,
            "adjustment_txn_id": int(adjustment_txn_id) if adjustment_txn_id else None,
            "adjustment_type": adjustment_type,
            "receipt_number": receipt_number,
            "is_paid": is_paid,
        }



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
        row = cur.execute(
            "SELECT COALESCE(is_paid, 0) AS is_paid FROM activity_signups WHERE id = ? LIMIT 1",
            (signup_id,),
        ).fetchone()
        if not row:
            self._log_activity_system_event(
                f"刪除活動報名失敗（signup_id {signup_id} 不存在）",
                level="WARN",
            )
            return False
        if int(row["is_paid"] or 0) == 1:
            self._log_activity_system_event(
                f"刪除活動報名失敗（signup_id {signup_id} 已繳費，不可直接刪除）",
                level="WARN",
            )
            raise ValueError("此筆活動報名已繳費，不可刪除")
        try:
            cur.execute("BEGIN;")
            cur.execute("DELETE FROM activity_signup_plans WHERE signup_id = ?", (signup_id,))
            cur.execute("DELETE FROM activity_signups WHERE id = ?", (signup_id,))
            self.conn.commit()
            ok = cur.rowcount > 0
            if ok:
                self._log_activity_data_change(
                    "ACTIVITY.SIGNUP.DELETE",
                    f"刪除活動報名（signup_id {signup_id}，是否作廢交易 否）",
                )
            return ok
        except Exception:
            self.conn.rollback()
            self._log_activity_system_event(
                f"刪除活動報名失敗（signup_id {signup_id}，原因：交易回滾）",
                level="WARN",
            )
            raise

    def delete_activity_signup_with_void_transactions(self, signup_id: str) -> bool:
        """
        新規則（活動右側）：
        刪除當前選取報名紀錄；若已繳費則將對應交易標記作廢（is_voided=1）。
        不影響其他同 group 紀錄。
        """
        sid = str(signup_id or "").strip()
        if not sid:
            self._log_activity_system_event("刪除活動報名失敗（原因：signup_id 為空）", level="WARN")
            return False
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id, COALESCE(is_paid, 0) AS is_paid FROM activity_signups WHERE id = ? LIMIT 1",
            (sid,),
        ).fetchone()
        if not row:
            self._log_activity_system_event(
                f"刪除活動報名失敗（signup_id {sid} 不存在）",
                level="WARN",
            )
            return False
        try:
            cur.execute("BEGIN;")
            voided = False
            if int(row["is_paid"] or 0) == 1 and self._table_exists("transactions"):
                cols = self._table_columns("transactions")
                if "is_voided" in cols:
                    cur.execute(
                        """
                        UPDATE transactions
                        SET is_voided = 1
                        WHERE (is_deleted = 0 OR is_deleted IS NULL)
                          AND COALESCE(source_type, '') = 'ACTIVITY_SIGNUP'
                          AND COALESCE(source_id, '') = ?
                        """,
                        (sid,),
                    )
                    voided = True
            cur.execute("DELETE FROM activity_signup_plans WHERE signup_id = ?", (sid,))
            cur.execute("DELETE FROM activity_signups WHERE id = ?", (sid,))
            self.conn.commit()
            ok = cur.rowcount > 0
            if ok:
                self._log_activity_data_change(
                    "ACTIVITY.SIGNUP.DELETE",
                    f"刪除活動報名（signup_id {sid}，是否作廢交易 {'是' if voided else '否'}）",
                )
            return ok
        except Exception:
            self.conn.rollback()
            self._log_activity_system_event(
                f"刪除活動報名失敗（signup_id {sid}，原因：交易回滾）",
                level="WARN",
            )
            raise

    def get_activity_signup_id_by_person(self, activity_id: str, person_id: str) -> Optional[str]:
        """
        取得某活動中某人目前的報名單 id（若有）。
        用於覆蓋式重存：先刪舊再存新。
        """
        aid = (activity_id or "").strip()
        pid = (person_id or "").strip()
        if not aid or not pid:
            return None

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM activity_signups
            WHERE activity_id = ? AND person_id = ?
            ORDER BY datetime(replace(COALESCE(signup_time, created_at), '/', '-')) DESC, id DESC
            LIMIT 1
            """,
            (aid, pid),
        )
        row = cur.fetchone()
        if not row:
            return None
        return str(row[0])

    
    def insert_activity_new(self, data: dict) -> str:
        """
        schema: activities
        data: {name, activity_start_date, activity_end_date, note, status}
        return: new activity_id (YYYYMMDDHHMMSS)
        """
        activity_id = generate_activity_id_safe(self._activity_id_exists)
        cursor = self.conn.cursor()
        now_text = self._now()
        cursor.execute("""
            INSERT INTO activities (
                id, name, activity_start_date, activity_end_date,
                note, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            activity_id,
            data.get("name"),
            data.get("activity_start_date"),
            data.get("activity_end_date"),
            data.get("note"),
            int(data.get("status", 1)),
            now_text,
            now_text,
        ))
        self.conn.commit()
        self._log_activity_data_change(
            "ACTIVITY.CREATE",
            (
                f"新增活動（activity_id {activity_id}，名稱 {data.get('name') or '-'}，"
                f"活動日期 {data.get('activity_start_date') or '-'} ~ {data.get('activity_end_date') or '-'}）"
            ),
        )
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
    def get_all_income_items(self, active_only: bool = True):
        cursor = self.conn.cursor()
        has_is_active = False
        try:
            cols = self._table_columns("income_items")
            has_is_active = "is_active" in cols
        except Exception:
            has_is_active = False

        if active_only and has_is_active:
            cursor.execute("""
                SELECT * FROM income_items
                WHERE COALESCE(is_active, 1) = 1
                ORDER BY id
            """)
        else:
            cursor.execute("SELECT * FROM income_items ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_expense_items(self, active_only: bool = True):
        cursor = self.conn.cursor()
        has_is_active = False
        try:
            cols = self._table_columns("expense_items")
            has_is_active = "is_active" in cols
        except Exception:
            has_is_active = False

        if active_only and has_is_active:
            cursor.execute("""
                SELECT * FROM expense_items
                WHERE COALESCE(is_active, 1) = 1
                ORDER BY id
            """)
        else:
            cursor.execute("SELECT * FROM expense_items ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def search_people(self, keyword):
        """
        搜尋信徒（不分戶長或成員），回傳 id, name, phone, address
        供 UI 搜尋並取得 person_id
        """
        keyword = (keyword or "").strip()
        if not keyword:
            return []
        
        cursor = self.conn.cursor()
        kw = f"%{keyword}%"
        cursor.execute("""
            SELECT
                id,
                name,
                gender,
                birthday_ad,
                birthday_lunar,
                birth_time,
                zodiac,
                role_in_household,
                phone_mobile,
                phone_home,
                address,
                note,
                joined_at
            FROM people 
            WHERE status='ACTIVE'
              AND (name LIKE ? OR phone_mobile LIKE ? OR phone_home LIKE ?)
            ORDER BY joined_at DESC
            LIMIT 50
        """, (kw, kw, kw))
        return [dict(row) for row in cursor.fetchall()]

    def search_people_unified_dedup_name_birthday(
        self,
        keyword: str,
        limit: int = 50,
        dedup: bool = True,
    ) -> List[Dict]:
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

        # 2) 去重：name + birthday（優先 birthday_ad，沒有就 birthday_lunar）
        seen = set()
        result = []
        for r in rows:
            pid = r.get("id")
            birthday_key = (r.get("birthday_ad") or r.get("birthday_lunar") or "").strip()
            name_key = (r.get("name") or "").strip()
            dedup_key = (name_key, birthday_key)

            if dedup:
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

            # 3) 統一輸出欄位（活動頁最常用）
            phone_mobile = (r.get("phone_mobile") or "").strip()
            phone_home = (r.get("phone_home") or "").strip()

            result.append({
                "id": pid,
                "name": name_key,
                "gender": (r.get("gender") or "").strip(),
                "role_in_household": (r.get("role_in_household") or "").strip(),
                "phone_mobile": phone_mobile,                 # ✅ 統一活動頁用這個
                "phone_home": phone_home,
                "phone_display": phone_mobile or phone_home,  # ✅ 顯示用（可選）
                "address": (r.get("address") or "").strip(),
                "birthday_ad": (r.get("birthday_ad") or "").strip(),
                "birthday_lunar": (r.get("birthday_lunar") or "").strip(),
                "birth_time": (r.get("birth_time") or "").strip(),
                "zodiac": (r.get("zodiac") or "").strip(),
                "note": (r.get("note") or "").strip(),
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
            self._log_finance_system_event(
                f"收據號碼產生使用 fallback 日期（輸入日期格式異常：{date_str}）",
                level="WARN",
            )
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
            tx_label = self._tx_type_label(data.get("type"))
            self._log_finance_system_event(f"新增{tx_label}失敗（原因：category_id 缺失）", level="WARN")
            raise ValueError("category_id is required")
        if data.get("type") == "income" and not data.get("payer_person_id"):
             self._log_finance_system_event("新增收入資料警示（payer_person_id 未提供）", level="WARN")

        cursor = self.conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO transactions (
                date, type, category_id, category_name, amount, 
                payer_person_id, payer_name, handler, receipt_number, note,
                source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get("note"),
            data.get("source_type"),
            data.get("source_id"),
            data.get("adjustment_kind"),
            data.get("adjusts_txn_id"),
            int(data.get("is_system_generated") or 0),
        ))
            self.conn.commit()
        except Exception as e:
            tx_label = self._tx_type_label(data.get("type"))
            self._log_finance_system_event(f"新增{tx_label}失敗（原因：{e}）", level="ERROR")
            raise
        tx_id = cursor.lastrowid
        tx_type = str(data.get("type") or "").strip().lower()
        action_prefix = "INCOME" if tx_type == "income" else "EXPENSE" if tx_type == "expense" else "TRANSACTION"
        self._log_transaction_change(f"{action_prefix}.CREATE", tx_id, data=data, before=None)
        return tx_id
    
    def get_transactions(self, transaction_type=None, start_date=None, end_date=None, keyword=None, voided_filter="all"):
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
            query += """
                AND (
                    t.payer_name LIKE ?
                    OR COALESCE(p.phone_mobile, '') LIKE ?
                    OR COALESCE(p.phone_home, '') LIKE ?
                    OR t.receipt_number LIKE ?
                    OR t.note LIKE ?
                )
            """
            params.extend([kw, kw, kw, kw, kw])

        cols = self._table_columns("transactions") if self._table_exists("transactions") else []
        if "is_voided" in cols:
            mode = str(voided_filter or "all").strip().lower()
            if mode == "exclude":
                query += " AND COALESCE(t.is_voided, 0) = 0"
            elif mode == "only":
                query += " AND COALESCE(t.is_voided, 0) = 1"
            
        query += " ORDER BY t.date DESC, t.created_at DESC"
        
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def list_transactions_by_source(self, source_type: str, source_id: str) -> List[Dict[str, Any]]:
        """
        依業務來源讀取交易鏈（主收款 / 補繳 / 退費）。
        用於業務頁摘要顯示，不含 UI 視覺分組邏輯。
        """
        stype = str(source_type or "").strip()
        sid = str(source_id or "").strip()
        if not stype or not sid:
            return []
        if not self._table_exists("transactions"):
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.id,
                t.date,
                t.type,
                t.category_id,
                t.category_name,
                t.amount,
                t.payer_person_id,
                t.payer_name,
                t.handler,
                t.receipt_number,
                t.note,
                t.source_type,
                t.source_id,
                t.adjustment_kind,
                t.adjusts_txn_id,
                COALESCE(t.is_system_generated, 0) AS is_system_generated,
                t.created_at
            FROM transactions t
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
              AND COALESCE(t.source_type, '') = ?
              AND COALESCE(t.source_id, '') = ?
            ORDER BY
              CASE COALESCE(t.adjustment_kind, '')
                WHEN 'PRIMARY' THEN 0
                WHEN 'SUPPLEMENT' THEN 1
                WHEN 'REFUND' THEN 2
                ELSE 9
              END ASC,
              t.id ASC
            """,
            (stype, sid),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_income_transactions_by_person(self, person_id: str) -> List[Dict]:
        """依信眾取得添油香（收入）交易紀錄。"""
        cursor = self.conn.cursor()
        cols = self._table_columns("transactions") if self._table_exists("transactions") else []
        sql = """
            SELECT
                t.id,
                t.date,
                t.category_id,
                t.category_name,
                t.amount,
                t.handler,
                t.receipt_number,
                t.note,
                t.source_type,
                t.adjustment_kind
            FROM transactions t
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
              AND t.type = 'income'
              AND t.payer_person_id = ?
        """
        if "is_voided" in cols:
            sql += " AND COALESCE(t.is_voided, 0) = 0"
        sql += " ORDER BY t.date DESC, t.created_at DESC"
        cursor.execute(sql, (person_id,))
        return [dict(row) for row in cursor.fetchall()]

    def _period_expr(self, granularity: str) -> str:
        g = (granularity or "").strip().lower()
        if g == "day":
            return "strftime('%Y/%m/%d', t.date)"
        if g == "week":
            # 以週一作為週起始，period_key 使用該週週一（YYYY-MM-DD）
            return "date(t.date, '-' || ((CAST(strftime('%w', t.date) AS INTEGER) + 6) % 7) || ' days')"
        if g == "month":
            return "strftime('%Y/%m', t.date)"
        if g == "year":
            return "strftime('%Y', t.date)"
        raise ValueError("Unsupported granularity, expected day/week/month/year")

    def get_finance_summary_by_period(
        self,
        granularity: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_category: bool = False,
        transaction_type: Optional[str] = None,
    ) -> List[Dict]:
        cursor = self.conn.cursor()
        period_expr = self._period_expr(granularity)
        if include_category:
            query = """
                SELECT
                    t.category_id AS category_id,
                    t.category_name AS category_name,
                    MIN(t.date) AS period_start,
                    MAX(t.date) AS period_end,
                    COALESCE(SUM(CASE WHEN t.type = 'income' THEN 1 ELSE 0 END), 0) AS income_count,
                    COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income_total,
                    COALESCE(SUM(CASE WHEN t.type = 'expense' THEN 1 ELSE 0 END), 0) AS expense_count,
                    COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense_total
                FROM transactions t
                WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
            """
            cols = self._table_columns("transactions") if self._table_exists("transactions") else []
            if "is_voided" in cols:
                query += " AND COALESCE(t.is_voided, 0) = 0"
            params: List[Any] = []

            if transaction_type in {"income", "expense"}:
                query += " AND t.type = ?"
                params.append(transaction_type)
            if start_date:
                query += " AND t.date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND t.date <= ?"
                params.append(end_date)

            query += """
                GROUP BY t.category_id, t.category_name
                ORDER BY t.category_id ASC
            """
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

        if (granularity or "").strip().lower() == "week":
            period_start_expr = period_expr
            period_end_expr = f"date({period_expr}, '+6 days')"
        else:
            period_start_expr = "MIN(t.date)"
            period_end_expr = "MAX(t.date)"

        query = f"""
            SELECT
                {period_expr} AS period_key,
                {period_start_expr} AS period_start,
                {period_end_expr} AS period_end,
                COALESCE(SUM(CASE WHEN t.type = 'income' THEN 1 ELSE 0 END), 0) AS income_count,
                COALESCE(SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END), 0) AS income_total,
                COALESCE(SUM(CASE WHEN t.type = 'expense' THEN 1 ELSE 0 END), 0) AS expense_count,
                COALESCE(SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END), 0) AS expense_total
            FROM transactions t
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
        """
        cols = self._table_columns("transactions") if self._table_exists("transactions") else []
        if "is_voided" in cols:
            query += " AND COALESCE(t.is_voided, 0) = 0"
        params: List[Any] = []

        if transaction_type in {"income", "expense"}:
            query += " AND t.type = ?"
            params.append(transaction_type)
        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)

        query += f"""
            GROUP BY period_key
            ORDER BY period_key DESC
        """
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def get_finance_detail_for_summary(
        self,
        granularity: str,
        period_key: str,
        transaction_type: str,
        category_id: Optional[str] = None,
    ) -> List[Dict]:
        cursor = self.conn.cursor()
        period_expr = self._period_expr(granularity)
        if transaction_type not in {"income", "expense"}:
            raise ValueError("transaction_type is required and must be income or expense")
        query = f"""
            SELECT t.*
            FROM transactions t
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
              AND {period_expr} = ?
              AND t.type = ?
        """
        cols = self._table_columns("transactions") if self._table_exists("transactions") else []
        if "is_voided" in cols:
            query += " AND COALESCE(t.is_voided, 0) = 0"
        params: List[Any] = [period_key, transaction_type]
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)

        query += " ORDER BY t.date DESC, t.created_at DESC"
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def delete_transaction(self, transaction_id):
        """軟刪除"""
        cursor = self.conn.cursor()
        before = cursor.execute(
            "SELECT * FROM transactions WHERE id=?",
            (transaction_id,),
        ).fetchone()
        if not before:
            self._log_finance_system_event(f"刪除交易失敗（transaction_id {transaction_id} 不存在）", level="WARN")
            return
        if int((before["is_voided"] if "is_voided" in before.keys() else 0) or 0) == 1:
            self._log_finance_system_event(
                f"刪除交易失敗（transaction_id {transaction_id} 已作廢，不可刪除）",
                level="WARN",
            )
            raise ValueError("作廢單據不可刪除")
        try:
            cursor.execute("UPDATE transactions SET is_deleted=1 WHERE id=?", (transaction_id,))
            self.conn.commit()
        except Exception as e:
            self._log_finance_system_event(f"刪除交易失敗（transaction_id {transaction_id}，原因：{e}）", level="ERROR")
            raise
        tx_type = str((before["type"] if before else "") or "").strip().lower()
        action_prefix = "INCOME" if tx_type == "income" else "EXPENSE" if tx_type == "expense" else "TRANSACTION"
        payload = dict(before)
        if tx_type:
            payload["type"] = tx_type
        self._log_transaction_change(f"{action_prefix}.DELETE", transaction_id, data=payload, before=payload)

    def update_transaction(self, transaction_id, data):
        """更新交易紀錄"""
        cursor = self.conn.cursor()
        before = cursor.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not before:
            self._log_finance_system_event(f"修改交易失敗（transaction_id {transaction_id} 不存在）", level="WARN")
            return
        if int((before["is_voided"] if "is_voided" in before.keys() else 0) or 0) == 1:
            self._log_finance_system_event(
                f"修改交易失敗（transaction_id {transaction_id} 已作廢，不可修改）",
                level="WARN",
            )
            raise ValueError("作廢單據不可修改")
        before_payload = dict(before)
        
        # 這裡只允許更新部分欄位，確保資料一致性
        # 注意：如果 user 修改了日期，receipt_number 是否要重算？
        # 目前策略：不重算單號，保留原單號，除非 user 自己想改(但 UI 不開放改單號)
        
        try:
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
        except Exception as e:
            tx_label = self._tx_type_label(data.get("type") or before_payload.get("type"))
            self._log_finance_system_event(f"修改{tx_label}失敗（ID {transaction_id}，原因：{e}）", level="ERROR")
            raise
        tx_type = str(
            data.get("type") or before_payload.get("type")
        ).strip().lower()
        action_prefix = "INCOME" if tx_type == "income" else "EXPENSE" if tx_type == "expense" else "TRANSACTION"
        payload = dict(before_payload)
        payload.update(dict(data or {}))
        if tx_type:
            payload["type"] = tx_type
        self._log_transaction_change(
            f"{action_prefix}.UPDATE",
            transaction_id,
            data=payload,
            before=before_payload,
        )

    def void_transaction(self, transaction_id):
        if not self._table_exists("transactions"):
            raise ValueError("交易資料表不存在")
        cols = self._table_columns("transactions")
        if "is_voided" not in cols:
            raise ValueError("目前資料庫尚未支援作廢欄位（is_voided）")

        cursor = self.conn.cursor()
        row = cursor.execute(
            "SELECT * FROM transactions WHERE id=? AND (is_deleted=0 OR is_deleted IS NULL)",
            (transaction_id,),
        ).fetchone()
        if not row:
            raise ValueError("交易不存在或已刪除")

        tx = dict(row)
        if str(tx.get("type") or "").strip().lower() != "income":
            raise ValueError("僅收入單據可作廢")
        if str(tx.get("category_id") or "").strip() in {"90", "91"}:
            raise ValueError("90/91 收入請回活動或安燈頁處理作廢")
        if int(tx.get("is_voided") or 0) == 1:
            return False

        cursor.execute(
            "UPDATE transactions SET is_voided=1 WHERE id=? AND COALESCE(is_voided,0)=0",
            (transaction_id,),
        )
        self.conn.commit()
        if int(cursor.rowcount or 0) <= 0:
            return False

        after = dict(tx)
        after["is_voided"] = 1
        self._log_transaction_change("INCOME.VOID", transaction_id, data=after, before=tx)
        return True

    # -------------------------
    # Believers (UX Improvements)
    # -------------------------
    def get_all_people(self, status="ACTIVE") -> List[Dict]:
        """列出所有信眾（含戶長與成員）"""
        params = []
        where = []
        if status and status != "ALL":
            where.append("status = ?")
            params.append(status)
        
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        sql = f"SELECT * FROM people {where_sql} ORDER BY joined_at DESC"
        
        cursor = self.conn.cursor()
        cursor.execute(sql, tuple(params))
        return [self._apply_effective_age(dict(row)) for row in cursor.fetchall()]

    def search_people_unified(self, keyword: str) -> List[Dict]:
        """
        搜尋包含關鍵字的姓名、手機或地址，並回傳所有匹配的人員清單
        """
        cursor = self.conn.cursor()
        kw = f"%{keyword}%"
        
        cursor.execute("""
            SELECT * 
            FROM people 
            WHERE status = 'ACTIVE' 
              AND (name LIKE ? OR phone_mobile LIKE ? OR address LIKE ?)
            ORDER BY joined_at DESC
        """, (kw, kw, kw))
        return [self._apply_effective_age(dict(row)) for row in cursor.fetchall()]

    def search_by_any_name(self, keyword: str) -> Tuple[Optional[Dict], List[Dict]]:
        """
        搜尋包含關鍵字的姓名，並回傳該人的戶長資料與所有戶員
        """
        cursor = self.conn.cursor()
        kw = f"%{keyword}%"

        cursor.execute("""
            SELECT household_id
            FROM people
            WHERE status = 'ACTIVE'
              AND (name LIKE ? OR phone_mobile LIKE ? OR address LIKE ?)
            LIMIT 1
        """, (kw, kw, kw))
        row = cursor.fetchone()
        
        if not row:
            return None, []
        
        household_id = row[0]
        
        # 2) 取得該戶的戶長
        cursor.execute("""
            SELECT * FROM people 
            WHERE household_id = ? AND role_in_household = 'HEAD' AND status = 'ACTIVE'
            LIMIT 1
        """, (household_id,))
        head_row = cursor.fetchone()
        head_result = self._apply_effective_age(dict(head_row)) if head_row else None
        
        # 3) 取得該戶的所有成員
        members = self.list_people_by_household(household_id)
        
        return head_result, members

    def get_household_people_by_person_id(self, person_id: str, status: str = "ACTIVE") -> List[Dict]:
        """
        由任一 person_id 取出同 household 的所有成員（含戶長與戶員）。
        用於活動報名：搜尋到任一人後，彈整戶勾選。
        """
        pid = (person_id or "").strip()
        if not pid:
            return []

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT household_id
            FROM people
            WHERE id = ?
            LIMIT 1
            """,
            (pid,),
        )
        row = cursor.fetchone()
        if not row:
            return []

        household_id = (row[0] or "").strip()
        if not household_id:
            return []

        return self.list_people_by_household(household_id, status=status)

    def format_head_data(self, row: Dict) -> Dict:
        """將 DB row 格式化為 UI table 期待的格式 (與 list_household 一致)"""
        # 如果已經是 dict 且包含 household_id，則補齊必要的欄位
        data = dict(row)
        if "household_id" not in data:
            data["household_id"] = data.get("id") # fallback
        
        # 為了解決 update_household_table 期待的 key
        data["head_person_id"] = data.get("id")
        
        # 如果 role_in_household 為 HEAD，則 head_name 就是本人姓名
        if data.get("role_in_household") == "HEAD":
            data["head_name"] = data.get("name")
            
        return data
