from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from app.utils import secret_store


LOCAL_DATA_ENCRYPTION_KEY_CURRENT = "local/data_encryption_key/current"


def _read_valid_fernet_key(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    try:
        Fernet(text.encode("utf-8"))
        return text
    except Exception:
        return ""


def get_or_create_local_data_encryption_key() -> bytes:
    current = ""
    try:
        current = _read_valid_fernet_key(secret_store.get_secret(LOCAL_DATA_ENCRYPTION_KEY_CURRENT))
    except Exception:
        current = ""
    if current:
        return current.encode("utf-8")
    new_key = Fernet.generate_key().decode("utf-8")
    secret_store.set_secret(LOCAL_DATA_ENCRYPTION_KEY_CURRENT, new_key)
    return new_key.encode("utf-8")


def _best_effort_chmod(path: Path) -> None:
    try:
        os.chmod(str(path), 0o600)
    except Exception:
        pass


def ensure_runtime_db_ready(*, runtime_db_path: str, encrypted_db_path: str, legacy_plain_db_path: str = "") -> None:
    runtime = Path(runtime_db_path)
    enc = Path(encrypted_db_path)
    legacy = Path(legacy_plain_db_path) if legacy_plain_db_path else None
    runtime.parent.mkdir(parents=True, exist_ok=True)
    enc.parent.mkdir(parents=True, exist_ok=True)

    if runtime.exists():
        _best_effort_chmod(runtime)
        return

    if enc.is_file():
        try:
            plain = Fernet(get_or_create_local_data_encryption_key()).decrypt(enc.read_bytes())
        except Exception as e:
            raise RuntimeError(f"無法解密地端資料庫：{e}")
        runtime.write_bytes(plain)
        _best_effort_chmod(runtime)
        if not runtime.exists():
            raise RuntimeError(f"地端資料庫還原失敗：{runtime}")
        return

    if legacy is not None and legacy.is_file():
        runtime.write_bytes(legacy.read_bytes())
        _best_effort_chmod(runtime)
        try:
            legacy.unlink()
        except Exception:
            pass
        for suffix in ("-wal", "-shm"):
            extra = Path(str(legacy) + suffix)
            if extra.exists():
                try:
                    extra.unlink()
                except Exception:
                    pass
        if not runtime.exists():
            raise RuntimeError(f"地端資料庫搬移失敗：{runtime}")
        return

    raise RuntimeError(
        "找不到可用的地端資料庫。預期至少存在 temple.db.enc 或既有 temple.db。"
    )


def finalize_runtime_db(*, runtime_db_path: str, encrypted_db_path: str) -> None:
    runtime = Path(runtime_db_path)
    enc = Path(encrypted_db_path)
    if not runtime.exists():
        return

    conn = None
    try:
        conn = sqlite3.connect(str(runtime))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        if conn is not None:
            conn.close()

    plain = runtime.read_bytes()
    token = Fernet(get_or_create_local_data_encryption_key()).encrypt(plain)
    enc.parent.mkdir(parents=True, exist_ok=True)
    enc.write_bytes(token)
    _best_effort_chmod(enc)

    for suffix in ("", "-wal", "-shm"):
        target = Path(str(runtime) + suffix)
        if target.exists():
            try:
                target.unlink()
            except Exception:
                pass
