from typing import Any
from .base_logger import write_log


def _compose_message(action: str, actor: str, target: str, detail: str) -> str:
    parts = []
    if actor:
        parts.append(actor)
    if action:
        parts.append(action)
    if target:
        parts.append(f"目標 {target}")
    text = " ".join(parts).strip()
    if detail:
        text = f"{text}（{detail}）" if text else detail
    return text or "-"


def log_data_change(message: str = "", level: str = "INFO", **kwargs: Any) -> None:
    """寫入資料異動 log（[DATA]）。"""
    action = str(kwargs.get("action") or "").strip()
    actor = str(kwargs.get("actor") or "").strip()
    target = str(kwargs.get("target") or "").strip()
    detail = str(kwargs.get("detail") or "").strip()
    text = str(message or "").strip() or _compose_message(action, actor, target, detail)
    write_log(level=level, tag="DATA", message=text)
