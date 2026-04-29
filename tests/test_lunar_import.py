from lunar import build_person_payload


def test_build_person_payload_allows_name_and_address_only():
    payload, warnings = build_person_payload({
        "姓名": "王大明",
        "聯絡地址": "台北市信義區",
    })

    assert payload["name"] == "王大明"
    assert payload["address"] == "台北市信義區"
    assert payload["gender"] == ""
    assert payload["birthday_ad"] == ""
    assert payload["birthday_lunar"] == ""
    assert payload["birth_time"] == ""
    assert payload["phone_mobile"] == ""
    assert warnings == []
