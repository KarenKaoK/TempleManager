# tests/test_app_controller.py
import sqlite3
import pytest

from app.controller.app_controller import AppController


# -------------------------
# Test DB Fixtures
# -------------------------

@pytest.fixture
def controller_with_db(tmp_path):
    """
    建立一個乾淨的 sqlite 測試 DB，建立必要 tables 並塞入測試資料，
    回傳 AppController(db_path=...).

    ✅ 不會碰到正式 temple.db
    """
    db_path = tmp_path / "test_app_controller.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- tables needed by tested methods ---
    cur.execute("""
        CREATE TABLE households (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            head_name TEXT NOT NULL,
            head_gender TEXT,
            head_birthday_ad TEXT,
            head_birthday_lunar TEXT,
            head_birth_time TEXT,
            head_age INTEGER,
            head_zodiac TEXT,
            head_phone_home TEXT,
            head_phone_mobile TEXT,
            head_email TEXT,
            head_address TEXT,
            head_zip_code TEXT,
            head_identity TEXT,
            head_note TEXT,
            head_joined_at TEXT,
            household_note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            gender TEXT,
            birthday_ad TEXT,
            birthday_lunar TEXT,
            birth_time TEXT,
            age INTEGER,
            zodiac TEXT,
            phone_home TEXT,
            phone_mobile TEXT,
            email TEXT,
            address TEXT,
            zip_code TEXT,
            identity TEXT,
            note TEXT,
            joined_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE household_members (
            id TEXT PRIMARY KEY,
            household_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            relationship TEXT
        )
    """)

    # --- seed data ---
    # Household 1: 王大明 (id will be 1)
    cur.execute("""
        INSERT INTO households (
            head_name, head_phone_home, head_phone_mobile, head_address, head_identity, head_joined_at, household_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("王大明", "02-1111-2222", "0911-111-111", "台北市A路", "丁", "2026-01-01", "戶註記A"))

    # Household 2: 林小美 (id will be 2)
    cur.execute("""
        INSERT INTO households (
            head_name, head_phone_home, head_phone_mobile, head_address, head_identity, head_joined_at, household_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("林小美", "02-3333-4444", "0922-222-222", "新北市B路", "丁", "2026-01-02", "戶註記B"))

    # People
    cur.execute("""
        INSERT INTO people (id, name, phone_mobile, identity, address, joined_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("P1", "王小明", "0933-333-333", "口", "台北市A路", "2026-01-03"))

    cur.execute("""
        INSERT INTO people (id, name, phone_mobile, identity, address, joined_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("P2", "王小華", "0944-444-444", "口", "台北市A路", "2026-01-04"))

    cur.execute("""
        INSERT INTO people (id, name, phone_mobile, identity, address, joined_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("P3", "林小強", "0955-555-555", "口", "新北市B路", "2026-01-05"))

    # Household members mapping
    # household_id=1 -> P1, P2
    cur.execute("INSERT INTO household_members (id, household_id, person_id, relationship) VALUES (?, ?, ?, ?)",
                ("HM1", "1", "P1", "子"))
    cur.execute("INSERT INTO household_members (id, household_id, person_id, relationship) VALUES (?, ?, ?, ?)",
                ("HM2", "1", "P2", "女"))

    # household_id=2 -> P3
    cur.execute("INSERT INTO household_members (id, household_id, person_id, relationship) VALUES (?, ?, ?, ?)",
                ("HM3", "2", "P3", "子"))

    conn.commit()
    conn.close()

    controller = AppController(db_path=str(db_path))
    yield controller

    # teardown
    try:
        controller.conn.close()
    except Exception:
        pass


# -------------------------
# Tests: search_households
# -------------------------

def test_search_households_by_head_name(controller_with_db):
    c = controller_with_db
    rows = c.search_households("王大")
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert rows[0]["head_name"] == "王大明"


def test_search_households_by_phone_home(controller_with_db):
    c = controller_with_db
    rows = c.search_households("02-3333")
    assert len(rows) == 1
    assert rows[0]["head_name"] == "林小美"


def test_search_households_by_phone_mobile(controller_with_db):
    c = controller_with_db
    rows = c.search_households("0911")
    assert len(rows) == 1
    assert rows[0]["head_name"] == "王大明"


# -------------------------
# Tests: get_household_members
# -------------------------

def test_get_household_members_returns_joined_people(controller_with_db):
    c = controller_with_db
    members = c.get_household_members("1")
    assert isinstance(members, list)
    assert len(members) == 2

    names = sorted([m["name"] for m in members])
    assert names == ["王小明", "王小華"]


# -------------------------
# Tests: search_by_any_name
# -------------------------

def test_search_by_any_name_when_keyword_is_head_name(controller_with_db):
    c = controller_with_db
    head_row, members = c.search_by_any_name("王大明")

    # head_row should be sqlite3.Row (or tuple-like)
    assert head_row is not None
    assert head_row["head_name"] == "王大明"

    assert isinstance(members, list)
    assert len(members) == 2
    assert sorted([m["name"] for m in members]) == ["王小明", "王小華"]


def test_search_by_any_name_when_keyword_is_member_name(controller_with_db):
    c = controller_with_db
    head_row, members = c.search_by_any_name("林小強")

    assert head_row is not None
    assert head_row["head_name"] == "林小美"

    assert isinstance(members, list)
    assert len(members) == 1
    assert members[0]["name"] == "林小強"


def test_search_by_any_name_not_found(controller_with_db):
    c = controller_with_db
    head_row, members = c.search_by_any_name("不存在的人")
    assert head_row is None
    assert members == []
