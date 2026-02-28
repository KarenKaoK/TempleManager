from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Final

_WRITE_LOCK: Final[Lock] = Lock()
_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
LOG_FILE_PATH: Final[Path] = _PROJECT_ROOT / "log.log"
_ALLOWED_LEVELS = {"INFO", "WARN", "ERROR"}
_ALLOWED_TAGS = {"SYSTEM", "DATA"}


def _normalize_level(level: str) -> str:
    lv = str(level or "INFO").strip().upper()
    return lv if lv in _ALLOWED_LEVELS else "INFO"


def _normalize_tag(tag: str) -> str:
    tg = str(tag or "SYSTEM").strip().upper()
    return tg if tg in _ALLOWED_TAGS else "SYSTEM"


def write_log(*, level: str, tag: str, message: str) -> None:
    """
    統一輸出格式：
    YYYY-MM-DD HH:MM:SS [LEVEL] [DATA|SYSTEM] 內容描述
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lv = _normalize_level(level)
    tg = _normalize_tag(tag)
    text = str(message or "").strip() or "-"
    line = f"{ts} [{lv}] [{tg}] {text}\n"

    with _WRITE_LOCK:
        with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
