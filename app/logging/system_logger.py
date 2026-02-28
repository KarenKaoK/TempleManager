from .base_logger import write_log


def log_system(message: str, level: str = "INFO") -> None:
    """寫入系統行為與錯誤 log（[SYSTEM]）。"""
    write_log(level=level, tag="SYSTEM", message=message)
