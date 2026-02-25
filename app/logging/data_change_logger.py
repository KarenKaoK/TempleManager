from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .system_logger import get_logger


_logger = get_logger("data_change")

# 信眾/戶籍 log 要記錄的欄位（依序）
_PERSON_LOG_KEYS = [
    "name",
    "gender",
    "birthday_ad",
    "birthday_lunar",
    "birth_time",
    "age",
    "zodiac",
    "phone_home",
    "phone_mobile",
    "address",
    "zip_code",
    "note",
    "lunar_is_leap",
    "role_in_household",
    "household_id",
    "status",
]


def person_snapshot_for_log(data: Optional[Mapping[str, Any]]) -> dict:
    """
    從 person 或 form data 擷取要寫入 log 的欄位，僅保留有值的欄位。
    用於新增戶長、新增成員、修改信眾、刪除/停用、恢復等資料異動 log。
    """
    if not data:
        return {}
    out = {}
    for k in _PERSON_LOG_KEYS:
        v = data.get(k)
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        out[k] = v
    return out


def _format_value(value: Any) -> str:
    """
    將值轉成適合寫入文字 log 的字串。
    """
    if value is None:
        return "NULL"
    try:
        return str(value)
    except Exception:
        return repr(value)


def log_data_change(
    *,
    user_id: Optional[str],
    action: str,
    entity: str,
    entity_id: Optional[str] = None,
    before: Optional[Mapping[str, Any]] = None,
    after: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    資料新增 / 刪除 / 異動 log。

    寫入格式採用人眼友善的中文敘述，例如：

        2026-02-24 15:01:12 [INFO] [DATA] data_change 登入更新最後登入時間變更，變更前：last_login_at=2026-02-23 21:59:07，變更後：last_login_at=2026-02-24 21:15:59
    """
    _ = datetime.now(timezone.utc)  # 保留時間物件以便未來需要擴充

    # 開頭固定為標籤與 logger 名稱
    segments = ["[DATA]", "data_change"]

    # 動作描述
    if action:
        segments.append(f"{_format_value(action)}變更")

    # 使用者 / 實體資訊（若有）
    middle_parts = []
    if user_id is not None:
        middle_parts.append(f"使用者={_format_value(user_id)}")
    if entity or entity_id is not None:
        entity_str = _format_value(entity) if entity else ""
        if entity_id is not None:
            entity_str = (entity_str + " ").strip()
            entity_str += f"ID={_format_value(entity_id)}"
        if entity_str:
            middle_parts.append(f"實體={entity_str}")
    if middle_parts:
        segments.append(" ".join(middle_parts))

    # 變更前 / 變更後欄位
    before_parts = []
    if before:
        for key, value in before.items():
            before_parts.append(f"{key}={_format_value(value)}")

    after_parts = []
    if after:
        for key, value in after.items():
            after_parts.append(f"{key}={_format_value(value)}")

    if before_parts:
        segments.append("變更前：" + " ".join(before_parts))
    if after_parts:
        segments.append("變更後：" + " ".join(after_parts))

    if extra:
        for key, value in extra.items():
            segments.append(f"額外_{key}={_format_value(value)}")
    if error:
        segments.append(f"錯誤={_format_value(error)}")

    # 使用全形逗號將語句片段串起來，更貼近自然語氣
    message = "，".join(segments[:3]) if len(segments) >= 3 else "，".join(segments)
    if len(segments) > 3:
        # 第 3 片段之後（變更前/後等）改用空白分隔，避免逗號過多
        tail = " ".join(segments[3:])
        if tail:
            message = f"{message} {tail}"

    _logger.info(message)

