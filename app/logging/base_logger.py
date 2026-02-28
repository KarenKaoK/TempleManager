from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
from threading import Lock
from typing import Final

_WRITE_LOCK: Final[Lock] = Lock()
_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
LOG_FILE_PATH: Final[Path] = _PROJECT_ROOT / "log.log"
_ALLOWED_LEVELS = {"INFO", "WARN", "ERROR"}
_ALLOWED_TAGS = {"SYSTEM", "DATA"}
_REDACTED = "[REDACTED]"
_SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\b(password|passwd|pwd|token|secret|authorization|api[_-]?key|id_number)\b\s*([:=：])\s*([^\s,，;；\)）]+)"
    ),
    re.compile(r"(身分證字號)\s*([:=：])\s*([^\s,，;；\)）]+)"),
)
_ROC_ID_PATTERN = re.compile(r"\b[A-Z][12]\d{8}\b")


def _normalize_level(level: str) -> str:
    lv = str(level or "INFO").strip().upper()
    return lv if lv in _ALLOWED_LEVELS else "INFO"


def _normalize_tag(tag: str) -> str:
    tg = str(tag or "SYSTEM").strip().upper()
    return tg if tg in _ALLOWED_TAGS else "SYSTEM"


def _sanitize_message(message: str) -> str:
    text = str(message or "")
    for p in _SENSITIVE_PATTERNS:
        text = p.sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}", text)
    text = _ROC_ID_PATTERN.sub(_REDACTED, text)
    return text


def _harden_log_file_permissions(path: Path) -> None:
    # best-effort: 在支援 chmod 的系統把 log 權限縮到使用者可讀寫
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def write_log(*, level: str, tag: str, message: str) -> None:
    """
    統一輸出格式：
    YYYY-MM-DD HH:MM:SS [LEVEL] [DATA|SYSTEM] 內容描述
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lv = _normalize_level(level)
    tg = _normalize_tag(tag)
    text = _sanitize_message(str(message or "").strip() or "-")
    line = f"{ts} [{lv}] [{tg}] {text}\n"

    with _WRITE_LOCK:
        with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
        _harden_log_file_permissions(LOG_FILE_PATH)
