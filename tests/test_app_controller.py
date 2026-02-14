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
    建立一個乾淨的 sqlite 測試 DB，建立必要 tables 並塞入測試資料。
    採用單表設計：所有人都在 people 表中。
    """
    db_path = tmp_path / "test_app_controller.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- Create people table (Single Table Design) ---
    cur.execute("""
    CREATE TABLE people (
        id TEXT PRIMARY KEY,
        household_id TEXT NOT NULL,
        role_in_household TEXT NOT NULL CHECK(role_in_household IN ('HEAD','MEMBER')),
        status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','INACTIVE')),
        name TEXT NOT NULL,
        gender TEXT,
        birthday_ad TEXT,
        birthday_lunar TEXT,
        lunar_is_leap INTEGER DEFAULT 0,
        birth_time TEXT,
        age INTEGER,
        zodiac TEXT,
        phone_home TEXT,
        phone_mobile TEXT,
        address TEXT,
        zip_code TEXT,
        note TEXT,
        joined_at TEXT
    )
    """)

    # --- Seed Data ---
    # Household 1 (Head: 王大明)
    cur.execute("""
        INSERT INTO people (id, household_id, role_in_household, name, phone_home, phone_mobile, address, joined_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("P0", "H1", "HEAD", "王大明", "02-1111-2222", "0911-111-111", "台北市A路", "2026-01-01", "ACTIVE"))
    
    cur.execute("""
        INSERT INTO people (id, household_id, role_in_household, name, phone_mobile, address, joined_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("P1", "H1", "MEMBER", "王小明", "0933-333-333", "台北市A路", "2026-01-03", "ACTIVE"))

    cur.execute("""
        INSERT INTO people (id, household_id, role_in_household, name, phone_mobile, address, joined_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("P2", "H1", "MEMBER", "王小華", "0944-444-444", "台北市A路", "2026-01-04", "ACTIVE"))

    # Household 2 (Head: 林小美)
    cur.execute("""
        INSERT INTO people (id, household_id, role_in_household, name, phone_home, phone_mobile, address, joined_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("P3", "H2", "HEAD", "林小美", "02-3333-4444", "0922-222-222", "新北市B路", "2026-01-02", "ACTIVE"))

    cur.execute("""
        INSERT INTO people (id, household_id, role_in_household, name, phone_mobile, address, joined_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("P4", "H2", "MEMBER", "林小強", "0955-555-555", "新北市B路", "2026-01-05", "ACTIVE"))

    conn.commit()
    conn.close()

    controller = AppController(db_path=str(db_path))
    yield controller

    try:
        controller.conn.close()
    except Exception:
        pass


# -------------------------
# Tests: get_all_people
# -------------------------

def test_get_all_people_returns_all_rows(controller_with_db):
    c = controller_with_db
    people = c.get_all_people()
    assert isinstance(people, list)
    assert len(people) == 5
    # P4 was added last (2026-01-05), so it should be first due to ORDER BY joined_at DESC
    assert people[0]["id"] == "P4" 


# -------------------------
# Tests: list_household
# -------------------------

def test_list_household_by_keyword_name(controller_with_db):
    c = controller_with_db
    rows = c.list_household(keyword="王大")
    assert len(rows) == 1
    assert rows[0]["name"] == "王大明"


def test_list_household_by_keyword_phone(controller_with_db):
    c = controller_with_db
    rows = c.list_household(keyword="0922")
    assert len(rows) == 1
    assert rows[0]["name"] == "林小美"


# -------------------------
# Tests: list_people_by_household
# -------------------------

def test_list_people_by_household(controller_with_db):
    c = controller_with_db
    members = c.list_people_by_household("H1")
    assert len(members) == 3
    names = sorted([m["name"] for m in members])
    assert names == ["王大明", "王小明", "王小華"]


# -------------------------
# Tests: search_people_unified
# -------------------------

def test_search_people_unified_by_name(controller_with_db):
    c = controller_with_db
    results = c.search_people_unified("王小")
    assert len(results) == 2
    assert sorted([r["name"] for r in results]) == ["王小明", "王小華"]


def test_search_people_unified_by_mobile(controller_with_db):
    c = controller_with_db
    results = c.search_people_unified("0955")
    assert len(results) == 1
    assert results[0]["name"] == "林小強"


def test_search_people_unified_no_result(controller_with_db):
    c = controller_with_db
    results = c.search_people_unified("XYZ")
    assert results == []
