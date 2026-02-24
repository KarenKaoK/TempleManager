from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


LOG_FILE_NAME = "log.log"


def _get_log_file_path() -> Path:
    """
    回傳 log 檔案路徑。
    目前設計為專案根目錄底下的 log.log。
    """
    # app/logging/system_logger.py -> parents[2] = .../TempleManager
    project_root = Path(__file__).resolve().parents[2]
    return project_root / LOG_FILE_NAME


def _configure_base_logger() -> logging.Logger:
    """
    建立並設定共用 logger（只建立一次）。
    """
    logger = logging.getLogger("temple")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_path = _get_log_file_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 避免訊息再往 root logger 傳，導致重複輸出到 stdout。
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    取得共用 logger 或其子 logger。
    """
    base = _configure_base_logger()
    if not name or name == base.name:
        return base
    return base.getChild(name)


def log_info(message: str, **context: Any) -> None:
    logger = get_logger()
    if context:
        message = f"{message} | {context}"
    logger.info(message)


def log_warning(message: str, **context: Any) -> None:
    logger = get_logger()
    if context:
        message = f"{message} | {context}"
    logger.warning(message)


def log_error(message: str, **context: Any) -> None:
    """
    一般錯誤 log，不需要 stack trace。
    若需要 stack trace，請在 except 區塊使用 log_exception。
    """
    logger = get_logger()
    if context:
        message = f"{message} | {context}"
    logger.error(message)


def log_exception(message: str, **context: Any) -> None:
    """
    在 except 區塊中呼叫，會自動附帶 stack trace。

    try:
        ...
    except Exception:
        log_exception("something failed", job_id=job_id)
    """
    logger = get_logger()
    if context:
        message = f"{message} | {context}"
    logger.exception(message)

