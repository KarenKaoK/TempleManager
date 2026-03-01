import os
import sqlite3
from datetime import datetime
import pytest
import app.controller.app_controller as app_controller_module

from app.controller.app_controller import AppController
from app.database.setup_db import create_security_tables


def _new_backup_controller(db_path):
    create_security_tables(str(db_path))
    return AppController(db_path=str(db_path))


def _mock_backup_logs(monkeypatch):
    calls = {"data": [], "system": []}

    def fake_data(*args, **kwargs):
        calls["data"].append({"args": args, "kwargs": kwargs})

    def fake_system(message: str, level: str = "INFO"):
        calls["system"].append({"message": message, "level": level})

    monkeypatch.setattr("app.controller.app_controller.log_data_change", fake_data)
    monkeypatch.setattr("app.controller.app_controller.log_system", fake_system)
    return calls


def test_backup_defaults_and_save(tmp_path, monkeypatch):
    logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "backup_defaults.db"
    controller = _new_backup_controller(db)
    defaults = controller.get_backup_settings()
    assert defaults["enabled"] is False
    assert defaults["frequency"] == "daily"
    assert defaults["keep_latest"] == 20
    assert defaults["use_cli_scheduler"] is False
    assert defaults["enable_local"] is True
    assert defaults["enable_drive"] is False
    assert defaults["drive_credentials_path"] == ""
    assert defaults["last_scheduled_run_at"] == ""

    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "weekly",
            "time": "22:30",
            "weekday": 5,
            "monthday": 8,
            "keep_latest": 7,
            "local_dir": str(tmp_path / "bkp"),
            "drive_folder_id": "folder_x",
            "drive_credentials_path": "/tmp/credentials.json",
            "enable_local": True,
            "enable_drive": False,
            "use_cli_scheduler": True,
        }
    )
    data = controller.get_backup_settings()
    assert data["enabled"] is True
    assert data["frequency"] == "weekly"
    assert data["time"] == "22:30"
    assert data["weekday"] == 5
    assert data["keep_latest"] == 7
    assert data["drive_folder_id"] == "folder_x"
    assert data["use_cli_scheduler"] is True
    assert data["drive_credentials_path"] == "/tmp/credentials.json"
    assert data["enable_local"] is True
    assert data["enable_drive"] is False
    assert any(
        call["kwargs"].get("action") == "BACKUP.SETTINGS.UPDATE"
        for call in logs["data"]
    )

def test_backup_settings_read_drive_credentials_path(tmp_path):
    db = tmp_path / "backup_legacy_path.db"
    controller = _new_backup_controller(db)
    controller.set_setting("backup/drive_credentials_path", "/tmp/credentials.json")
    data = controller.get_backup_settings()
    assert data["drive_credentials_path"] == "/tmp/credentials.json"


def test_create_local_backup_and_retention(tmp_path, monkeypatch):
    mock_logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "backup_retention.db"
    controller = _new_backup_controller(db)
    backup_dir = tmp_path / "backups"
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "00:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 2,
            "local_dir": str(backup_dir),
        }
    )

    controller.create_local_backup(manual=True, now=datetime(2026, 2, 20, 10, 0, 1))
    controller.create_local_backup(manual=True, now=datetime(2026, 2, 20, 10, 0, 2))
    controller.create_local_backup(manual=True, now=datetime(2026, 2, 20, 10, 0, 3))

    files = sorted([p for p in os.listdir(backup_dir) if p.endswith(".db")])
    assert len(files) == 2

    backup_logs = controller.list_backup_logs(limit=10)
    assert len(backup_logs) >= 3
    assert backup_logs[0]["status"] == "SUCCESS"
    assert any(
        call["kwargs"].get("action") == "BACKUP.RUN.SUCCESS"
        for call in mock_logs["data"]
    )


def test_create_local_backup_without_target_writes_system_log(tmp_path, monkeypatch):
    logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "backup_without_target.db"
    controller = _new_backup_controller(db)
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "00:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 20,
            "local_dir": str(tmp_path / "backups"),
            "enable_local": False,
            "enable_drive": False,
        }
    )
    import pytest
    with pytest.raises(ValueError, match="請至少啟用一種備份目的地"):
        controller.create_local_backup(manual=True, now=datetime(2026, 2, 20, 10, 0, 1))

    assert any(
        call.get("level") in {"WARN", "ERROR"} and "執行備份失敗" in call.get("message", "")
        for call in logs["system"]
    )


def test_should_run_scheduled_backup(tmp_path):
    db = tmp_path / "backup_schedule.db"
    controller = _new_backup_controller(db)
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "12:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 20,
            "local_dir": str(tmp_path / "backups"),
        }
    )

    assert controller.should_run_scheduled_backup(now=datetime(2026, 2, 20, 11, 59)) is False
    assert controller.should_run_scheduled_backup(now=datetime(2026, 2, 20, 12, 0)) is True
    controller.mark_backup_run(now=datetime(2026, 2, 20, 12, 1), scheduled=True)
    assert controller.should_run_scheduled_backup(now=datetime(2026, 2, 20, 12, 5)) is False


def test_run_scheduled_backup_once(tmp_path):
    db = tmp_path / "backup_schedule_run_once.db"
    controller = _new_backup_controller(db)
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "12:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 20,
            "local_dir": str(tmp_path / "backups"),
        }
    )

    assert controller.run_scheduled_backup_once(now=datetime(2026, 2, 20, 11, 0)) is False
    assert controller.run_scheduled_backup_once(now=datetime(2026, 2, 20, 12, 1)) is True
    data = controller.get_backup_settings()
    assert data["last_scheduled_run_at"] == "2026-02-20 12:01:00"


