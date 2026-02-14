# app/utils/lunar_solar_converter.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

try:
    from lunardate import LunarDate
except Exception as e:
    LunarDate = None


def _require_lib():
    if LunarDate is None:
        raise RuntimeError("缺少套件 lunardate，請先執行：pip install lunardate")


def _parse_ymd(s: str) -> tuple[int, int, int]:
    s = (s or "").strip()
    try:
        dt = datetime.strptime(s, "%Y/%m/%d")
        return dt.year, dt.month, dt.day
    except Exception:
        raise ValueError("日期格式需為 YYYY/MM/DD")


def solar_to_lunar(solar_ymd: str) -> tuple[str, int]:
    """
    solar_ymd: 'YYYY/MM/DD'
    return: (lunar_ymd_str, is_leap_int)
    """
    _require_lib()
    y, m, d = _parse_ymd(solar_ymd)
    ld = LunarDate.fromSolarDate(y, m, d)

    # lunardate 的 leap month 支援：ld.isLeapMonth (不同版本可能是 .isLeapMonth 或 .leap)
    is_leap = int(getattr(ld, "isLeapMonth", False) or getattr(ld, "leap", False) or False)
    lunar_str = f"{ld.year:04d}/{ld.month:02d}/{ld.day:02d}"
    return lunar_str, is_leap


def lunar_to_solar(lunar_ymd: str, is_leap: int = 0) -> str:
    """
    lunar_ymd: 'YYYY/MM/DD'
    is_leap: 0/1
    return: solar_ymd_str
    """
    _require_lib()
    y, m, d = _parse_ymd(lunar_ymd)

    # LunarDate(year, month, day, isLeapMonth=False)
    ld = LunarDate(y, m, d, bool(int(is_leap)))
    sd = ld.toSolarDate()
    return sd.strftime("%Y/%m/%d")
