# app/controller/app_controller.py
import uuid
import locale
import sqlite3
import json
import re
import os
from typing import Tuple, Optional,  List, Dict, Any

from datetime import datetime, date, timedelta


from PyQt5.QtWidgets import QDialog, QPushButton, QHBoxLayout, QMessageBox
from app.utils.id_utils import generate_activity_id_safe, new_plan_id
from app.config import DB_NAME



class AppController:
    SYSTEM_INCOME_ITEMS = (
        ("90", "活動收入"),
        ("91", "點燈收入"),
    )
    ACTIVITY_INCOME_ITEM_ID = "90"

    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_security_schema()
        self._ensure_backup_schema()
        self._ensure_people_schema()
        self._ensure_activity_signup_schema()
        self._ensure_system_income_items()

    # -------------------------
    # Helpers 
    # -------------------------
    def _uuid(self) -> str:
        return str(uuid.uuid4())
    
    MIN_PASSWORD_LENGTH = 8

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_username TEXT NOT NULL,
                action TEXT NOT NULL,
                target_username TEXT,
                detail TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        if self._table_exists("users"):
            if not self._column_exists("users", "must_change_password"):
                cur.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
            if not self._column_exists("users", "password_changed_at"):
                cur.execute("ALTER TABLE users ADD COLUMN password_changed_at TEXT")
            if not self._column_exists("users", "is_active"):
                cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            if not self._column_exists("users", "updated_at"):
                cur.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
                cur.execute("UPDATE users SET updated_at = ? WHERE updated_at IS NULL", (self._now(),))
            if not self._column_exists("users", "last_login_at"):
                cur.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
        self._ensure_setting("security/password_reminder_days", "90")
        self._ensure_setting("security/idle_logout_minutes", "15")
        self._ensure_setting("ui/login_cover_title", "")
        self._ensure_setting("ui/login_cover_image_path", "")
        self.conn.commit()

    def _ensure_backup_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                trigger_mode TEXT NOT NULL,      -- MANUAL / SCHEDULED
                status TEXT NOT NULL,            -- SUCCESS / FAILED
                backup_file TEXT,
                file_size_bytes INTEGER,
                error_message TEXT
            )
            """
        )
        self._ensure_setting("backup/enabled", "0")
        self._ensure_setting("backup/frequency", "daily")     # daily / weekly / monthly
        self._ensure_setting("backup/time", "23:00")          # HH:MM
        self._ensure_setting("backup/weekday", "1")           # 1=Mon ... 7=Sun
        self._ensure_setting("backup/monthday", "1")          # 1..31
        self._ensure_setting("backup/keep_latest", "20")
        self._ensure_setting("backup/local_dir", "")
        self._ensure_setting("backup/last_run_at", "")
        self._ensure_setting("backup/drive_folder_id", "")    # phase-2 用
        self._ensure_setting("backup/oauth_client_secret_path", "")
        self._ensure_setting("backup/oauth_token_path", "")
        self._ensure_setting("backup/drive_credentials_path", "")  # legacy key
        self._ensure_setting("backup/use_cli_scheduler", "0")
        self._ensure_setting("backup/enable_local", "1")
        self._ensure_setting("backup/enable_drive", "0")
        self.conn.commit()

    def _ensure_people_schema(self):
        if not self._table_exists("people"):
            return
        cur = self.conn.cursor()
        if not self._column_exists("people", "age_offset"):
            cur.execute("ALTER TABLE people ADD COLUMN age_offset INTEGER DEFAULT 0")
            self.conn.commit()

    def _ensure_activity_signup_schema(self):
        if not self._table_exists("activity_signups"):
            return
        cur = self.conn.cursor()
        changed = False
        if not self._column_exists("activity_signups", "is_paid"):
            cur.execute("ALTER TABLE activity_signups ADD COLUMN is_paid INTEGER DEFAULT 0")
            changed = True
        if not self._column_exists("activity_signups", "paid_at"):
            cur.execute("ALTER TABLE activity_signups ADD COLUMN paid_at TEXT")
            changed = True
        if not self._column_exists("activity_signups", "payment_txn_id"):
            cur.execute("ALTER TABLE activity_signups ADD COLUMN payment_txn_id INTEGER")
            changed = True
        if not self._column_exists("activity_signups", "payment_receipt_number"):
            cur.execute("ALTER TABLE activity_signups ADD COLUMN payment_receipt_number TEXT")
            changed = True
        if changed:
            self.conn.commit()

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
        self.set_setting("security/password_reminder_days", str(max(0, int(reminder_days))))
        self.set_setting("security/idle_logout_minutes", str(max(0, int(idle_minutes))))

    def get_login_cover_settings(self) -> Dict[str, str]:
        return {
            "title": self.get_setting("ui/login_cover_title", ""),
            "image_path": self.get_setting("ui/login_cover_image_path", ""),
        }

    def save_login_cover_settings(self, title: str, image_path: str):
        self.set_setting("ui/login_cover_title", (title or "").strip())
        self.set_setting("ui/login_cover_image_path", (image_path or "").strip())

    # -------------------------
    # Backup
    # -------------------------
    def get_backup_settings(self) -> Dict[str, Any]:
        def _to_int(v: str, fallback: int) -> int:
            try:
                return int(str(v))
            except Exception:
                return fallback

        return {
            "enabled": self.get_setting("backup/enabled", "0") == "1",
            "frequency": (self.get_setting("backup/frequency", "daily") or "daily").strip().lower(),
            "time": (self.get_setting("backup/time", "23:00") or "23:00").strip(),
            "weekday": max(1, min(7, _to_int(self.get_setting("backup/weekday", "1"), 1))),
            "monthday": max(1, min(31, _to_int(self.get_setting("backup/monthday", "1"), 1))),
            "keep_latest": max(1, _to_int(self.get_setting("backup/keep_latest", "20"), 20)),
            "local_dir": (self.get_setting("backup/local_dir", "") or "").strip(),
            "last_run_at": (self.get_setting("backup/last_run_at", "") or "").strip(),
            "drive_folder_id": (self.get_setting("backup/drive_folder_id", "") or "").strip(),
            "oauth_client_secret_path": (self.get_setting("backup/oauth_client_secret_path", "") or "").strip(),
            "oauth_token_path": (self.get_setting("backup/oauth_token_path", "") or "").strip(),
            "drive_credentials_path": (self.get_setting("backup/drive_credentials_path", "") or "").strip(),  # legacy read
            "enable_local": self.get_setting("backup/enable_local", "1") == "1",
            "enable_drive": self.get_setting("backup/enable_drive", "0") == "1",
            "use_cli_scheduler": self.get_setting("backup/use_cli_scheduler", "0") == "1",
        }

    def save_backup_settings(self, settings: Dict[str, Any]):
        if not isinstance(settings, dict):
            raise ValueError("settings must be a dict")
        self.set_setting("backup/enabled", "1" if bool(settings.get("enabled")) else "0")
        self.set_setting("backup/frequency", str(settings.get("frequency", "daily")).strip().lower())
        self.set_setting("backup/time", str(settings.get("time", "23:00")).strip())
        self.set_setting("backup/weekday", str(max(1, min(7, int(settings.get("weekday", 1))))))
        self.set_setting("backup/monthday", str(max(1, min(31, int(settings.get("monthday", 1))))))
        self.set_setting("backup/keep_latest", str(max(1, int(settings.get("keep_latest", 20)))))
        self.set_setting("backup/local_dir", str(settings.get("local_dir", "")).strip())
        self.set_setting("backup/drive_folder_id", str(settings.get("drive_folder_id", "")).strip())
        self.set_setting("backup/oauth_client_secret_path", str(settings.get("oauth_client_secret_path", "")).strip())
        self.set_setting("backup/oauth_token_path", str(settings.get("oauth_token_path", "")).strip())
        self.set_setting("backup/drive_credentials_path", str(settings.get("oauth_client_secret_path", "")).strip())  # legacy mirror
        self.set_setting("backup/enable_local", "1" if bool(settings.get("enable_local", True)) else "0")
        self.set_setting("backup/enable_drive", "1" if bool(settings.get("enable_drive", False)) else "0")
        self.set_setting("backup/use_cli_scheduler", "1" if bool(settings.get("use_cli_scheduler")) else "0")

    def _default_backup_dir(self) -> str:
        return os.path.join(os.path.dirname(DB_NAME), "backups")

    def _default_oauth_token_path(self) -> str:
        return os.path.join(os.path.dirname(DB_NAME), "drive_oauth_token.json")

    @staticmethod
    def _drive_scopes() -> List[str]:
        return ["https://www.googleapis.com/auth/drive"]

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

        filename = f"temple_backup_{now.strftime('%Y%m%d_%H%M%S')}.db"
        backup_file = os.path.join(backup_dir, filename)

        try:
            dst_conn = sqlite3.connect(backup_file)
            try:
                self.conn.backup(dst_conn)
            finally:
                dst_conn.close()

            size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0

            drive_file_id = ""
            drive_folder_name = ""
            if enable_drive:
                drive_file_id, drive_folder_name = self._upload_backup_to_drive(
                    backup_file,
                    folder_id=settings.get("drive_folder_id", ""),
                    oauth_client_secret_path=settings.get("oauth_client_secret_path", ""),
                    oauth_token_path=settings.get("oauth_token_path", ""),
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
                drive_file_name=os.path.basename(backup_file),
            )
            self._insert_backup_log(created_at, trigger, "SUCCESS", backup_file_display, size, "")
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
                drive_file_name=os.path.basename(backup_file) if backup_file else "",
            )
            self._insert_backup_log(created_at, trigger, "FAILED", backup_file_display, 0, str(e))
            raise

    def _upload_backup_to_drive(
        self,
        local_file: str,
        folder_id: str,
        oauth_client_secret_path: str,
        oauth_token_path: str,
        keep_latest: int,
    ) -> Tuple[str, str]:
        service = self._build_drive_service_oauth(
            oauth_client_secret_path=oauth_client_secret_path,
            oauth_token_path=oauth_token_path,
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

    def authorize_google_drive_oauth(self, oauth_client_secret_path: str, oauth_token_path: str = "") -> Dict[str, str]:
        token_path = (oauth_token_path or "").strip() or self._default_oauth_token_path()

        service = self._build_drive_service_oauth(
            oauth_client_secret_path=(oauth_client_secret_path or "").strip(),
            oauth_token_path=token_path,
            interactive=True,
        )
        about = service.about().get(fields="user(emailAddress)").execute()
        email = str((about.get("user") or {}).get("emailAddress") or "")
        return {"email": email, "token_path": token_path}

    def _build_drive_service_oauth(
        self,
        oauth_client_secret_path: str,
        oauth_token_path: str,
        interactive: bool,
    ):
        if not oauth_client_secret_path:
            raise ValueError("請先設定 OAuth credentials.json 路徑")
        if not os.path.isfile(oauth_client_secret_path):
            raise ValueError(f"OAuth 憑證檔不存在：{oauth_client_secret_path}")
        if not oauth_token_path:
            raise ValueError("請先設定 OAuth token.json 路徑")

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
        if os.path.isfile(oauth_token_path):
            try:
                creds = Credentials.from_authorized_user_file(oauth_token_path, self._drive_scopes())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif interactive:
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_secret_path, self._drive_scopes())
                creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
            else:
                raise ValueError("尚未完成 Google OAuth 授權，請先在資料備份頁按「Google 授權」")

        os.makedirs(os.path.dirname(os.path.abspath(oauth_token_path)), exist_ok=True)
        with open(oauth_token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def _prune_drive_backups(self, service, folder_id: str, keep_latest: int):
        keep = max(1, int(keep_latest or 1))
        q = "name contains 'temple_backup_' and name contains '.db' and trashed = false"
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

        last_run_text = s.get("last_run_at") or ""
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

    def mark_backup_run(self, now: Optional[datetime] = None):
        dt = now or datetime.now()
        self.set_setting("backup/last_run_at", dt.strftime("%Y-%m-%d %H:%M:%S"))

    def run_scheduled_backup_once(self, now: Optional[datetime] = None) -> bool:
        """
        執行一次排程判斷：
        - 若未達條件：回傳 False
        - 若達條件並完成備份：回傳 True
        """
        if not self.should_run_scheduled_backup(now=now):
            return False
        self.create_local_backup(manual=False, now=now)
        self.mark_backup_run(now=now)
        return True

    def log_security_event(self, actor_username: str, action: str, target_username: Optional[str], detail: str = ""):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO security_logs (actor_username, action, target_username, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (actor_username or "", action or "", target_username, detail or "", self._now()),
        )
        self.conn.commit()

    def list_users(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT username, role, COALESCE(is_active, 1) AS is_active,
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

    def create_user_account(self, actor_username: str, username: str, password: str, role: str):
        username = (username or "").strip()
        role = (role or "").strip()
        if not username:
            raise ValueError("username is required")
        self._validate_password_policy(username, password)
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if cur.fetchone():
            raise ValueError("username already exists")
        import bcrypt

        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        now = self._now()
        cur.execute(
            """
            INSERT INTO users (id, username, password_hash, role, created_at, updated_at, is_active, password_changed_at, must_change_password)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0)
            """,
            (self._uuid(), username, pw_hash, role, now, now, now),
        )
        self.conn.commit()
        self.log_security_event(actor_username, "create_user", username, f"role={role}")

    def reset_user_password(self, actor_username: str, target_username: str, new_password: str, mode: str = "manual"):
        target_username = (target_username or "").strip()
        self._validate_password_policy(target_username, new_password)
        cur = self.conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=?", (target_username,))
        if not cur.fetchone():
            raise ValueError("target user not found")
        import bcrypt

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
        self.log_security_event(actor_username, "reset_password", target_username, f"mode={mode}")

    def toggle_user_active(self, actor_username: str, target_username: str, is_active: bool):
        cur = self.conn.cursor()
        cur.execute("SELECT role, COALESCE(is_active,1) FROM users WHERE username=?", (target_username,))
        row = cur.fetchone()
        if not row:
            raise ValueError("target user not found")
        target_role = row[0]
        if not is_active and target_role == "管理員":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='管理員' AND COALESCE(is_active,1)=1")
            active_admin_count = int(cur.fetchone()[0] or 0)
            if active_admin_count <= 1:
                raise ValueError("至少需要保留一位啟用中的管理員")
        now = self._now()
        cur.execute(
            "UPDATE users SET is_active=?, updated_at=? WHERE username=?",
            (1 if is_active else 0, now, target_username),
        )
        self.conn.commit()
        action = "enable_user" if is_active else "disable_user"
        self.log_security_event(actor_username, action, target_username, "")

    def delete_user_account(self, actor_username: str, target_username: str):
        target_username = (target_username or "").strip()
        if not target_username:
            raise ValueError("target user is required")
        cur = self.conn.cursor()
        cur.execute("SELECT role FROM users WHERE username=?", (target_username,))
        row = cur.fetchone()
        if not row:
            raise ValueError("target user not found")
        target_role = row[0]
        if target_role == "管理員":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='管理員'")
            admin_count = int(cur.fetchone()[0] or 0)
            if admin_count <= 1:
                raise ValueError("至少需要保留一位管理員，無法刪除最後一位管理員")
        cur.execute("DELETE FROM users WHERE username=?", (target_username,))
        self.conn.commit()
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
            raise ValueError("person_id is required")

        if payload is None or not isinstance(payload, dict):
            raise ValueError("payload must be a dict")

        # 1) 先確認 person 存在（同時拿既有生日，供年齡校正計算）
        cur = self.conn.cursor()
        existing = cur.execute(
            "SELECT birthday_ad, phone_home, phone_mobile FROM people WHERE id = ?",
            (person_id,),
        ).fetchone()
        if not existing:
            raise ValueError("person not found")
        existing_birthday_ad = existing[0]

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
                    raise ValueError("lunar_is_leap must be 0 or 1")
                if v not in (0, 1):
                    raise ValueError("lunar_is_leap must be 0 or 1")

            if k == "age" and v not in (None, ""):
                try:
                    v = int(v)
                except Exception:
                    raise ValueError("age must be an integer")
                if v < 0 or v > 150:
                    raise ValueError("age must be between 0 and 150")
                birthday_for_age = payload.get("birthday_ad", existing_birthday_ad)
                offset = self._derive_age_offset(birthday_for_age, v)
                updates["age_offset"] = 0 if offset is None else int(offset)

            updates[k] = v

        if not updates:
            raise ValueError("no updatable fields in payload")

        # 2.5) 電話規則：聯絡電話/手機號碼至少一個有值
        if "phone_mobile" in updates or "phone_home" in updates:
            new_mobile = updates["phone_mobile"] if "phone_mobile" in updates else (existing["phone_mobile"] or "")
            new_home = updates["phone_home"] if "phone_home" in updates else (existing["phone_home"] or "")
            if not str(new_mobile).strip() and not str(new_home).strip():
                raise ValueError("聯絡電話與手機號碼不可同時為空，請至少保留一個")

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

    def reactivate_person(self, person_id: str) -> int:
        """
        恢復停用的人員（status: INACTIVE -> ACTIVE）
        - MEMBER：可直接恢復
        - HEAD：同戶不得已有另一位 ACTIVE HEAD
        return: rowcount（正常 1；原本已 ACTIVE 會是 0）
        """
        person_id = (person_id or "").strip()
        if not person_id:
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

    def _is_legacy_activity_schema(self) -> bool:
        if not self._table_exists("activities"):
            return False
        cols = self._table_columns("activities")
        return {"activity_id", "start_date", "end_date", "scheme_name", "scheme_item", "amount"}.issubset(cols)

    def generate_activity_id(self) -> str:
        """Legacy compatibility: YYYYMMDD-XXX"""
        if not self._is_legacy_activity_schema():
            return generate_activity_id_safe(self._activity_id_exists)
        prefix = datetime.now().strftime("%Y%m%d")
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT activity_id
            FROM activities
            WHERE activity_id LIKE ?
            ORDER BY activity_id DESC
            LIMIT 1
            """,
            (f"{prefix}-%",),
        )
        row = cur.fetchone()
        seq = 1
        if row and row[0]:
            try:
                seq = int(str(row[0]).split("-")[-1]) + 1
            except Exception:
                seq = 1
        return f"{prefix}-{seq:03d}"

    def insert_activity(self, data: dict):
        """Legacy compatibility for tests using old activities schema."""
        if not self._is_legacy_activity_schema():
            activity_id = self.insert_activity_new({
                "name": data.get("activity_name") or data.get("name") or "",
                "activity_start_date": data.get("start_date") or data.get("activity_start_date") or "",
                "activity_end_date": data.get("end_date") or data.get("activity_end_date") or "",
                "note": data.get("content") or data.get("note") or "",
                "status": 1,
            })
            for row in (data.get("scheme_rows") or []):
                self.create_activity_plan(
                    activity_id=activity_id,
                    name=(row.get("scheme_name") or "").strip(),
                    items=(row.get("scheme_item") or "").strip(),
                    fee_type="fixed",
                    amount=int(row.get("amount") or 0),
                    note="",
                )
            return activity_id

        activity_id = self.generate_activity_id()
        name = data.get("activity_name") or ""
        start_date = data.get("start_date") or ""
        end_date = data.get("end_date") or ""
        note = data.get("content") or ""
        scheme_rows = data.get("scheme_rows") or []
        cur = self.conn.cursor()
        for row in scheme_rows:
            cur.execute(
                """
                INSERT INTO activities (
                    id, activity_id, name, start_date, end_date,
                    scheme_name, scheme_item, amount, note, is_closed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    self._uuid(),
                    activity_id,
                    name,
                    start_date,
                    end_date,
                    row.get("scheme_name") or "",
                    row.get("scheme_item") or "",
                    float(row.get("amount") or 0),
                    note,
                ),
            )
        self.conn.commit()
        return activity_id


    def update_activity(self, activity_id: str, data: dict = None):
        # legacy signature support: update_activity(payload_dict)
        if data is None and isinstance(activity_id, dict):
            data = activity_id
            activity_id = data.get("activity_id") or data.get("id")
        if data is None:
            data = {}

        if self._is_legacy_activity_schema():
            target_id = data.get("activity_id") or activity_id
            cur = self.conn.cursor()
            cur.execute("DELETE FROM activities WHERE activity_id = ?", (target_id,))
            rows = data.get("scheme_rows") or []
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO activities (
                        id, activity_id, name, start_date, end_date,
                        scheme_name, scheme_item, amount, note, is_closed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        self._uuid(),
                        target_id,
                        data.get("activity_name") or data.get("name") or "",
                        data.get("start_date") or data.get("activity_start_date") or "",
                        data.get("end_date") or data.get("activity_end_date") or "",
                        row.get("scheme_name") or "",
                        row.get("scheme_item") or "",
                        float(row.get("amount") or 0),
                        data.get("content") or data.get("note") or "",
                    ),
                )
            self.conn.commit()
            return

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
        if self._is_legacy_activity_schema():
            cur = self.conn.cursor()
            cur.execute("DELETE FROM activities WHERE activity_id = ?", (activity_id,))
            self.conn.commit()
            return cur.rowcount > 0

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
        return cur.rowcount > 0



    def get_all_activities(self, active_only: bool = False):
        if self._is_legacy_activity_schema():
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT
                    activity_id,
                    MIN(id) AS id,
                    name,
                    start_date,
                    end_date,
                    note,
                    is_closed,
                    GROUP_CONCAT(scheme_name, '\n') AS scheme_names,
                    GROUP_CONCAT(scheme_item, '\n') AS scheme_items,
                    GROUP_CONCAT(CAST(amount AS TEXT), '\n') AS amounts
                FROM activities
                GROUP BY activity_id, name, start_date, end_date, note, is_closed
                ORDER BY start_date DESC, activity_id DESC
                """
            )
            return [dict(r) for r in cur.fetchall()]

        """
        回傳給 UI：list[dict]
        - active_only=True  : 只回 status = 1（正常活動）
        - active_only=False : 回所有「非刪除」活動（status != -1）
        """
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
        if self._is_legacy_activity_schema():
            cur = self.conn.cursor()
            like = f"%{(keyword or '').strip()}%"
            cur.execute(
                """
                SELECT
                    activity_id,
                    MIN(id) AS id,
                    name,
                    start_date,
                    end_date,
                    note,
                    is_closed,
                    GROUP_CONCAT(scheme_name, '\n') AS scheme_names,
                    GROUP_CONCAT(scheme_item, '\n') AS scheme_items,
                    GROUP_CONCAT(CAST(amount AS TEXT), '\n') AS amounts
                FROM activities
                WHERE name LIKE ? OR start_date LIKE ? OR end_date LIKE ? OR activity_id LIKE ?
                GROUP BY activity_id, name, start_date, end_date, note, is_closed
                ORDER BY start_date DESC, activity_id DESC
                """,
                (like, like, like, like),
            )
            return [dict(r) for r in cur.fetchall()]

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
        if self._is_legacy_activity_schema():
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM activities
                WHERE activity_id = ?
                ORDER BY id ASC
                """,
                (activity_id,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                return {}, []
            first = rows[0]
            basic = {
                "activity_id": first.get("activity_id"),
                "activity_name": first.get("name"),
                "start_date": first.get("start_date"),
                "end_date": first.get("end_date"),
                "content": first.get("note") or "",
            }
            schemes = [
                {
                    "scheme_name": r.get("scheme_name") or "",
                    "scheme_item": r.get("scheme_item") or "",
                    "amount": r.get("amount") or 0,
                }
                for r in rows
            ]
            return basic, schemes

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


    def get_activity_signups(self, activity_id):
        sql = """
        SELECT
            s.id AS signup_id,
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

    def mark_activity_signups_paid(self, activity_id: str, signup_ids: List[str], handler: str = "") -> Dict[str, Any]:
        aid = (activity_id or "").strip()
        normalized_ids = [str(x).strip() for x in (signup_ids or []) if str(x).strip()]
        if not aid:
            raise ValueError("activity_id is required")
        if not normalized_ids:
            return {"paid_count": 0, "skipped_count": 0, "receipt_numbers": []}
        handler_text = (handler or "").strip()
        if not handler_text:
            raise ValueError("經手人為必填")

        income_item = self._resolve_activity_income_item()
        if not income_item:
            raise ValueError("找不到可用的收入項目，請先到類別設定建立收入項目")

        category_id = str(income_item.get("id") or "").strip()
        category_name = str(income_item.get("name") or "活動收入").strip() or "活動收入"
        if not category_id:
            raise ValueError("收入項目設定不完整，缺少 category_id")

        cur = self.conn.cursor()
        q_marks = ",".join(["?"] * len(normalized_ids))
        sql = f"""
        SELECT
               s.id AS signup_id,
               s.person_id,
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
        now = self._now()
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            cur.execute("BEGIN;")
            for row in rows:
                if int(row.get("is_paid") or 0) == 1:
                    skipped_count += 1
                    continue

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
                        payer_person_id, payer_name, handler, receipt_number, note
                    ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?)
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

            cur.execute("COMMIT;")
        except Exception:
            cur.execute("ROLLBACK;")
            raise

        return {
            "paid_count": paid_count,
            "skipped_count": skipped_count,
            "receipt_numbers": receipt_numbers,
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
        try:
            cur.execute("BEGIN;")
            cur.execute("DELETE FROM activity_signup_plans WHERE signup_id = ?", (signup_id,))
            cur.execute("DELETE FROM activity_signups WHERE id = ?", (signup_id,))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception:
            self.conn.rollback()
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

    def get_income_transactions_by_person(self, person_id: str) -> List[Dict]:
        """依信眾取得添油香（收入）交易紀錄。"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.id,
                t.date,
                t.category_id,
                t.category_name,
                t.amount,
                t.handler,
                t.receipt_number,
                t.note
            FROM transactions t
            WHERE (t.is_deleted = 0 OR t.is_deleted IS NULL)
              AND t.type = 'income'
              AND t.payer_person_id = ?
            ORDER BY t.date DESC, t.created_at DESC
            """,
            (person_id,),
        )
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

        cols = self._table_columns("people")
        row = None
        if "household_id" in cols:
            # 1) 先找是否有人的姓名、手機或地址匹配
            cursor.execute("""
                SELECT household_id
                FROM people
                WHERE status = 'ACTIVE'
                  AND (name LIKE ? OR phone_mobile LIKE ? OR address LIKE ?)
                LIMIT 1
            """, (kw, kw, kw))
            row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT hm.household_id
                FROM people p
                JOIN household_members hm ON hm.person_id = p.id
                WHERE (p.name LIKE ? OR p.phone_mobile LIKE ? OR p.address LIKE ?)
                LIMIT 1
            """, (kw, kw, kw))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    """
                    SELECT id
                    FROM households
                    WHERE head_name LIKE ?
                       OR head_phone_home LIKE ?
                       OR head_phone_mobile LIKE ?
                    LIMIT 1
                    """,
                    (kw, kw, kw),
                )
                row = cursor.fetchone()
        
        if not row:
            return None, []
        
        household_id = row[0]

        if "household_id" not in cols:
            cursor.execute("SELECT * FROM households WHERE id = ? LIMIT 1", (household_id,))
            h = cursor.fetchone()
            head = dict(h) if h else None
            members = self.get_household_members(household_id)
            return head, members
        
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

    # -------------------------
    # Legacy household compatibility (for old tests/schema)
    # -------------------------
    def search_households(self, keyword: str):
        cur = self.conn.cursor()
        like = f"%{(keyword or '').strip()}%"
        cur.execute(
            """
            SELECT *
            FROM households
            WHERE head_name LIKE ? OR head_phone_home LIKE ? OR head_phone_mobile LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_household_members(self, household_id):
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT p.*
            FROM household_members hm
            JOIN people p ON p.id = hm.person_id
            WHERE hm.household_id = ?
            ORDER BY hm.id ASC
            """,
            (household_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_household_by_id(self, household_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM households WHERE id = ? LIMIT 1", (household_id,))
        row = cur.fetchone()
        return dict(row) if row else {}

    def household_has_members(self, household_id):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) FROM household_members WHERE household_id = ?", (household_id,))
        return int(cur.fetchone()[0] or 0) > 0

    def delete_household(self, household_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM household_members WHERE household_id = ?", (household_id,))
        cur.execute("DELETE FROM households WHERE id = ?", (household_id,))
        self.conn.commit()

    def insert_household(self, data: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO households (
                head_name, head_gender, head_birthday_ad, head_birthday_lunar, head_birth_time,
                head_age, head_zodiac, head_phone_home, head_phone_mobile, head_email,
                head_address, head_zip_code, head_identity, head_note, head_joined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("head_name"),
                data.get("head_gender"),
                data.get("head_birthday_ad"),
                data.get("head_birthday_lunar"),
                data.get("head_birth_time"),
                data.get("head_age"),
                data.get("head_zodiac"),
                data.get("head_phone_home"),
                data.get("head_phone_mobile"),
                data.get("head_email"),
                data.get("head_address"),
                data.get("head_zip_code"),
                data.get("head_identity"),
                data.get("head_note"),
                data.get("head_joined_at"),
            ),
        )
        self.conn.commit()

    def insert_member(self, data: dict):
        person_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO people (
                id, name, gender, birthday_ad, birthday_lunar, birth_time,
                age, zodiac, phone_home, phone_mobile, email,
                address, zip_code, identity, note, joined_at, lunar_is_leap, id_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                data.get("name"),
                data.get("gender"),
                data.get("birthday_ad"),
                data.get("birthday_lunar"),
                data.get("birth_time"),
                data.get("age"),
                data.get("zodiac"),
                data.get("phone_home"),
                data.get("phone_mobile"),
                data.get("email"),
                data.get("address"),
                data.get("zip_code"),
                data.get("identity"),
                data.get("note"),
                data.get("joined_at"),
                int(data.get("lunar_is_leap") or 0),
                data.get("id_number"),
            ),
        )
        cur.execute(
            "INSERT INTO household_members (household_id, person_id, relationship) VALUES (?, ?, ?)",
            (data.get("household_id"), person_id, "家人"),
        )
        self.conn.commit()

    def get_member_by_id(self, person_id: str):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM people WHERE id = ? LIMIT 1", (person_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_member(self, data: dict):
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE people SET
                name=?, gender=?, birthday_ad=?, birthday_lunar=?, birth_time=?,
                age=?, zodiac=?, phone_home=?, phone_mobile=?, email=?,
                address=?, zip_code=?, identity=?, note=?, joined_at=?,
                lunar_is_leap=?, id_number=?
            WHERE id=?
            """,
            (
                data.get("name"),
                data.get("gender"),
                data.get("birthday_ad"),
                data.get("birthday_lunar"),
                data.get("birth_time"),
                data.get("age"),
                data.get("zodiac"),
                data.get("phone_home"),
                data.get("phone_mobile"),
                data.get("email"),
                data.get("address"),
                data.get("zip_code"),
                data.get("identity"),
                data.get("note"),
                data.get("joined_at"),
                int(data.get("lunar_is_leap") or 0),
                data.get("id_number"),
                data.get("id"),
            ),
        )
        self.conn.commit()

    def delete_member_by_id(self, person_id: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM household_members WHERE person_id = ?", (person_id,))
        cur.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self.conn.commit()

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
