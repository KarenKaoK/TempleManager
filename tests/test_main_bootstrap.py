import sqlite3
from pathlib import Path

import app.main as main_module


def test_ensure_database_ready_skips_when_db_exists_and_schema_ready(tmp_path, monkeypatch):
    db_path = tmp_path / "exists.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.close()

    called = {"init": 0}
    monkeypatch.setattr(main_module, "initialize_database", lambda *_: called.__setitem__("init", called["init"] + 1))

    main_module.ensure_database_ready(str(db_path))

    assert called["init"] == 0


def test_ensure_database_ready_initializes_when_db_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "missing.db"
    called = {"arg": None}
    monkeypatch.setattr(main_module, "initialize_database", lambda arg: called.__setitem__("arg", arg))

    main_module.ensure_database_ready(str(db_path))
    assert called["arg"] == str(db_path)


def test_ensure_database_ready_initializes_when_schema_incomplete(tmp_path, monkeypatch):
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    conn.close()
    called = {"arg": None}
    monkeypatch.setattr(main_module, "initialize_database", lambda arg: called.__setitem__("arg", arg))
    main_module.ensure_database_ready(str(db_path))
    assert called["arg"] == str(db_path)
