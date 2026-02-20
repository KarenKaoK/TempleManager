import sqlite3
import bcrypt
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5 import QtWidgets
from app.dialogs.login_ui import Ui_Dialog  
from app.config import DB_NAME
from datetime import datetime
from uuid import uuid4

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)



class LoginDialog(QDialog):
    """登入視窗"""
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # 設定按鈕事件
        self.ui.pushButtonLogin.clicked.connect(self.check_login)
        self.ui.pushButtonCancel.clicked.connect(self.reject)

        # 初始化登入結果
        self.username = None
        self.role = None
        self._ensure_admin_bootstrap()

    def _column_exists(self, conn, table, column):
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            rows = cur.fetchall() or []
            return any(r[1] == column for r in rows)
        except Exception:
            return False

    def _get_password_reminder_days(self, conn):
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM app_settings WHERE key='security/password_reminder_days'"
            )
            row = cur.fetchone()
        except Exception:
            return 90
        try:
            return int(row[0]) if row else 90
        except Exception:
            return 90

    def _build_password_reminder(self, conn, password_changed_at, created_at):
        reminder_days = self._get_password_reminder_days(conn)
        if reminder_days <= 0:
            return ""
        base = password_changed_at or created_at
        if not base:
            return ""
        try:
            dt = datetime.strptime(str(base), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
        used_days = (datetime.now() - dt).days
        if used_days >= reminder_days:
            return f"\n提醒：此帳號已 {used_days} 天未變更密碼。"
        return ""

    def _has_admin_user(self, conn):
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE role IN ('管理員', '管理者')
                  AND COALESCE(is_active, 1) = 1
                """
            )
            return int(cur.fetchone()[0] or 0) > 0
        except Exception:
            # 測試或舊環境尚未建表時，不阻擋登入視窗初始化
            return True

    def _insert_admin_user(self, conn, username: str, password: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cols = []
        vals = []

        def add(col, val):
            cols.append(col)
            vals.append(val)

        table_cols = []
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        for r in cur.fetchall():
            table_cols.append(r[1])

        add("id", str(uuid4()))
        add("username", username)
        add("password_hash", pw_hash)
        add("role", "管理員")
        if "is_active" in table_cols:
            add("is_active", 1)
        if "must_change_password" in table_cols:
            add("must_change_password", 0)
        if "password_changed_at" in table_cols:
            add("password_changed_at", now)
        if "created_at" in table_cols:
            add("created_at", now)
        if "updated_at" in table_cols:
            add("updated_at", now)

        placeholders = ", ".join(["?"] * len(cols))
        col_sql = ", ".join(cols)
        cur.execute(f"INSERT INTO users ({col_sql}) VALUES ({placeholders})", tuple(vals))
        conn.commit()

    def _ensure_admin_bootstrap(self):
        conn = sqlite3.connect(DB_NAME)
        try:
            if self._has_admin_user(conn):
                return
            QMessageBox.information(
                self,
                "首次初始化",
                "尚未建立管理員帳號，請先完成建立。",
            )
            while True:
                username, ok = QtWidgets.QInputDialog.getText(self, "建立管理員", "管理員帳號")
                if not ok:
                    self.reject()
                    return
                username = (username or "").strip()
                if not username:
                    QMessageBox.warning(self, "錯誤", "帳號不可空白")
                    continue

                password, ok = QtWidgets.QInputDialog.getText(
                    self, "建立管理員", "管理員密碼", QtWidgets.QLineEdit.Password
                )
                if not ok:
                    self.reject()
                    return
                if len(password or "") < 4:
                    QMessageBox.warning(self, "錯誤", "密碼至少 4 碼")
                    continue

                confirm, ok = QtWidgets.QInputDialog.getText(
                    self, "建立管理員", "確認密碼", QtWidgets.QLineEdit.Password
                )
                if not ok:
                    self.reject()
                    return
                if password != confirm:
                    QMessageBox.warning(self, "錯誤", "兩次密碼不一致")
                    continue

                cur = conn.cursor()
                cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
                if cur.fetchone():
                    QMessageBox.warning(self, "錯誤", "帳號已存在，請更換")
                    continue

                self._insert_admin_user(conn, username, password)
                QMessageBox.information(self, "成功", "管理員帳號建立完成，請使用新帳號登入。")
                return
        finally:
            conn.close()

    def check_login(self):
        """驗證帳號密碼並設定登入資訊"""
        username = self.ui.lineEditUsername.text()
        password = self.ui.lineEditPassword.text()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        has_active = self._column_exists(conn, "users", "is_active")
        has_pwd_changed = self._column_exists(conn, "users", "password_changed_at")
        has_last_login = self._column_exists(conn, "users", "last_login_at")
        has_created = self._column_exists(conn, "users", "created_at")

        select_fields = ["password_hash", "role"]
        select_fields.append("created_at" if has_created else "CURRENT_TIMESTAMP AS created_at")
        if has_active:
            select_fields.append("is_active")
        if has_pwd_changed:
            select_fields.append("password_changed_at")
        cursor.execute(f"SELECT {', '.join(select_fields)} FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user:
            stored_hash = user[0]
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode("utf-8")

            if bcrypt.checkpw(password.encode(), stored_hash):
                created_at = user[2] if len(user) > 2 else None
                idx = 3
                is_active = 1
                if has_active and len(user) > idx:
                    is_active = user[idx]
                    idx += 1
                password_changed_at = None
                if has_pwd_changed and len(user) > idx:
                    password_changed_at = user[idx]
                if has_active and int(is_active or 0) != 1:
                    conn.close()
                    QMessageBox.warning(self, "登入失敗", "此帳號已停用，請聯絡管理員")
                    return
                self.username = username
                self.role = user[1]
                if has_last_login:
                    cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE username=?", (username,))
                    conn.commit()
                reminder = self._build_password_reminder(conn, password_changed_at, created_at)
                conn.close()
                QMessageBox.information(self, "登入成功", f"登入成功，歡迎 {self.role} 使用！{reminder}")
                self.accept()  # 關閉登入視窗
                return

        conn.close()
        QMessageBox.warning(self, "登入失敗", "帳號或密碼錯誤")
