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


def test_get_data_dir_uses_single_app_segment(monkeypatch):
    captured = {"appname": None, "appauthor": "NOT_SET"}

    def fake_user_data_dir(appname, appauthor=None, **kwargs):
        captured["appname"] = appname
        captured["appauthor"] = appauthor
        return "/tmp/TempleManager"

    monkeypatch.setattr(app_config, "user_data_dir", fake_user_data_dir)
    app_config.get_data_dir()
    assert captured == {"appname": "TempleManager", "appauthor": False}
