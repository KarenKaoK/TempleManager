from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
from threading import Lock
from typing import Final
import app.utils.secret_store as secret_store
from cryptography.fernet import Fernet

_WRITE_LOCK: Final[Lock] = Lock()
_PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
LOG_FILE_PATH: Final[Path] = _PROJECT_ROOT / "log.log"
LOG_ENCRYPTION_SECRET_KEY: Final[str] = "logging/file_encryption_fernet_key"
_ALLOWED_LEVELS = {"INFO", "WARN", "ERROR"}
_ALLOWED_TAGS = {"SYSTEM", "DATA"}
_REDACTED = "[REDACTED]"
_SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\b(password|passwd|pwd|token|secret|authorization|api[_-]?key|id_number)\b\s*([:=：])\s*([^\s,，;；\)）]+)"
    ),
    re.compile(r"(身分證字號)\s*([:=：])\s*([^\s,，;；\)）]+)"),
)
_SENSITIVE_QUOTED_VALUE_PATTERNS = (
    re.compile(
        r"""(?ix)
        ("?(?:access_token|refresh_token|id_token|client_secret|authorization_code|password|passwd|pwd|token|secret|api[_-]?key|id_number)"?\s*[:=]\s*["'])
        ([^"']+)
        (["'])
        """
    ),
    re.compile(
        r"""(?ix)
        (['"](?:access_token|refresh_token|id_token|client_secret|authorization_code|password|passwd|pwd|token|secret|api[_-]?key|id_number)['"]\s*:\s*['"])
        ([^'"]+)
        (['"])
        """
    ),
)
_SENSITIVE_UNQUOTED_VALUE_PATTERNS = (
    re.compile(
        r"""(?ix)
        ("?(?:access_token|refresh_token|id_token|client_secret|authorization_code|password|passwd|pwd|token|secret|api[_-]?key|id_number)"?\s*[:=]\s*)
        ([^\s,，;；\)）\}\]]+)
        """
    ),
)
_BEARER_PATTERN = re.compile(r"(?i)\b((?:authorization|auth)\s*[:=]\s*bearer\s+)([A-Za-z0-9._~+\-/=]+)")
_QUERY_TOKEN_PATTERN = re.compile(
    r"(?i)\b((?:access_token|refresh_token|id_token|client_secret|authorization_code|code)=)([^&\s]+)"
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
    # 先處理 Bearer 與 query token，避免被一般 key/value 規則先吃掉而漏遮罩
    text = _BEARER_PATTERN.sub(lambda m: f"{m.group(1)}{_REDACTED}", text)
    text = _QUERY_TOKEN_PATTERN.sub(lambda m: f"{m.group(1)}{_REDACTED}", text)
    for p in _SENSITIVE_PATTERNS:
        text = p.sub(lambda m: f"{m.group(1)}{m.group(2)}{_REDACTED}", text)
    for p in _SENSITIVE_QUOTED_VALUE_PATTERNS:
        text = p.sub(lambda m: f"{m.group(1)}{_REDACTED}{m.group(3)}", text)
    for p in _SENSITIVE_UNQUOTED_VALUE_PATTERNS:
        text = p.sub(lambda m: f"{m.group(1)}{_REDACTED}", text)
    text = _ROC_ID_PATTERN.sub(_REDACTED, text)
    return text


def _harden_log_file_permissions(path: Path) -> None:
    # best-effort: 在支援 chmod 的系統把 log 權限縮到使用者可讀寫
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _get_or_create_log_fernet_key() -> bytes:
    try:
        existing = (secret_store.get_secret(LOG_ENCRYPTION_SECRET_KEY) or "").strip()
    except Exception:
        existing = ""
    if existing:
        key = existing.encode("utf-8")
        Fernet(key)  # 驗證 key 格式
        return key
    key = Fernet.generate_key()
    secret_store.set_secret(LOG_ENCRYPTION_SECRET_KEY, key.decode("utf-8"))
    return key


def _encrypt_line(line: str) -> str:
    f = Fernet(_get_or_create_log_fernet_key())
    return f.encrypt(line.encode("utf-8")).decode("utf-8")


def _decrypt_line(token: str) -> str:
    f = Fernet(_get_or_create_log_fernet_key())
    # 不做舊明文 fallback：解不開直接拋錯
    return f.decrypt((token or "").strip().encode("utf-8")).decode("utf-8")


def _decode_log_lines(lines) -> str:
    out_lines = []
    for raw in lines:
        text = (raw or "").strip()
        if not text:
            continue
        out_lines.append(_decrypt_line(text))
    return "\n".join(out_lines).strip()


def read_log_text() -> str:
    if not LOG_FILE_PATH.exists():
        return ""
    return _decode_log_lines(LOG_FILE_PATH.read_text(encoding="utf-8").splitlines())


def read_log_tail_text(max_lines: int = 1000) -> str:
    if not LOG_FILE_PATH.exists():
        return ""
    if max_lines <= 0:
        return ""
    lines = LOG_FILE_PATH.read_text(encoding="utf-8").splitlines()
    return _decode_log_lines(lines[-max_lines:])


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
    encrypted_line = _encrypt_line(line.rstrip("\n"))

    with _WRITE_LOCK:
        with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
            f.write(encrypted_line + "\n")
        _harden_log_file_permissions(LOG_FILE_PATH)
