# tests/test_app_controller.py
from datetime import date
import sqlite3
import pytest

from app.controller.app_controller import AppController
from app.database.setup_db import (
    create_security_tables,
    create_lighting_items_table,
    create_lighting_signup_tables,
)


def _new_lighting_controller(db_path):
    create_security_tables(str(db_path))
    create_lighting_items_table(str(db_path))
    create_lighting_signup_tables(str(db_path))
    return AppController(db_path=str(db_path))


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
        age_offset INTEGER DEFAULT 0,
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

    create_security_tables(str(db_path))
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


def test_login_cover_settings_roundtrip(controller_with_db):
    c = controller_with_db
    c.save_login_cover_settings("深坑天南宮", "/tmp/login_cover.png")
    settings = c.get_login_cover_settings()
    assert settings["title"] == "深坑天南宮"
    assert settings["image_path"] == "/tmp/login_cover.png"


def test_lighting_defaults_seeded_on_controller_init(tmp_path):
    db_path = tmp_path / "lighting_defaults.db"
    controller = _new_lighting_controller(db_path)
    try:
        rows = controller.list_lighting_items(include_inactive=True)
        names = [r["name"] for r in rows]
        assert "太歲燈" in names
        assert "光明燈" in names
        assert "吉祥如意燈" in names
        assert "祭改" in names
    finally:
        controller.conn.close()


def test_create_custom_lighting_item(tmp_path):
    db_path = tmp_path / "lighting_custom.db"
    controller = _new_lighting_controller(db_path)
    try:
        item_id = controller.create_lighting_item(name="文昌燈", fee=500, kind="JI_XIANG")
        rows = controller.list_lighting_items(include_inactive=True)
        row = next(r for r in rows if r["id"] == item_id)
        assert row["name"] == "文昌燈"
        assert int(row["fee"]) == 500
        assert row["kind"] == "JI_XIANG"
    finally:
        controller.conn.close()


