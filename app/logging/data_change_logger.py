from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from .system_logger import get_logger


_logger = get_logger("data_change")


def _make_serializable(value: Any) -> Any:
    """
    確保可以被 JSON 序列化；若不行則改用 repr。
    """
    try:
        json.dumps(value)
        return value
    except TypeError:
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

    寫入位置與一般系統 log 相同（log.log），但內容為單行 JSON 方便後續搜尋/分析。

    典型用法（例如新增/修改/刪除戶長）：

        log_data_change(
            user_id=current_user_id,
            action="HOUSEHOLDER.CREATE",
            entity="householder",
            entity_id=str(new_id),
            before=None,
            after={"name": name, "phone": phone},
        )
    """
    event: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": "data_change",
        "user_id": user_id,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "before": before,
        "after": after,
        "extra": extra,
        "error": error,
    }

    serializable_event = {
        key: _make_serializable(value) for key, value in event.items()
    }

    _logger.info(json.dumps(serializable_event, ensure_ascii=False))

