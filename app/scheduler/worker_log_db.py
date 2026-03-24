from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR


def worker_log_db_path() -> str:
    return str(Path(DATA_DIR) / "worker_logs.db")


def connect() -> sqlite3.Connection:
    db_path = Path(worker_log_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_event_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL,
            action TEXT NOT NULL,
            job_id TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_email_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            job_id TEXT NOT NULL,
            to_emails TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            attachments TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_backup_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            job_id TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_event_logs_created_at ON worker_event_logs(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_event_logs_action ON worker_event_logs(action)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_email_outbox_created_at ON worker_email_outbox(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_email_outbox_job_id ON worker_email_outbox(job_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_backup_logs_created_at ON worker_backup_logs(created_at)"
    )
    conn.commit()


def insert_event(
    conn: sqlite3.Connection,
    *,
    level: str,
    action: str,
    message: str,
    job_id: str = "",
) -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO worker_event_logs(created_at, level, action, job_id, message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ts, str(level or "INFO"), str(action or ""), str(job_id or ""), str(message or "")),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_email_outbox(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    to_emails: str,
    subject: str,
    body: str,
    attachments: str,
    status: str,
    error: str,
) -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO worker_email_outbox(created_at, job_id, to_emails, subject, body, attachments, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ts, job_id, to_emails, subject, body, attachments, status, error),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_backup_log(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    status: str,
    detail: str,
) -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO worker_backup_logs(created_at, job_id, status, detail)
        VALUES (?, ?, ?, ?)
        """,
        (ts, job_id, status, detail),
    )
    conn.commit()
    return int(cur.lastrowid)
