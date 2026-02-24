import sqlite3

import pytest

from app.controller.app_controller import AppController


def _init_users_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _insert_user(conn, uid, username, role):
    # 測試只驗證帳號管理流程，不驗證密碼內容
    pw = "dummy_hash"
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (uid, username, pw, role),
    )
    conn.commit()


@pytest.fixture
def security_db(tmp_path):
    db = tmp_path / "security.db"
    conn = sqlite3.connect(db)
    _init_users_table(conn)
    conn.close()
    return db


def test_delete_last_admin_is_blocked(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    with pytest.raises(ValueError, match="至少需要保留一位管理員"):
        controller.delete_user_account("admin", "admin")


def test_delete_admin_allowed_when_multiple_admins(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin1", "管理員")
    _insert_user(conn, "U2", "admin2", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    controller.delete_user_account("admin1", "admin2")

    rows = controller.list_users()
    usernames = {r["username"] for r in rows}
    assert usernames == {"admin1"}


def test_create_and_reset_password_write_security_logs(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    controller.create_user_account("admin", "staff1", "abcd1234", "工作人員", display_name="王小明")
    controller.reset_user_password("admin", "staff1", "temp5678", mode="manual")

    cur = controller.conn.cursor()
    cur.execute(
        "SELECT action, actor_username, target_username FROM security_logs ORDER BY id ASC"
    )
    logs = cur.fetchall()
    assert len(logs) >= 2
    assert logs[-2][0] == "create_user"
    assert logs[-2][1] == "admin"
    assert logs[-2][2] == "staff1"
    assert logs[-1][0] == "reset_password"
    assert logs[-1][1] == "admin"
    assert logs[-1][2] == "staff1"


def test_create_user_stores_display_name(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    controller.create_user_account("admin", "staff1001", "abcd1234", "工作人員", display_name="王小明")
    rows = controller.list_users()
    staff = next(r for r in rows if r["username"] == "staff1001")
    assert staff["display_name"] == "王小明"


def test_create_user_rejects_short_password(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    with pytest.raises(ValueError, match="at least 8 characters"):
        controller.create_user_account("admin", "staff1", "1234567", "工作人員", display_name="王小明")


def test_create_user_rejects_password_same_as_username(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    conn.close()

    controller = AppController(db_path=str(security_db))
    with pytest.raises(ValueError, match="same as username"):
        controller.create_user_account("admin", "staff1001", "staff1001", "工作人員", display_name="王小明")


def test_reset_password_rejects_password_same_as_username(security_db):
    conn = sqlite3.connect(security_db)
    _insert_user(conn, "U1", "admin", "管理員")
    _insert_user(conn, "U2", "staff1001", "工作人員")
    conn.close()
    controller = AppController(db_path=str(security_db))
    with pytest.raises(ValueError, match="same as username"):
        controller.reset_user_password("admin", "staff1001", "staff1001", mode="manual")
