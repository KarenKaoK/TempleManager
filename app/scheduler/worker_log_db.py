from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR


def worker_log_db_path(db_path: str | None = None) -> str:
    if db_path:
        return str(Path(db_path).resolve().parent / "worker_logs.db")
    return str(Path(DATA_DIR) / "worker_logs.db")


def connect(db_path: str | None = None) -> sqlite3.Connection:
    db_path = Path(worker_log_db_path(db_path=db_path))
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
        """
        CREATE TABLE IF NOT EXISTS worker_backup_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'daily',
            time_text TEXT NOT NULL DEFAULT '23:00',
            weekday INTEGER NOT NULL DEFAULT 1,
            monthday INTEGER NOT NULL DEFAULT 1,
            last_scheduled_run_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worker_reload_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            config_version INTEGER NOT NULL DEFAULT 0,
            reload_required INTEGER NOT NULL DEFAULT 0,
            last_applied_version INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT ''
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


def list_backup_logs(conn: sqlite3.Connection, *, limit: int = 100):
    lim = max(1, int(limit or 100))
    rows = conn.execute(
        """
        SELECT created_at, job_id, status, detail
        FROM worker_backup_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (lim,),
    ).fetchall()
    return [dict(r) for r in rows]


def upsert_backup_state(
    conn: sqlite3.Connection,
    *,
    enabled: bool,
    frequency: str,
    time_text: str,
    weekday: int,
    monthday: int,
    last_scheduled_run_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO worker_backup_state(id, enabled, frequency, time_text, weekday, monthday, last_scheduled_run_at)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            enabled=excluded.enabled,
            frequency=excluded.frequency,
            time_text=excluded.time_text,
            weekday=excluded.weekday,
            monthday=excluded.monthday,
            last_scheduled_run_at=excluded.last_scheduled_run_at
        """,
        (
            1 if bool(enabled) else 0,
            str(frequency or "daily"),
            str(time_text or "23:00"),
            int(weekday or 1),
            int(monthday or 1),
            str(last_scheduled_run_at or ""),
        ),
    )
    conn.commit()


def get_backup_state(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT enabled, frequency, time_text, weekday, monthday, last_scheduled_run_at
        FROM worker_backup_state
        WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return {
            "enabled": False,
            "frequency": "daily",
            "time_text": "23:00",
            "weekday": 1,
            "monthday": 1,
            "last_scheduled_run_at": "",
        }
    return {
        "enabled": bool(row["enabled"]),
        "frequency": str(row["frequency"] or "daily"),
        "time_text": str(row["time_text"] or "23:00"),
        "weekday": int(row["weekday"] or 1),
        "monthday": int(row["monthday"] or 1),
        "last_scheduled_run_at": str(row["last_scheduled_run_at"] or ""),
    }


def get_reload_state(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT config_version, reload_required, last_applied_version, updated_at
        FROM worker_reload_state
        WHERE id = 1
        """
    ).fetchone()
    if row is None:
        return {
            "config_version": 0,
            "reload_required": False,
            "last_applied_version": 0,
            "updated_at": "",
        }
    return {
        "config_version": int(row["config_version"] or 0),
        "reload_required": bool(row["reload_required"]),
        "last_applied_version": int(row["last_applied_version"] or 0),
        "updated_at": str(row["updated_at"] or ""),
    }


def request_reload(conn: sqlite3.Connection) -> int:
    state = get_reload_state(conn)
    next_version = int(state.get("config_version", 0)) + 1
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO worker_reload_state(id, config_version, reload_required, last_applied_version, updated_at)
        VALUES (1, ?, 1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            config_version=excluded.config_version,
            reload_required=1,
            updated_at=excluded.updated_at
        """,
        (next_version, int(state.get("last_applied_version", 0)), ts),
    )
    conn.commit()
    return next_version


def mark_reload_applied(conn: sqlite3.Connection, version: int) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO worker_reload_state(id, config_version, reload_required, last_applied_version, updated_at)
        VALUES (1, ?, 0, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            config_version=CASE
                WHEN worker_reload_state.config_version < excluded.config_version THEN excluded.config_version
                ELSE worker_reload_state.config_version
            END,
            reload_required=0,
            last_applied_version=excluded.last_applied_version,
            updated_at=excluded.updated_at
        """,
        (int(version), int(version), ts),
    )
    conn.commit()
