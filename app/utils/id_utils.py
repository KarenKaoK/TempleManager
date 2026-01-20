# app/utils/id_utils.py
from __future__ import annotations

import time
from datetime import datetime
from PyQt5.QtCore import QDate

def generate_activity_id() -> str:
    """
    產生活動 ID：YYYYMMDDHHMMSS
    - 優點：可讀、可排序
    - 風險：同秒多筆可能撞；所以做一個「同秒內 sleep 重試」策略
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")


def generate_activity_id_safe(exists_fn, max_retry: int = 5) -> str:
    """
    安全版：避免同秒撞 PK
    exists_fn: callable(id) -> bool，用來查 DB 是否已存在
    策略：
      - 產生 YYYYMMDDHHMMSS
      - 如果存在就 sleep 0.2 秒，最多重試 max_retry 次
      - 最後仍撞：直接 raise
    """
    for _ in range(max_retry):
        aid = generate_activity_id()
        if not exists_fn(aid):
            return aid
        time.sleep(0.2)

    raise RuntimeError("無法產生唯一的活動ID（同秒建立過多筆），請稍後再試。")

def _compute_display_status(self, start_qdate: QDate, end_qdate: QDate) -> str:
    today = QDate.currentDate()
    if today < start_qdate:
        return "未開始"
    if today > end_qdate:
        return "已結束"
    return "進行中"