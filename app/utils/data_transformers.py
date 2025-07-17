# app/utils/data_transformers.py

def convert_head_to_member_format(data: dict) -> dict:
    """
    將 household 的戶長資料轉換為 member 格式，
    以統一呈現在 member table 的欄位格式中。
    """
    mapping = {
            "name": "head_name",
            "gender": "head_gender",
            "birthday_ad": "head_birthday_ad",
            "birthday_lunar": "head_birthday_lunar",
            "zodiac": "head_zodiac",
            "age": "head_age",
            "birth_time": "head_birth_time",
            "phone_home": "head_phone_home",
            "phone_mobile": "head_phone_mobile",
            "id": "id",
            "address": "head_address",
            "email": "head_email",
            "note": "head_note"
        }
    result = {k: data.get(v, "") for k, v in mapping.items()}
    result["identity"] = "丁" if data.get("head_gender") == "男" else "口"
    return result

def convert_member_to_head_format(member: dict) -> dict:
    """
    將 people/member 格式轉換為 household 用的 head_ 前綴格式
    """
    return {f"head_{key}": value for key, value in member.items()}