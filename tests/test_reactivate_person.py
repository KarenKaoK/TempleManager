import sqlite3
import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def people_db(tmp_path):
    db_path = tmp_path / "people_reactivate.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            household_id TEXT NOT NULL,
            role_in_household TEXT NOT NULL,
            status TEXT NOT NULL,
            name TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def test_reactivate_head_blocked_when_active_head_exists(people_db):
    c = AppController(db_path=people_db)
    cur = c.conn.cursor()
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES (?, ?, ?, ?, ?)",
        ("H_ACTIVE", "HH1", "HEAD", "ACTIVE", "現任戶長"),
    )
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES (?, ?, ?, ?, ?)",
        ("H_OLD", "HH1", "HEAD", "INACTIVE", "舊戶長"),
    )
    c.conn.commit()

    with pytest.raises(ValueError, match="已有啟用中的戶長"):
        c.reactivate_person("H_OLD")


def test_reactivate_member_blocked_when_no_active_head(people_db):
    c = AppController(db_path=people_db)
    cur = c.conn.cursor()
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES (?, ?, ?, ?, ?)",
        ("M1", "HH2", "MEMBER", "INACTIVE", "停用戶員"),
    )
    c.conn.commit()

    with pytest.raises(ValueError, match="請先恢復戶長"):
        c.reactivate_person("M1")


def test_reactivate_member_success_when_active_head_exists(people_db):
    c = AppController(db_path=people_db)
    cur = c.conn.cursor()
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES (?, ?, ?, ?, ?)",
        ("H1", "HH3", "HEAD", "ACTIVE", "戶長"),
    )
    cur.execute(
        "INSERT INTO people (id, household_id, role_in_household, status, name) VALUES (?, ?, ?, ?, ?)",
        ("M2", "HH3", "MEMBER", "INACTIVE", "戶員"),
    )
    c.conn.commit()

    affected = c.reactivate_person("M2")
    assert affected == 1

    row = cur.execute("SELECT status FROM people WHERE id = 'M2'").fetchone()
    assert row[0] == "ACTIVE"