def test_lighting_zodiac_suggestions_contains_required_fields(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_hint.db")
    try:
        data = controller.get_lighting_zodiac_suggestions(2026)
        assert data["year"] == 2026
        assert "year_zodiac" in data
        assert "太歲" in data["tai_sui_hint"]
        assert "祭改" in data["ji_gai_hint"]
        # 2026（屬馬）對照檢查
        star_map = data["annual_star_zodiac_map"]
        assert star_map["太歲"] == "馬"
        assert star_map["太陽"] == "蛇"
        assert star_map["喪門"] == "龍"
        assert star_map["太陰"] == "兔"
        assert star_map["五鬼"] == "虎"
        assert star_map["死符"] == "牛"
        assert star_map["歲破"] == "鼠"
        assert star_map["龍德"] == "豬"
        assert star_map["白虎"] == "狗"
        assert star_map["福德"] == "雞"
        assert star_map["天狗"] == "猴"
        assert star_map["病符"] == "羊"
        assert data["tai_sui_zodiacs"] == ["馬", "鼠"]
        assert data["ji_gai_zodiacs"] == ["龍", "兔", "虎", "牛", "狗", "猴", "羊"]
    finally:
        controller.conn.close()


def test_lighting_hint_settings_defaults_and_save(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_hint_settings.db")
    try:
        defaults = controller.get_lighting_hint_settings()
        assert defaults["year"]
        assert "犯太歲" in defaults["tai_sui_text"]
        assert "祭改" in defaults["ji_gai_text"]

        controller.save_lighting_hint_settings(
            year=2026,
            tai_sui_text="犯太歲：馬、鼠、兔、牛",
            ji_gai_text="祭改：如五鬼、喪命、吊客、病符、天狗、白虎、死符",
        )
        saved = controller.get_lighting_hint_settings()
        assert saved["year"] == "2026"
        assert saved["tai_sui_text"] == "犯太歲：馬、鼠、兔、牛"
        assert saved["ji_gai_text"] == "祭改：如五鬼、喪命、吊客、病符、天狗、白虎、死符"
    finally:
        controller.conn.close()


def test_list_lighting_signups_empty_returns_list(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_empty.db")
    try:
        # 建立最小 people 表，讓 lighting_signups 查詢 JOIN 可執行
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        controller.conn.commit()

        rows = controller.list_lighting_signups(2026)
        assert isinstance(rows, list)
        assert rows == []
    finally:
        controller.conn.close()


def test_upsert_lighting_signup_and_item_totals(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_upsert.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P2", "王小明", "0922000000"))
        controller.conn.commit()

        controller.upsert_lighting_signup(2026, "P1", ["L01", "L02"])
        controller.upsert_lighting_signup(2026, "P2", ["L01"])

        rows = controller.list_lighting_signups(2026)
        assert len(rows) == 2
        by_person = {r["person_name"]: r for r in rows}
        assert int(by_person["王大明"]["total_amount"]) == 1000
        assert int(by_person["王小明"]["total_amount"]) == 500

        totals = controller.get_lighting_signup_item_totals(2026)
        by_item = {r["lighting_item_id"]: r for r in totals}
        assert int(by_item["L01"]["signup_count"]) == 2
        assert int(by_item["L01"]["total_amount"]) == 1000
        assert int(by_item["L02"]["signup_count"]) == 1
        assert int(by_item["L02"]["total_amount"]) == 500

        selected = controller.get_lighting_signup_selected_item_ids(2026, ["P1", "P2"])
        assert set(selected["P1"]) == {"L01", "L02"}
        assert set(selected["P2"]) == {"L01"}
    finally:
        controller.conn.close()

def test_list_lighting_signup_rows_by_item_for_print(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_print_rows.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P2", "王小明", "0922000000"))
        controller.conn.commit()

        sid1 = controller.upsert_lighting_signup(2026, "P1", ["L01", "L02"])
        controller.upsert_lighting_signup(2026, "P2", ["L01"])
        cur.execute(
            "UPDATE lighting_signups SET is_paid = 1, payment_receipt_number = ? WHERE id = ?",
            ("R001", sid1),
        )
        controller.conn.commit()

        rows = controller.list_lighting_signup_rows_by_item(2026)
        assert len(rows) == 3
        assert [r["lighting_item_id"] for r in rows] == ["L01", "L01", "L02"]
        assert rows[0]["lighting_item_name"] in {"太歲燈", "光明燈", "吉祥如意燈", "祭改"}
        assert any(int(r.get("is_paid") or 0) == 1 for r in rows)
        assert any(str(r.get("payment_receipt_number") or "") == "R001" for r in rows)

        only_p2 = controller.list_lighting_signup_rows_by_item(2026, keyword="王小明")
        assert len(only_p2) == 1
        assert only_p2[0]["person_name"] == "王小明"
    finally:
        controller.conn.close()


def test_upsert_lighting_signup_rejects_paid_record_update(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_paid_guard.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])
        cur.execute("UPDATE lighting_signups SET is_paid = 1 WHERE id = ?", (signup_id,))
        controller.conn.commit()

        with pytest.raises(ValueError, match="已繳費"):
            controller.upsert_lighting_signup(2026, "P1", ["L01", "L02"])
    finally:
        controller.conn.close()


def test_upsert_lighting_signup_allows_paid_record_update_with_flag(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_paid_allow_update.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])
        cur.execute("UPDATE lighting_signups SET is_paid = 1 WHERE id = ?", (signup_id,))
        controller.conn.commit()

        same_signup_id = controller.upsert_lighting_signup(
            2026,
            "P1",
            ["L01", "L02"],
            allow_paid_update=True,
        )
        assert same_signup_id == signup_id

        rows = controller.list_lighting_signups(2026)
        assert len(rows) == 1
        assert int(rows[0]["is_paid"] or 0) == 1
        assert int(rows[0]["total_amount"] or 0) == 1000
    finally:
        controller.conn.close()


def test_mark_lighting_signups_paid_writes_transaction_source_link(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_paid_source_link.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS income_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT OR REPLACE INTO income_items (id, name, amount) VALUES (?, ?, ?)", ("91", "點燈收入", 0))
        cur.execute("INSERT OR REPLACE INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("91R", "安燈退費", 0))
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])
        result = controller.mark_lighting_signups_paid(2026, [signup_id], handler="測試經手人")
        assert int(result["paid_count"]) == 1

        txn = cur.execute(
            """
            SELECT source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
            FROM transactions
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        assert txn is not None
        assert str(txn["source_type"] or "") == "LIGHTING_SIGNUP"
        assert str(txn["source_id"] or "") == signup_id
        assert str(txn["adjustment_kind"] or "") == "PRIMARY"
        assert txn["adjusts_txn_id"] is None
        assert int(txn["is_system_generated"] or 0) == 1
    finally:
        controller.conn.close()


def test_mark_lighting_signup_append_paid_writes_supplement_kind(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_append_paid_kind.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS income_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT OR REPLACE INTO income_items (id, name, amount) VALUES (?, ?, ?)", ("91", "點燈收入", 0))
        cur.execute("INSERT OR REPLACE INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("91R", "安燈退費", 0))
        controller.conn.commit()

        controller.upsert_lighting_signup(2026, "P1", ["L01"])
        append_result = controller.create_lighting_signup_append(2026, "P1", ["L02"])
        append_signup_id = str(append_result["signup_id"] or "")

        result = controller.mark_lighting_signups_paid(2026, [append_signup_id], handler="測試經手人")
        assert int(result["paid_count"]) == 1

        txn = cur.execute(
            """
            SELECT adjustment_kind
            FROM transactions
            WHERE source_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (append_signup_id,),
        ).fetchone()
        assert txn is not None
        assert str(txn["adjustment_kind"] or "") == "SUPPLEMENT"
    finally:
        controller.conn.close()


def test_update_paid_lighting_signup_with_adjustment_creates_supplement_and_refund(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_adjustment_phase3.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS income_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT OR REPLACE INTO income_items (id, name, amount) VALUES (?, ?, ?)", ("91", "點燈收入", 0))
        cur.execute("INSERT OR REPLACE INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("91R", "安燈退費", 0))
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])  # 600
        paid = controller.mark_lighting_signups_paid(2026, [signup_id], handler="測試經手人")
        assert int(paid["paid_count"]) == 1

        adj1 = controller.update_paid_lighting_signup_with_adjustment(
            2026, "P1", ["L01", "L02"], handler="測試經手人"
        )
        assert int(adj1["delta"]) == 500
        assert str(adj1["adjustment_type"]) == "SUPPLEMENT"

        adj2 = controller.update_paid_lighting_signup_with_adjustment(
            2026, "P1", ["L02"], handler="測試經手人"
        )
        assert int(adj2["delta"]) == -500
        assert str(adj2["adjustment_type"]) == "REFUND"

        tx_rows = cur.execute(
            """
            SELECT type, amount, source_type, adjustment_kind
            FROM transactions
            WHERE source_id = ?
            ORDER BY id ASC
            """,
            (signup_id,),
        ).fetchall()
        assert len(tx_rows) == 3
        assert [str(r["adjustment_kind"] or "") for r in tx_rows] == ["PRIMARY", "SUPPLEMENT", "REFUND"]
    finally:
        controller.conn.close()


def test_delete_lighting_signup_removes_master_and_items(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_delete.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01", "L02"])
        assert controller.delete_lighting_signup(2026, signup_id) is True
        assert controller.list_lighting_signups(2026) == []
        assert controller.get_lighting_signup_item_totals(2026) == []
    finally:
        controller.conn.close()


def test_create_lighting_signup_append_creates_second_record_with_group_and_kind(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_append_kind.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        controller.conn.commit()

        first_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])
        result = controller.create_lighting_signup_append(2026, "P1", ["L02"])
        second_id = str(result["signup_id"] or "")
        assert second_id and second_id != first_id
        assert str(result["signup_kind"] or "") == "APPEND"

        rows = controller.list_lighting_signups(2026)
        assert len(rows) == 2
        kinds = [str(r.get("signup_kind") or "") for r in rows]
        assert "INITIAL" in kinds
        assert "APPEND" in kinds
        group_ids = {str(r.get("group_id") or "") for r in rows}
        assert len(group_ids) == 1
    finally:
        controller.conn.close()


def test_delete_lighting_signup_paid_record_voids_transactions_and_deletes_record(tmp_path):
    controller = _new_lighting_controller(tmp_path / "lighting_signup_delete_paid.db")
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute("INSERT OR REPLACE INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        controller.conn.commit()

        signup_id = controller.upsert_lighting_signup(2026, "P1", ["L01"])
        cur.execute(
            "UPDATE lighting_signups SET is_paid = 1, payment_txn_id = 1, payment_receipt_number = 'R001' WHERE id = ?",
            (signup_id,),
        )
        cur.execute(
            """
            INSERT INTO transactions (
                date, type, category_id, category_name, amount,
                payer_person_id, payer_name, handler, receipt_number, note,
                is_voided, source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated, is_deleted
            ) VALUES (?, 'income', ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 0)
            """,
            ("2026-01-01", "91", "點燈收入", 600, "P1", "王大明", "櫃台", "R001", "測試", "LIGHTING_SIGNUP", signup_id, "PRIMARY", None, 1),
        )
        controller.conn.commit()

        assert controller.delete_lighting_signup(2026, signup_id) is True
        row = cur.execute("SELECT id FROM lighting_signups WHERE id = ?", (signup_id,)).fetchone()
        assert row is None
        tx = cur.execute(
            "SELECT COALESCE(is_voided, 0) AS is_voided FROM transactions WHERE source_id = ? LIMIT 1",
            (signup_id,),
        ).fetchone()
        assert tx is not None
        assert int(tx["is_voided"] or 0) == 1
    finally:
        controller.conn.close()


def test_delete_activity_signup_removes_unpaid_record(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_signup_delete_unpaid.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                signup_time TEXT,
                note TEXT,
                total_amount INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                is_paid INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT
            )
            """
        )
        now = controller._now()
        cur.execute(
            """
            INSERT INTO activity_signups (
                id, activity_id, person_id, group_id, signup_kind, signup_time, note, total_amount, created_at, updated_at, is_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("AS1", "A1", "P1", "AS1", "INITIAL", now, None, 100, now, now, 0),
        )
        controller.conn.commit()

        assert controller.delete_activity_signup("AS1") is True
        row = cur.execute("SELECT id FROM activity_signups WHERE id = 'AS1'").fetchone()
        assert row is None
    finally:
        controller.conn.close()


def test_delete_activity_signup_rejects_paid_record(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_signup_delete_paid.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                signup_time TEXT,
                note TEXT,
                total_amount INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                is_paid INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT
            )
            """
        )
        now = controller._now()
        cur.execute(
            """
            INSERT INTO activity_signups (
                id, activity_id, person_id, group_id, signup_kind, signup_time, note, total_amount, created_at, updated_at, is_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("AS1", "A1", "P1", "AS1", "INITIAL", now, None, 100, now, now, 1),
        )
        controller.conn.commit()

        with pytest.raises(ValueError, match="已繳費"):
            controller.delete_activity_signup("AS1")
    finally:
        controller.conn.close()


def test_mark_activity_signups_paid_writes_transaction_source_link(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_paid_source_link.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                name TEXT,
                activity_end_date TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                total_amount INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                paid_at TEXT,
                payment_txn_id INTEGER,
                payment_receipt_number TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_plans (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                name TEXT,
                price_type TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT,
                plan_id TEXT,
                qty INTEGER DEFAULT 0,
                line_total INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS income_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute("INSERT INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT INTO activities (id, name, activity_end_date) VALUES (?, ?, ?)", ("A1", "法會", "2026-03-01"))
        cur.execute(
            "INSERT INTO activity_signups (id, activity_id, person_id, group_id, signup_kind, total_amount, is_paid) VALUES (?, ?, ?, ?, ?, ?, 0)",
            ("AS1", "A1", "P1", "AS1", "INITIAL", 1000),
        )
        cur.execute("INSERT INTO activity_plans (id, activity_id, name, price_type) VALUES (?, ?, ?, ?)", ("AP1", "A1", "方案A", "FIXED"))
        cur.execute("INSERT INTO activity_signup_plans (id, signup_id, plan_id, qty, line_total) VALUES (?, ?, ?, ?, ?)", ("ASP1", "AS1", "AP1", 1, 1000))
        cur.execute("INSERT OR REPLACE INTO income_items (id, name, amount) VALUES (?, ?, ?)", ("90", "活動收入", 0))
        cur.execute("INSERT OR REPLACE INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("90R", "活動退費", 0))
        controller.conn.commit()

        result = controller.mark_activity_signups_paid("A1", ["AS1"], handler="測試經手人")
        assert int(result["paid_count"]) == 1

        txn = cur.execute(
            """
            SELECT source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated
            FROM transactions
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        assert txn is not None
        assert str(txn["source_type"] or "") == "ACTIVITY_SIGNUP"
        assert str(txn["source_id"] or "") == "AS1"
        assert str(txn["adjustment_kind"] or "") == "PRIMARY"
        assert txn["adjusts_txn_id"] is None
        assert int(txn["is_system_generated"] or 0) == 1
    finally:
        controller.conn.close()


def test_update_paid_activity_signup_with_adjustment_creates_supplement_and_refund(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_adjustment_phase3.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                name TEXT,
                activity_end_date TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                total_amount INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                paid_at TEXT,
                payment_txn_id INTEGER,
                payment_receipt_number TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_plans (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                name TEXT,
                price_type TEXT,
                fixed_price INTEGER DEFAULT 0,
                suggested_price INTEGER DEFAULT 0,
                min_price INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT,
                plan_id TEXT,
                qty INTEGER DEFAULT 0,
                unit_price_snapshot INTEGER DEFAULT 0,
                amount_override INTEGER,
                line_total INTEGER DEFAULT 0,
                note TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS income_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_items (
                id TEXT PRIMARY KEY,
                name TEXT,
                amount INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute("INSERT INTO people (id, name, phone_mobile) VALUES (?, ?, ?)", ("P1", "王大明", "0911000000"))
        cur.execute("INSERT INTO activities (id, name, activity_end_date) VALUES (?, ?, ?)", ("A1", "法會", "2026-03-01"))
        cur.execute(
            "INSERT INTO activity_signups (id, activity_id, person_id, group_id, signup_kind, total_amount, is_paid) VALUES (?, ?, ?, ?, ?, ?, 0)",
            ("AS1", "A1", "P1", "AS1", "INITIAL", 600),
        )
        cur.execute(
            """
            INSERT INTO activity_plans (id, activity_id, name, price_type, fixed_price, suggested_price, min_price, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("AP1", "A1", "方案A", "FIXED", 600, 0, 0, 1),
        )
        cur.execute(
            """
            INSERT INTO activity_signup_plans
            (id, signup_id, plan_id, qty, unit_price_snapshot, amount_override, line_total, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("ASP1", "AS1", "AP1", 1, 600, None, 600, None),
        )
        cur.execute("INSERT OR REPLACE INTO income_items (id, name, amount) VALUES (?, ?, ?)", ("90", "活動收入", 0))
        cur.execute("INSERT OR REPLACE INTO expense_items (id, name, amount) VALUES (?, ?, ?)", ("90R", "活動退費", 0))
        controller.conn.commit()

        paid = controller.mark_activity_signups_paid("A1", ["AS1"], handler="測試經手人")
        assert int(paid["paid_count"]) == 1

        adj1 = controller.update_paid_activity_signup_with_adjustment(
            "AS1",
            {"AP1": 2},
            {},
            handler="測試經手人",
        )
        assert int(adj1["delta"]) == 600
        assert str(adj1["adjustment_type"] or "") == "SUPPLEMENT"

        adj2 = controller.update_paid_activity_signup_with_adjustment(
            "AS1",
            {"AP1": 1},
            {},
            handler="測試經手人",
        )
        assert int(adj2["delta"]) == -600
        assert str(adj2["adjustment_type"] or "") == "REFUND"

        tx_rows = cur.execute(
            """
            SELECT type, amount, source_type, adjustment_kind
            FROM transactions
            WHERE source_id = ?
            ORDER BY id ASC
            """,
            ("AS1",),
        ).fetchall()
        assert len(tx_rows) == 3
        assert [str(r["adjustment_kind"] or "") for r in tx_rows] == ["PRIMARY", "SUPPLEMENT", "REFUND"]
    finally:
        controller.conn.close()


def test_list_transactions_by_source_filters_and_orders(tmp_path):
    controller = AppController(db_path=str(tmp_path / "tx_by_source.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, amount, source_type, source_id, adjustment_kind, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            ("2026-01-01", "income", "91", 1000, "LIGHTING_SIGNUP", "LS1", "PRIMARY"),
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, amount, source_type, source_id, adjustment_kind, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            ("2026-01-02", "income", "91", 200, "LIGHTING_SIGNUP", "LS1", "SUPPLEMENT"),
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, amount, source_type, source_id, adjustment_kind, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            ("2026-01-03", "expense", "91R", 100, "LIGHTING_SIGNUP", "LS1", "REFUND"),
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, amount, source_type, source_id, adjustment_kind, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            ("2026-01-04", "income", "91", 999, "LIGHTING_SIGNUP", "LS2", "PRIMARY"),
        )
        controller.conn.commit()

        rows = controller.list_transactions_by_source("LIGHTING_SIGNUP", "LS1")
        assert [str(r["adjustment_kind"] or "") for r in rows] == ["PRIMARY", "SUPPLEMENT", "REFUND"]
        assert [int(r["amount"] or 0) for r in rows] == [1000, 200, 100]
    finally:
        controller.conn.close()


def test_get_income_transactions_by_person_filters_voided_rows(tmp_path):
    controller = AppController(db_path=str(tmp_path / "income_by_person_voided.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                adjustment_kind TEXT,
                is_voided INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, category_name, amount, payer_person_id, payer_name, is_voided, is_deleted) VALUES (?, 'income', ?, ?, ?, ?, ?, 0, 0)",
            ("2026-01-01", "91", "點燈收入", 600, "P1", "王大明"),
        )
        cur.execute(
            "INSERT INTO transactions (date, type, category_id, category_name, amount, payer_person_id, payer_name, is_voided, is_deleted) VALUES (?, 'income', ?, ?, ?, ?, ?, 1, 0)",
            ("2026-01-02", "90", "活動收入", 1000, "P1", "王大明"),
        )
        controller.conn.commit()

        rows = controller.get_income_transactions_by_person("P1")
        assert len(rows) == 1
        assert str(rows[0]["category_id"] or "") == "91"
    finally:
        controller.conn.close()


def test_create_activity_signup_append_creates_second_record_with_group_and_kind(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_append_kind.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT,
                address TEXT,
                birthday_ad TEXT,
                birthday_lunar TEXT,
                lunar_is_leap INTEGER DEFAULT 0
            )
            """
        )
        cur.execute("CREATE TABLE IF NOT EXISTS activities (id TEXT PRIMARY KEY, name TEXT, activity_end_date TEXT)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                signup_time TEXT,
                note TEXT,
                total_amount INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                is_paid INTEGER DEFAULT 0,
                paid_at TEXT,
                payment_txn_id INTEGER,
                payment_receipt_number TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_plans (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                name TEXT,
                price_type TEXT,
                fixed_price INTEGER DEFAULT 0,
                min_price INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT,
                plan_id TEXT,
                qty INTEGER DEFAULT 1,
                unit_price_snapshot INTEGER DEFAULT 0,
                amount_override INTEGER,
                line_total INTEGER DEFAULT 0,
                note TEXT
            )
            """
        )
        cur.execute(
            "INSERT INTO people (id, name, phone_mobile, address, birthday_ad, birthday_lunar, lunar_is_leap) VALUES ('P1','王大明','0911000000','','','','0')"
        )
        cur.execute("INSERT INTO activities (id, name, activity_end_date) VALUES ('A1','法會','2026-03-01')")
        cur.execute("INSERT INTO activity_plans (id, activity_id, name, price_type, fixed_price, min_price) VALUES ('AP1','A1','方案A','FIXED',600,0)")
        controller.conn.commit()

        first_id = controller.create_activity_signup("A1", "P1", [{"plan_id": "AP1", "qty": 1}])
        result = controller.create_activity_signup_append("A1", "P1", [{"plan_id": "AP1", "qty": 2}])
        second_id = str(result.get("signup_id") or "")
        assert second_id and second_id != first_id
        assert str(result.get("signup_kind") or "") == "APPEND"

        rows = controller.get_activity_signups("A1")
        assert len(rows) == 2
        kinds = [str(r.get("signup_kind") or "") for r in rows]
        assert "INITIAL" in kinds and "APPEND" in kinds
        assert len({str(r.get("group_id") or "") for r in rows}) == 1
    finally:
        controller.conn.close()


def test_mark_activity_signup_append_paid_writes_supplement_kind(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_append_paid_kind.db"))
    try:
        cur = controller.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone_mobile TEXT,
                address TEXT,
                birthday_ad TEXT,
                birthday_lunar TEXT,
                lunar_is_leap INTEGER DEFAULT 0
            )
            """
        )
        cur.execute("CREATE TABLE IF NOT EXISTS activities (id TEXT PRIMARY KEY, name TEXT, activity_end_date TEXT)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                signup_time TEXT,
                note TEXT,
                total_amount INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                is_paid INTEGER DEFAULT 0,
                paid_at TEXT,
                payment_txn_id INTEGER,
                payment_receipt_number TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_plans (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                name TEXT,
                price_type TEXT,
                fixed_price INTEGER DEFAULT 0,
                min_price INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signup_plans (
                id TEXT PRIMARY KEY,
                signup_id TEXT,
                plan_id TEXT,
                qty INTEGER DEFAULT 0,
                unit_price_snapshot INTEGER DEFAULT 0,
                amount_override INTEGER,
                line_total INTEGER DEFAULT 0,
                note TEXT
            )
            """
        )
        cur.execute("CREATE TABLE IF NOT EXISTS income_items (id TEXT PRIMARY KEY, name TEXT, amount INTEGER DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS expense_items (id TEXT PRIMARY KEY, name TEXT, amount INTEGER DEFAULT 0)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute(
            "INSERT INTO people (id, name, phone_mobile, address, birthday_ad, birthday_lunar, lunar_is_leap) VALUES ('P1','王大明','0911000000','','','','0')"
        )
        cur.execute("INSERT INTO activities VALUES ('A1','法會','2026-03-01')")
        cur.execute("INSERT INTO activity_plans (id, activity_id, name, price_type, fixed_price, min_price) VALUES ('AP1','A1','方案A','FIXED',600,0)")
        cur.execute("INSERT OR REPLACE INTO income_items VALUES ('90','活動收入',0)")
        cur.execute("INSERT OR REPLACE INTO expense_items VALUES ('90R','活動退費',0)")
        controller.conn.commit()

        controller.create_activity_signup("A1", "P1", [{"plan_id": "AP1", "qty": 1}])
        append = controller.create_activity_signup_append("A1", "P1", [{"plan_id": "AP1", "qty": 1}])
        append_sid = str(append.get("signup_id") or "")
        cur.execute("UPDATE activity_signups SET total_amount = 600 WHERE id = ?", (append_sid,))
        cur.execute("INSERT INTO activity_signup_plans (id, signup_id, plan_id, qty, line_total) VALUES ('X1', ?, 'AP1', 1, 600)", (append_sid,))
        controller.conn.commit()

        result = controller.mark_activity_signups_paid("A1", [append_sid], handler="櫃台A")
        assert int(result["paid_count"]) == 1
        tx = cur.execute("SELECT adjustment_kind FROM transactions WHERE source_id = ? ORDER BY id DESC LIMIT 1", (append_sid,)).fetchone()
        assert tx is not None
        assert str(tx["adjustment_kind"] or "") == "SUPPLEMENT"
    finally:
        controller.conn.close()


def test_delete_activity_signup_with_void_transactions_paid_record(tmp_path):
    controller = AppController(db_path=str(tmp_path / "activity_delete_voided.db"))
    try:
        cur = controller.conn.cursor()
        now = controller._now()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_signups (
                id TEXT PRIMARY KEY,
                activity_id TEXT,
                person_id TEXT,
                group_id TEXT,
                signup_kind TEXT DEFAULT 'INITIAL',
                signup_time TEXT,
                note TEXT,
                total_amount INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                is_paid INTEGER DEFAULT 0,
                paid_at TEXT,
                payment_txn_id INTEGER,
                payment_receipt_number TEXT
            )
            """
        )
        cur.execute("CREATE TABLE IF NOT EXISTS activity_signup_plans (id TEXT PRIMARY KEY, signup_id TEXT)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
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
                is_voided INTEGER DEFAULT 0,
                source_type TEXT,
                source_id TEXT,
                adjustment_kind TEXT,
                adjusts_txn_id INTEGER,
                is_system_generated INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        cur.execute(
            """
            INSERT INTO activity_signups (id, activity_id, person_id, group_id, signup_kind, signup_time, total_amount, created_at, updated_at, is_paid, payment_txn_id, payment_receipt_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 'R001')
            """,
            ("AS1", "A1", "P1", "AS1", "INITIAL", now, 600, now, now),
        )
        cur.execute("INSERT INTO activity_signup_plans (id, signup_id) VALUES ('ASP1', 'AS1')")
        cur.execute(
            """
            INSERT INTO transactions (date, type, category_id, category_name, amount, payer_person_id, payer_name, handler, receipt_number, note,
                                      is_voided, source_type, source_id, adjustment_kind, adjusts_txn_id, is_system_generated, is_deleted)
            VALUES ('2026-01-01','income','90','活動收入',600,'P1','王大明','櫃台','R001','測試',0,'ACTIVITY_SIGNUP','AS1','PRIMARY',NULL,1,0)
            """
        )
        controller.conn.commit()

        assert controller.delete_activity_signup_with_void_transactions("AS1") is True
        assert cur.execute("SELECT id FROM activity_signups WHERE id='AS1'").fetchone() is None
        tx = cur.execute("SELECT COALESCE(is_voided,0) AS is_voided FROM transactions WHERE source_id='AS1' LIMIT 1").fetchone()
        assert tx is not None
        assert int(tx["is_voided"] or 0) == 1
    finally:
        controller.conn.close()
