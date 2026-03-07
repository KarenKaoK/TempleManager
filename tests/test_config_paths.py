from pathlib import Path

import app.config as app_config


def test_resolve_db_name_prefers_env(monkeypatch, tmp_path):
    env_db = tmp_path / "custom.db"
    monkeypatch.setenv("TEMPLEMANAGER_DB_PATH", str(env_db))

    result = app_config.resolve_db_name(data_dir=tmp_path / "data")

    assert result == str(env_db)


def test_resolve_db_name_uses_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("TEMPLEMANAGER_DB_PATH", raising=False)
    data_dir = tmp_path / "data"

    result = app_config.resolve_db_name(data_dir=data_dir)

    assert result == str(data_dir / "temple.db")
