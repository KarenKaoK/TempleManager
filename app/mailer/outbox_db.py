# app/mailer/outbox_db.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS email_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        to_emails TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        attachments TEXT,               -- comma-separated absolute paths
        status TEXT NOT NULL,           -- SENT / FAILED
        error TEXT,
        created_at TEXT NOT NULL
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_job_id ON email_outbox(job_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_status ON email_outbox(status);")
    conn.commit()


def insert_record(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    to_emails: List[str],
    subject: str,
    body: str,
    attachments: List[str],
    status: str,
    error: Optional[str],
) -> int:
    ts = now_utc_iso()
    to_str = ",".join([e.strip() for e in to_emails if e and e.strip()])
    att_str = ",".join([a.strip() for a in attachments if a and a.strip()])

    cur = conn.execute(
        """
        INSERT INTO email_outbox(job_id,to_emails,subject,body,attachments,status,error,created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (job_id, to_str, subject, body, att_str, status, (error or "")[:2000], ts),
    )
    conn.commit()
    return int(cur.lastrowid)