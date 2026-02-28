import sqlite3

import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def controller_with_payment_db(tmp_path):
    db_path = tmp_path / "test_activity_payment.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT,
            password_hash TEXT,
            display_name TEXT,
            role TEXT,
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 0,
            password_changed_at TEXT,
            last_login_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount REAL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            activity_end_date TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE activity_signups (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            group_id TEXT,
            signup_kind TEXT DEFAULT 'INITIAL',
            signup_time TEXT NOT NULL,
            note TEXT,
            total_amount INTEGER NOT NULL DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            paid_at TEXT,
            payment_txn_id INTEGER,
            payment_receipt_number TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE activity_plans (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price_type TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE activity_signup_plans (
            id TEXT PRIMARY KEY,
            signup_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            line_total INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category_id TEXT NOT NULL,
            category_name TEXT,
            amount INTEGER DEFAULT 0,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            receipt_number TEXT,
            note TEXT,
            source_type TEXT,
            source_id TEXT,
            adjustment_kind TEXT,
            adjusts_txn_id INTEGER,
            is_system_generated INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # seed
    cur.execute("INSERT INTO people (id, name) VALUES ('P1', '王小明')")
    cur.execute("INSERT INTO activities (id, name, activity_end_date) VALUES ('A1', '虎爺聖誕', '2026/02/28')")
    cur.execute(
        "INSERT INTO activity_signups (id, activity_id, person_id, group_id, signup_kind, signup_time, total_amount, created_at, updated_at) "
        "VALUES ('S1', 'A1', 'P1', 'S1', 'INITIAL', '2026-02-01 10:00:00', 600, '2026-02-01 10:00:00', '2026-02-01 10:00:00')"
    )
    cur.execute("INSERT INTO activity_plans (id, activity_id, name, price_type) VALUES ('PL1', 'A1', '雙虎祝壽', 'FIXED')")
    cur.execute("INSERT INTO activity_signup_plans (id, signup_id, plan_id, qty, line_total) VALUES ('SP1', 'S1', 'PL1', 2, 600)")
    conn.commit()
    conn.close()

    c = AppController(db_path=str(db_path))
    yield c
    c.conn.close()


def test_system_income_items_upserted_on_startup(controller_with_payment_db):
    cur = controller_with_payment_db.conn.cursor()
    rows = cur.execute("SELECT id, name FROM income_items ORDER BY id").fetchall()
    values = {(r["id"], r["name"]) for r in rows}
    assert ("90", "活動收入") in values
    assert ("91", "點燈收入") in values


def test_mark_activity_paid_maps_category_and_note(controller_with_payment_db):
    c = controller_with_payment_db
    result = c.mark_activity_signups_paid("A1", ["S1"], handler="櫃台A")
    assert result["paid_count"] == 1

    row = c.conn.cursor().execute(
        "SELECT category_id, category_name, note FROM transactions ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row["category_id"] == "90"
    assert row["category_name"] == "活動收入"
    assert row["note"].startswith("[2026/02/28 虎爺聖誕]")
    assert "雙虎祝壽×2" in row["note"]
