import sqlite3
import pytest

from app.controller.app_controller import AppController


@pytest.fixture
def controller_with_household_db(tmp_path):
    db_path = tmp_path / "test_household_people.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

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

    conn.commit()
    conn.close()

    controller = AppController(db_path=str(db_path))
    yield controller

    try:
        controller.conn.close()
    except Exception:
        pass


def _new_head_payload(name="王大明", mobile="0912000000"):
    return {
        "name": name,
        "gender": "男",
        "birthday_ad": "1980-01-01",
        "birthday_lunar": "1979-12-01",
        "birth_time": "子時",
        "phone_mobile": mobile,
        "address": "台北市",
        "phone_home": "02-1111-2222",
        "note": "戶長備註",
    }


def _new_member_payload(name="王小明", mobile="0933000000"):
    return {
        "name": name,
        "gender": "男",
        "birthday_ad": "2000-02-02",
        "birthday_lunar": "1999-12-10",
        "birth_time": "午時",
        "phone_mobile": mobile,
        "address": "台北市",
        "phone_home": "02-3333-4444",
        "note": "戶員備註",
    }


def test_create_household_then_list_household_by_name_and_phone(controller_with_household_db):
    c = controller_with_household_db
    _, _ = c.create_household(_new_head_payload(name="王大明", mobile="0912000000"))
    _, _ = c.create_household(_new_head_payload(name="陳小華", mobile="0933999000"))

    rows = c.list_household(keyword="王")
    assert len(rows) == 1
    assert rows[0]["name"] == "王大明"

    rows2 = c.list_household(keyword="0933")
    assert len(rows2) == 1
    assert rows2[0]["name"] == "陳小華"


def test_search_by_any_name_when_keyword_matches_head(controller_with_household_db):
    c = controller_with_household_db
    head_id, household_id = c.create_household(_new_head_payload(name="王大明", mobile="0912000000"))
    _ = c.create_people(head_id, _new_member_payload(name="小孩A", mobile="0912333444"))

    head_row, members = c.search_by_any_name("王")

    assert head_row is not None
    assert head_row["name"] == "王大明"
    assert head_row["household_id"] == household_id
    assert any(m["name"] == "小孩A" for m in members)


def test_search_by_any_name_when_keyword_matches_member(controller_with_household_db):
    c = controller_with_household_db
    head_id, _ = c.create_household(_new_head_payload(name="戶長B", mobile="0922000000"))
    _ = c.create_people(head_id, _new_member_payload(name="關鍵戶員", mobile="0922333444"))

    head_row, members = c.search_by_any_name("關鍵")
    assert head_row is not None
    assert head_row["name"] == "戶長B"
    assert any(m["name"] == "關鍵戶員" for m in members)


def test_search_by_any_name_not_found(controller_with_household_db):
    c = controller_with_household_db
    _ = c.create_household(_new_head_payload(name="某戶長", mobile="0966000000"))
    head_row, members = c.search_by_any_name("不存在")
    assert head_row is None
    assert members == []


def test_list_people_by_household_returns_head_then_members(controller_with_household_db):
    c = controller_with_household_db
    head_id, household_id = c.create_household(_new_head_payload(name="王戶長", mobile="0911000000"))
    m1 = c.create_people(head_id, _new_member_payload(name="戶員1", mobile="0911222333"))
    m2 = c.create_people(head_id, _new_member_payload(name="戶員2", mobile="0911444555"))

    members = c.list_people_by_household(household_id)
    assert len(members) == 3
    assert members[0]["role_in_household"] == "HEAD"
    assert members[0]["id"] == head_id
    member_ids = {x["id"] for x in members[1:]}
    assert member_ids == {m1, m2}


def test_create_people_requires_active_head(controller_with_household_db):
    c = controller_with_household_db
    with pytest.raises(ValueError, match="head person not found"):
        c.create_people("NON_EXIST_HEAD", _new_member_payload())


def test_update_person_updates_allowed_fields(controller_with_household_db):
    c = controller_with_household_db
    head_id, _ = c.create_household(_new_head_payload(name="更新前", mobile="0900000000"))
    rc = c.update_person(head_id, {"name": "更新後", "phone_mobile": "0900999888", "note": "新備註"})
    assert rc == 1

    row = c.conn.cursor().execute(
        "SELECT name, phone_mobile, note FROM people WHERE id = ?",
        (head_id,),
    ).fetchone()
    assert row["name"] == "更新後"
    assert row["phone_mobile"] == "0900999888"
    assert row["note"] == "新備註"


def test_get_household_people_by_person_id_returns_same_household_members(controller_with_household_db):
    c = controller_with_household_db
    head_id, household_id = c.create_household(_new_head_payload(name="王戶長", mobile="0977000000"))
    member_id = c.create_people(head_id, _new_member_payload(name="戶員A", mobile="0977111222"))

    rows = c.get_household_people_by_person_id(member_id)
    assert len(rows) == 2
    assert {r["household_id"] for r in rows} == {household_id}
    assert {r["name"] for r in rows} == {"王戶長", "戶員A"}
