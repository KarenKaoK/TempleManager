import os
import sqlite3
from datetime import datetime
import pytest
from cryptography.fernet import Fernet
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

    expected_default = str((tmp_path / "scheduler_config.yaml").resolve())
    assert controller.get_scheduler_config_path() == expected_default
    assert os.path.isfile(expected_default) is True

    custom = tmp_path / "custom_scheduler.yaml"
    controller.save_scheduler_config_path(str(custom))
    assert controller.get_scheduler_config_path() == str(custom.resolve())
    assert os.path.isfile(str(custom.resolve())) is True

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


def test_drive_backup_uploads_encrypted_file_and_cleans_temp_enc(tmp_path, monkeypatch):
    db = tmp_path / "backup_drive_encrypted.db"
    controller = _new_backup_controller(db)
    backup_dir = tmp_path / "backups"

    secret_map = {}
    monkeypatch.setattr(app_controller_module.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(app_controller_module.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))
    monkeypatch.setattr(app_controller_module.secret_store, "delete_secret", lambda k: secret_map.pop(k, None))
    monkeypatch.setattr(app_controller_module.secret_store, "backend_label", lambda: "TestSecretStore")

    captured = {}

    def _fake_upload(local_file: str, folder_id: str, oauth_client_secret_path: str, keep_latest: int):
        captured["local_file"] = local_file
        captured["folder_id"] = folder_id
        with open(local_file, "rb") as f:
            captured["head"] = f.read(16)
        return ("drive-file-1", "backup-folder")

    monkeypatch.setattr(controller, "_upload_backup_to_drive", _fake_upload)

    controller.save_backup_settings(
        {
            "enabled": True,
            "frequency": "daily",
            "time": "00:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 3,
            "local_dir": str(backup_dir),
            "drive_folder_id": "folder123",
            "drive_credentials_path": "/tmp/credentials.json",
            "enable_local": True,
            "enable_drive": True,
        }
    )

    result = controller.create_local_backup(manual=True, now=datetime(2026, 3, 2, 10, 0, 0))
    assert str(captured.get("local_file", "")).endswith(".db.enc")
    assert captured.get("head", b"").startswith(b"SQLite format 3") is False
    assert os.path.exists(result["backup_file"]) is True
    assert result["backup_file"].endswith(".db")
    assert os.path.exists(captured["local_file"]) is False
    assert not any(name.endswith(".db.enc") for name in os.listdir(backup_dir))

    rows = controller.list_backup_logs(limit=1)
    assert len(rows) == 1
    assert ".db.enc" in str(rows[0].get("backup_file") or "")


def test_rotate_cloud_backup_key_keeps_previous_key(tmp_path, monkeypatch):
    db = tmp_path / "backup_cloud_key_rotate.db"
    controller = _new_backup_controller(db)

    secret_map = {}
    monkeypatch.setattr(app_controller_module.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(app_controller_module.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))
    monkeypatch.setattr(app_controller_module.secret_store, "delete_secret", lambda k: secret_map.pop(k, None))
    monkeypatch.setattr(app_controller_module.secret_store, "backend_label", lambda: "TestSecretStore")

    old_key = Fernet.generate_key().decode("utf-8")
    secret_map[AppController.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT] = old_key

    status = controller.rotate_cloud_backup_encryption_key()
    assert status["current_set"] is True
    assert status["previous_set"] is True

    new_key = secret_map.get(AppController.BACKUP_CLOUD_ENCRYPTION_KEY_CURRENT, "")
    prev_key = secret_map.get(AppController.BACKUP_CLOUD_ENCRYPTION_KEY_PREVIOUS, "")

    assert bool(new_key) is True
    assert new_key != old_key
    assert prev_key == old_key


