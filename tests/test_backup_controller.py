import os
import sqlite3
from datetime import datetime

from app.controller.app_controller import AppController


def test_backup_defaults_and_save(tmp_path):
    db = tmp_path / "backup_defaults.db"
    controller = AppController(db_path=str(db))
    defaults = controller.get_backup_settings()
    assert defaults["enabled"] is False
    assert defaults["frequency"] == "daily"
    assert defaults["keep_latest"] == 20
    assert defaults["use_cli_scheduler"] is False
    assert defaults["enable_local"] is True
    assert defaults["enable_drive"] is False
    assert defaults["oauth_token_path"] == ""

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
            "oauth_client_secret_path": "/tmp/credentials.json",
            "oauth_token_path": "/tmp/token.json",
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
    assert data["oauth_client_secret_path"] == "/tmp/credentials.json"
    assert data["oauth_token_path"] == "/tmp/token.json"
    assert data["enable_local"] is True
    assert data["enable_drive"] is False

def test_backup_settings_ignore_legacy_drive_credentials_path(tmp_path):
    db = tmp_path / "backup_legacy_path.db"
    controller = AppController(db_path=str(db))
    controller.set_setting("backup/drive_credentials_path", "/tmp/legacy_credentials.json")
    controller.set_setting("backup/oauth_client_secret_path", "")
    data = controller.get_backup_settings()
    assert data["oauth_client_secret_path"] == ""


def test_create_local_backup_and_retention(tmp_path):
    db = tmp_path / "backup_retention.db"
    controller = AppController(db_path=str(db))
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

    logs = controller.list_backup_logs(limit=10)
    assert len(logs) >= 3
    assert logs[0]["status"] == "SUCCESS"


def test_should_run_scheduled_backup(tmp_path):
    db = tmp_path / "backup_schedule.db"
    controller = AppController(db_path=str(db))
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
    controller.mark_backup_run(now=datetime(2026, 2, 20, 12, 1))
    assert controller.should_run_scheduled_backup(now=datetime(2026, 2, 20, 12, 5)) is False


def test_run_scheduled_backup_once(tmp_path):
    db = tmp_path / "backup_schedule_run_once.db"
    controller = AppController(db_path=str(db))
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
