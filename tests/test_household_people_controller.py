# tests/test_household_people_controller.py
import sqlite3
import uuid
import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def controller_with_household_db(tmp_path):
    """
    建立 households / people / household_members 三張表的測試 DB，回傳 AppController。

    注意：
    - 這裡的 household_members schema 設計成「不需要手動提供 id」
      以符合你 AppController.insert_member() 目前的 INSERT 寫法。
    - 如果你 production 的 household_members 是 id TEXT PRIMARY KEY 且無 DEFAULT，
      那 insert_member 在真環境會炸；你需要統一 schema 或修 insert_member。
    """
    db_path = tmp_path / "test_household_people.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # households：符合你 controller 常用欄位（id + head_*）
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

    # people：符合 insert_member / update_member / get_member_by_id / search_people
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
            joined_at TEXT,
            lunar_is_leap INTEGER DEFAULT 0,
            id_number TEXT
        )
    """)

    # household_members：這裡用 AUTOINCREMENT 讓 insert_member 不用提供 id
    cur.execute("""
        CREATE TABLE household_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            household_id INTEGER NOT NULL,
            person_id TEXT NOT NULL,
            relationship TEXT
        )
    """)

    conn.commit()
    conn.close()

    controller = AppController(db_path=str(db_path))
    yield controller

    try:
        controller.conn.close()
    except Exception:
        pass


def _insert_household_direct(controller, head_name="王戶長", phone_home="02-123", phone_mobile="0912"):
    cur = controller.conn.cursor()
    cur.execute("""
        INSERT INTO households (
            head_name, head_gender, head_birthday_ad, head_birthday_lunar, head_birth_time,
            head_age, head_zodiac, head_phone_home, head_phone_mobile, head_email,
            head_address, head_zip_code, head_identity, head_note, head_joined_at, household_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        head_name, "男", "1980-01-01", "1979-12-01", "子時",
        45, "龍", phone_home, phone_mobile, "a@b.com",
        "台北市", "100", "丁", "戶長備註", "2026-01-13", "戶備註"
    ))
    controller.conn.commit()
    return cur.lastrowid