def test_restore_database_from_encrypted_backup(tmp_path, monkeypatch):
    db = tmp_path / "restore_target.db"
    controller = _new_backup_controller(db)

    secret_map = {}
    monkeypatch.setattr(app_controller_module.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(app_controller_module.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))
    monkeypatch.setattr(app_controller_module.secret_store, "delete_secret", lambda k: secret_map.pop(k, None))
    monkeypatch.setattr(app_controller_module.secret_store, "backend_label", lambda: "TestSecretStore")

    key = controller._get_or_create_cloud_backup_encryption_key()

    src_db = tmp_path / "restore_source.db"
    sconn = sqlite3.connect(src_db)
    sconn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT)")
    sconn.execute(
        """
        CREATE TABLE backup_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            trigger_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            backup_file TEXT, file_size_bytes INTEGER, error_message TEXT
        )
        """
    )
    sconn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))", ("restore/probe", "ok"))
    sconn.commit()
    sconn.close()

    enc_file = tmp_path / "restore_source.db.enc"
    with open(src_db, "rb") as f:
        plain = f.read()
    token = Fernet(key).encrypt(plain)
    with open(enc_file, "wb") as f:
        f.write(token)

    controller.restore_database_from_encrypted_backup(str(enc_file))
    assert controller.get_setting("restore/probe", "") == "ok"
    rows = controller.list_backup_logs(limit=5)
    assert any(
        str(r.get("trigger_mode") or "") == "RESTORE"
        and str(r.get("status") or "") == "SUCCESS"
        and str(r.get("backup_file") or "") == str(enc_file)
        for r in rows
    )


def test_restore_keeps_existing_manual_backup_logs(tmp_path, monkeypatch):
    db = tmp_path / "restore_keep_manual.db"
    controller = _new_backup_controller(db)

    secret_map = {}
    monkeypatch.setattr(app_controller_module.secret_store, "get_secret", lambda k: secret_map.get(k, ""))
    monkeypatch.setattr(app_controller_module.secret_store, "set_secret", lambda k, v: secret_map.__setitem__(k, v))
    monkeypatch.setattr(app_controller_module.secret_store, "delete_secret", lambda k: secret_map.pop(k, None))
    monkeypatch.setattr(app_controller_module.secret_store, "backend_label", lambda: "TestSecretStore")

    # 先在目前 DB 放一筆較新的 MANUAL 記錄（這筆不在還原來源裡）
    cur = controller.conn.cursor()
    cur.execute(
        """
        INSERT INTO backup_logs (created_at, trigger_mode, status, backup_file, file_size_bytes, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("2026-03-20 10:00:00", "MANUAL", "SUCCESS", "LOCAL:/tmp/latest_manual.db", 12345, ""),
    )
    controller.conn.commit()

    key = controller._get_or_create_cloud_backup_encryption_key()

    # 還原來源刻意只放舊資料，模擬整庫覆蓋會把新 MANUAL 洗掉的情境
    src_db = tmp_path / "restore_old_source.db"
    sconn = sqlite3.connect(src_db)
    sconn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT)")
    sconn.execute(
        """
        CREATE TABLE backup_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            trigger_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            backup_file TEXT, file_size_bytes INTEGER, error_message TEXT
        )
        """
    )
    sconn.execute(
        """
        INSERT INTO backup_logs (created_at, trigger_mode, status, backup_file, file_size_bytes, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("2026-03-01 08:00:00", "MANUAL", "SUCCESS", "LOCAL:/tmp/old_manual.db", 2222, ""),
    )
    sconn.commit()
    sconn.close()

    enc_file = tmp_path / "restore_old_source.db.enc"
    with open(src_db, "rb") as f:
        plain = f.read()
    with open(enc_file, "wb") as f:
        f.write(Fernet(key).encrypt(plain))

    controller.restore_database_from_encrypted_backup(str(enc_file))
    rows = controller.list_backup_logs(limit=50)
    files = {str(r.get("backup_file") or "") for r in rows}
    assert "LOCAL:/tmp/latest_manual.db" in files
    assert "LOCAL:/tmp/old_manual.db" in files
    assert any(
        str(r.get("trigger_mode") or "") == "RESTORE" and str(r.get("status") or "") == "SUCCESS"
        for r in rows
    )
