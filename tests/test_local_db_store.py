import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from app.utils import local_db_store


def _create_sqlite_db(path: Path) -> bytes:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO demo (name) VALUES ('ok')")
    conn.commit()
    conn.close()
    return path.read_bytes()


def test_ensure_runtime_db_ready_decrypts_encrypted_db(tmp_path, monkeypatch):
    runtime = tmp_path / "temple.db"
    enc = tmp_path / "temple.db.enc"
    plain_src = tmp_path / "plain.db"

    key = Fernet.generate_key().decode("utf-8")
    secret_map = {local_db_store.LOCAL_DATA_ENCRYPTION_KEY_CURRENT: key}
    monkeypatch.setattr(local_db_store.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(local_db_store.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))

    plain = _create_sqlite_db(plain_src)
    enc.write_bytes(Fernet(key.encode("utf-8")).encrypt(plain))

    local_db_store.ensure_runtime_db_ready(
        runtime_db_path=str(runtime),
        encrypted_db_path=str(enc),
        legacy_plain_db_path="",
    )

    conn = sqlite3.connect(str(runtime))
    try:
        row = conn.execute("SELECT name FROM demo").fetchone()
        assert row[0] == "ok"
    finally:
        conn.close()


def test_finalize_runtime_db_encrypts_and_removes_runtime_files(tmp_path, monkeypatch):
    runtime = tmp_path / "temple.db"
    enc = tmp_path / "temple.db.enc"

    key = Fernet.generate_key().decode("utf-8")
    secret_map = {local_db_store.LOCAL_DATA_ENCRYPTION_KEY_CURRENT: key}
    monkeypatch.setattr(local_db_store.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(local_db_store.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))

    runtime.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(runtime))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO demo (name) VALUES ('persisted')")
    conn.commit()
    conn.close()

    local_db_store.finalize_runtime_db(runtime_db_path=str(runtime), encrypted_db_path=str(enc))

    assert enc.exists() is True
    assert runtime.exists() is False
    assert Path(str(runtime) + "-wal").exists() is False
    assert Path(str(runtime) + "-shm").exists() is False

    restored = tmp_path / "restored.db"
    restored.write_bytes(Fernet(key.encode("utf-8")).decrypt(enc.read_bytes()))
    conn2 = sqlite3.connect(str(restored))
    try:
        row = conn2.execute("SELECT name FROM demo").fetchone()
        assert row[0] == "persisted"
    finally:
        conn2.close()


def test_ensure_runtime_db_ready_raises_when_no_encrypted_or_plain_db_exists(tmp_path, monkeypatch):
    runtime = tmp_path / "temple.db"
    enc = tmp_path / "temple.db.enc"

    key = Fernet.generate_key().decode("utf-8")
    secret_map = {local_db_store.LOCAL_DATA_ENCRYPTION_KEY_CURRENT: key}
    monkeypatch.setattr(local_db_store.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(local_db_store.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))

    try:
        local_db_store.ensure_runtime_db_ready(
            runtime_db_path=str(runtime),
            encrypted_db_path=str(enc),
            legacy_plain_db_path="",
        )
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "找不到可用的地端資料庫" in str(exc)