def _insert_member_direct(controller, household_id: int, name="李戶員", phone_home="02-777", phone_mobile="0988"):
    person_id = str(uuid.uuid4())
    cur = controller.conn.cursor()
    cur.execute("""
        INSERT INTO people (
            id, name, gender, birthday_ad, birthday_lunar, birth_time,
            age, zodiac, phone_home, phone_mobile, email,
            address, zip_code, identity, note, joined_at, lunar_is_leap, id_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        person_id, name, "女", "1995-02-02", "1994-12-10", "午時",
        30, "豬", phone_home, phone_mobile, "m@b.com",
        "新北市", "220", "口", "戶員備註", "2026-01-13", 0, "B234567890"
    ))
    cur.execute("""
        INSERT INTO household_members (household_id, person_id, relationship)
        VALUES (?, ?, ?)
    """, (household_id, person_id, "家人"))
    controller.conn.commit()
    return person_id


# -------------------------
# search_households
# -------------------------

def test_search_households_by_name_and_phones(controller_with_household_db):
    c = controller_with_household_db
    _insert_household_direct(c, head_name="王大明", phone_home="02-111", phone_mobile="0912-000")
    _insert_household_direct(c, head_name="陳小華", phone_home="02-222", phone_mobile="0933-999")

    # by name
    rows = c.search_households("王")
    assert len(rows) == 1
    assert rows[0]["head_name"] == "王大明"

    # by home phone
    rows2 = c.search_households("02-222")
    assert len(rows2) == 1
    assert rows2[0]["head_name"] == "陳小華"

    # by mobile
    rows3 = c.search_households("0912")
    assert len(rows3) == 1
    assert rows3[0]["head_name"] == "王大明"


# -------------------------
# get_household_members
# -------------------------

def test_get_household_members_returns_people_dicts(controller_with_household_db):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="王戶長")
    pid = _insert_member_direct(c, hid, name="李戶員")

    members = c.get_household_members(hid)
    assert isinstance(members, list)
    assert len(members) == 1
    assert members[0]["id"] == pid
    assert members[0]["name"] == "李戶員"


# -------------------------
# search_by_any_name
# -------------------------

def test_search_by_any_name_when_keyword_is_head_name(controller_with_household_db):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="王大明")
    _insert_member_direct(c, hid, name="小孩A")
    head_row, members = c.search_by_any_name("王")

    assert head_row is not None
    assert head_row["head_name"] == "王大明"
    assert len(members) == 1
    assert members[0]["name"] == "小孩A"


def test_search_by_any_name_when_keyword_is_member_name(controller_with_household_db):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="戶長B")
    _insert_member_direct(c, hid, name="關鍵戶員")

    head_row, members = c.search_by_any_name("關鍵")
    assert head_row is not None
    assert head_row["head_name"] == "戶長B"
    assert len(members) == 1
    assert members[0]["name"] == "關鍵戶員"


def test_search_by_any_name_not_found(controller_with_household_db):
    c = controller_with_household_db
    _insert_household_direct(c, head_name="某戶長")
    head_row, members = c.search_by_any_name("不存在")
    assert head_row is None
    assert members == []


# -------------------------
# get_household_by_id
# -------------------------

def test_get_household_by_id_returns_dict(controller_with_household_db):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="王戶長")

    row = c.get_household_by_id(hid)
    assert isinstance(row, dict)
    assert row["id"] == hid
    assert row["head_name"] == "王戶長"


def test_get_household_by_id_not_found_returns_empty_dict(controller_with_household_db):
    c = controller_with_household_db
    row = c.get_household_by_id(999999)
    assert row == {}


# -------------------------
# household_has_members + delete_household
# -------------------------

def test_household_has_members_and_delete_household(controller_with_household_db):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="王戶長")
    _insert_member_direct(c, hid, name="戶員1")

    assert c.household_has_members(hid) is True

    c.delete_household(hid)

    # households 被刪
    rows = c.search_households("王戶長")
    assert rows == []

    # household_members 也應清掉（避免殘留）
    cur = c.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM household_members WHERE household_id = ?", (hid,))
    assert cur.fetchone()[0] == 0


# -------------------------
# insert_household（用 controller 自己的方法）
# -------------------------

def test_insert_household_then_searchable(controller_with_household_db):
    c = controller_with_household_db
    data = {
        "head_name": "新增戶長",
        "head_gender": "女",
        "head_birthday_ad": "1988-01-01",
        "head_birthday_lunar": "1987-12-01",
        "head_birth_time": "辰時",
        "head_age": 38,
        "head_zodiac": "龍",
        "head_phone_home": "02-555",
        "head_phone_mobile": "0911-222",
        "head_email": "x@y.com",
        "head_address": "台中市",
        "head_zip_code": "400",
        "head_identity": "丁",
        "head_note": "note",
        "head_joined_at": "2026-01-13",
        # household_note 在 insert_household 沒寫入（你的 SQL 沒含這欄）
    }
    c.insert_household(data)

    rows = c.search_households("新增戶長")
    assert len(rows) == 1
    assert rows[0]["head_name"] == "新增戶長"


# -------------------------
# insert_member / get_member_by_id / update_member / delete_member_by_id
# -------------------------

def test_member_crud_via_controller_methods(controller_with_household_db, monkeypatch):
    c = controller_with_household_db
    hid = _insert_household_direct(c, head_name="王戶長")

    # 讓 uuid 固定，方便 assert
    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    monkeypatch.setattr(uuid, "uuid4", lambda: fixed_uuid)

    data = {
        "household_id": hid,
        "name": "測試戶員",
        "gender": "男",
        "birthday_ad": "2000-01-01",
        "birthday_lunar": "1999-12-01",
        "birth_time": "申時",
        "age": 26,
        "zodiac": "龍",
        "phone_home": "02-999",
        "phone_mobile": "0900-000",
        "email": "m@t.com",
        "address": "桃園市",
        "zip_code": "330",
        "identity": "口",
        "note": "note",
        "joined_at": "2026-01-13",
    }
    c.insert_member(data)

    person_id = str(fixed_uuid)
    got = c.get_member_by_id(person_id)
    assert got is not None
    assert got["name"] == "測試戶員"

    # update_member 需要更多欄位（你的 SQL 有 lunar_is_leap / id_number）
    update_data = dict(got)
    update_data.update({
        "name": "測試戶員(更新)",
        "lunar_is_leap": 0,
        "id_number": "Z123456789",
    })
    c.update_member(update_data)

    got2 = c.get_member_by_id(person_id)
    assert got2["name"] == "測試戶員(更新)"
    assert got2["id_number"] == "Z123456789"

    c.delete_member_by_id(person_id)
    assert c.get_member_by_id(person_id) is None
