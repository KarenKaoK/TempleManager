from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def timestamp_for_filename() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_source_db(source_db: str, backup_dir: str, *, timestamp: str | None = None) -> str:
    source = Path(source_db)
    if not source.is_file():
        raise FileNotFoundError(f"Source DB not found: {source}")

    target_dir = Path(backup_dir)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Failed to create backup directory: {target_dir}") from exc

    stamp = timestamp or timestamp_for_filename()
    backup_name = f"{source.stem}_{stamp}{source.suffix or '.db'}"
    backup_path = target_dir / backup_name
    if backup_path.exists():
        raise FileExistsError(f"Backup already exists: {backup_path}")

    src_conn = None
    dst_conn = None
    try:
        src_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        dst_conn = sqlite3.connect(str(backup_path))
        src_conn.backup(dst_conn)
        dst_conn.commit()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to back up source DB {source} to {backup_path}: {exc}") from exc
    finally:
        if dst_conn is not None:
            dst_conn.close()
        if src_conn is not None:
            src_conn.close()

    return str(backup_path)