def test_manual_backup_mark_does_not_block_scheduled_backup(tmp_path):
    db = tmp_path / "backup_schedule_manual_not_block.db"
    controller = _new_backup_controller(db)
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "18:50",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 20,
            "local_dir": str(tmp_path / "backups"),
        }
    )

    # 手動備份只更新 last_run_at，不應阻擋排程
    controller.mark_backup_run(now=datetime(2026, 2, 20, 18, 40), scheduled=False)
    assert controller.should_run_scheduled_backup(now=datetime(2026, 2, 20, 18, 50)) is True


def test_scheduler_feature_settings_defaults_and_save(tmp_path, monkeypatch):
    logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "scheduler_feature_settings.db"
    controller = _new_backup_controller(db)

    defaults = controller.get_scheduler_feature_settings()
    assert defaults["mail_enabled"] is True
    assert defaults["backup_enabled"] is True

    controller.save_scheduler_feature_settings(
        {
            "mail_enabled": False,
            "backup_enabled": True,
        }
    )
    data = controller.get_scheduler_feature_settings()
    assert data["mail_enabled"] is False
    assert data["backup_enabled"] is True
    assert any(
        call["kwargs"].get("action") == "SCHEDULER.FEATURE_FLAGS.UPDATE"
        for call in logs["data"]
    )


def test_scheduler_config_path_defaults_and_save(tmp_path, monkeypatch):
    logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "scheduler_config_path.db"
    controller = _new_backup_controller(db)
    assert controller.get_scheduler_config_path() == "app/scheduler/scheduler_config.yaml"
    controller.save_scheduler_config_path("/tmp/custom_scheduler.yaml")
    assert controller.get_scheduler_config_path() == "/tmp/custom_scheduler.yaml"
    assert any(
        call["kwargs"].get("action") == "SCHEDULER.CONFIG_PATH.UPDATE"
        for call in logs["data"]
    )


def test_scheduler_mail_settings_store_secret(tmp_path, monkeypatch):
    logs = _mock_backup_logs(monkeypatch)
    db = tmp_path / "scheduler_mail_settings.db"
    controller = _new_backup_controller(db)

    monkeypatch.setattr(app_controller_module.secret_store, "backend_label", lambda: "Windows Credential Manager")
    monkeypatch.setattr(app_controller_module.secret_store, "has_secret", lambda _k: True)
    monkeypatch.setattr(app_controller_module.secret_store, "set_secret", lambda _k, _v: None)
    monkeypatch.setattr(app_controller_module.secret_store, "get_secret", lambda _k: "app-password")

    controller.save_scheduler_mail_settings("temple@gmail.com", "app-password")
    info = controller.get_scheduler_mail_settings()
    assert info["smtp_username"] == "temple@gmail.com"
    assert info["smtp_password_set"] is True
    assert info["secret_backend"] == "Windows Credential Manager"

    user, pwd = controller.get_scheduler_mail_credentials()
    assert user == "temple@gmail.com"
    assert pwd == "app-password"
    assert any(
        call["kwargs"].get("action") == "SCHEDULER.MAIL_SETTINGS.UPDATE"
        for call in logs["data"]
    )


def test_authorize_google_drive_oauth_without_token_path_does_not_fallback(tmp_path, monkeypatch):
    db = tmp_path / "backup_oauth_no_token_path.db"
    controller = _new_backup_controller(db)
    captured = {}

    class _AboutRequest:
        def execute(self):
            return {"user": {"emailAddress": "drive@example.com"}}

    class _AboutApi:
        def get(self, fields=None):
            return _AboutRequest()

    class _Service:
        def about(self):
            return _AboutApi()

    def _fake_build_drive_service_oauth(
        oauth_client_secret_path: str,
        interactive: bool,
    ):
        captured["oauth_client_secret_path"] = oauth_client_secret_path
        captured["interactive"] = interactive
        return _Service()

    monkeypatch.setattr(controller, "_build_drive_service_oauth", _fake_build_drive_service_oauth)
    result = controller.authorize_google_drive_oauth("/tmp/credentials.json")
    assert captured["interactive"] is True
    assert result == {"email": "drive@example.com"}


def test_create_local_backup_hardens_permissions_best_effort(tmp_path):
    db = tmp_path / "backup_perm_hardening.db"
    controller = _new_backup_controller(db)
    backup_dir = tmp_path / "secure_backups"
    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "00:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 3,
            "local_dir": str(backup_dir),
            "enable_local": True,
            "enable_drive": False,
        }
    )

    chmod_calls = []
    real_chmod = app_controller_module.os.chmod

    def _spy_chmod(path, mode):
        chmod_calls.append((str(path), int(mode)))
        return real_chmod(path, mode)

    mp = pytest.MonkeyPatch()
    mp.setattr(app_controller_module.os, "chmod", _spy_chmod)
    try:
        result = controller.create_local_backup(manual=True, now=datetime(2026, 3, 1, 10, 0, 0))
    finally:
        mp.undo()

    assert any(p == str(backup_dir) and m == 0o700 for p, m in chmod_calls)
    assert any(p == str(result["backup_file"]) and m == 0o600 for p, m in chmod_calls)
