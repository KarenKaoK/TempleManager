import pytest
import sqlite3
from datetime import datetime
from app.controller.app_controller import AppController

@pytest.fixture
def controller(tmp_path):
    db_path = tmp_path / "test_receipt.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create necessary table
    cur.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            date TEXT,
            type TEXT,
            category_id TEXT,
            category_name TEXT,
            amount INTEGER,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            note TEXT,
            receipt_number TEXT,
            created_at TEXT,
            is_deleted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    
    return AppController(db_path=str(db_path))

def test_generate_first_receipt_number(controller):
    """測試該年度第一張收據"""
    # 假設今天是 2024-01-01 (民國113年)
    date_str = "2024-01-01"
    
    # 資料庫為空，應產生 1130001
    receipt_num = controller.generate_receipt_number(date_str)
    assert receipt_num == "1130001"

def test_generate_next_receipt_number(controller):
    """測試流水號遞增"""
    date_str = "2024-02-01" # 113年
    
    # 模擬資料庫已有一筆 1130005
    cur = controller.conn.cursor()
    cur.execute("INSERT INTO transactions (id, receipt_number) VALUES (?, ?)", 
                ("T1", "1130005"))
    controller.conn.commit()
    
    # 應產生 1130006
    receipt_num = controller.generate_receipt_number(date_str)
    assert receipt_num == "1130006"

def test_generate_receipt_number_year_change(controller):
    """測試跨年號碼重置"""
    # 模擬資料庫有 113 年的資料
    cur = controller.conn.cursor()
    cur.execute("INSERT INTO transactions (id, receipt_number) VALUES (?, ?)", 
                ("T1", "1139999"))
    controller.conn.commit()
    
    # 產生 2025 年 (114年) 的收據
    date_str = "2025-01-01"
    
    # 應產生 1140001 (不應延續 113 的號碼)
    receipt_num = controller.generate_receipt_number(date_str)
    assert receipt_num == "1140001"

def test_generate_receipt_number_fallback(controller):
    """測試日期格式錯誤時的 Fallback (使用當下日期)"""
    # 給一個錯誤的日期格式
    invalid_date = "invalid-date"
    
    receipt_num = controller.generate_receipt_number(invalid_date)
    
    # 預期會用當下年份
    now = datetime.now()
    roc_year = now.year - 1911
    expected_prefix = f"{roc_year}"
    
    assert receipt_num.startswith(expected_prefix)
    assert len(receipt_num) == len(expected_prefix) + 4
