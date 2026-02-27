from unittest.mock import MagicMock

from app.dialogs.backup_settings_dialog import BackupHelpDialog, BackupSettingsDialog, GoogleSettingsDialog, ScheduleSettingsDialog


class DummyController:
    def get_backup_settings(self):
        return {
            "enabled": False,
            "frequency": "daily",
            "time": "23:00",
            "weekday": 1,
            "monthday": 1,
            "keep_latest": 20,
            "local_dir": "",
            "drive_folder_id": "",
            "oauth_client_secret_path": "",
            "oauth_token_path": "",
            "enable_local": True,
            "enable_drive": False,
            "use_cli_scheduler": False,
            "last_scheduled_run_at": "",
        }

    def get_scheduler_feature_settings(self):
        return {"mail_enabled": True, "backup_enabled": True}

    def save_backup_settings(self, _settings):
        return None

    def list_backup_logs(self, limit=200):
        return []

    def authorize_google_drive_oauth(self, _client, _token):
        return {"email": "test@example.com", "token_path": "/tmp/token.json"}

    def create_local_backup(self, manual=True):
        return {"backup_file": "x.db", "file_size_bytes": 1}

    def mark_backup_run(self):
        return None


def test_backup_settings_dialog_has_help_button(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    assert dialog.btn_help_doc.text() == "說明文件"


def test_backup_settings_dialog_open_help_document(qtbot, monkeypatch):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)

    html = dialog._build_help_document_html()
    assert "2. 建議設定流程（先後順序）" in html
    called = {"ok": False, "title": "", "size": (0, 0)}

    def _fake_exec(self):
        called["ok"] = True
        called["title"] = self.windowTitle()
        called["size"] = (self.width(), self.height())
        return 0

    monkeypatch.setattr(BackupHelpDialog, "exec_", _fake_exec)
    dialog._open_help_document()

    assert called["ok"] is True
    assert called["title"] == "備份說明文件"
    assert called["size"][0] >= 720


def test_backup_settings_dialog_manual_backup_finished_marks_run(qtbot, monkeypatch):
    controller = DummyController()
    controller.create_local_backup = MagicMock(return_value={"backup_file": "x.db", "file_size_bytes": 1})
    controller.mark_backup_run = MagicMock()
    controller.save_backup_settings = MagicMock()

    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.information", lambda *a, **k: None)
    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.warning", lambda *a, **k: None)

    dialog = BackupSettingsDialog(controller)
    qtbot.addWidget(dialog)
    dialog._on_manual_backup_finished({"backup_file": "x.db", "file_size_bytes": 1})

    controller.mark_backup_run.assert_called_once()


def test_backup_settings_dialog_manual_backup_running_state_toggles(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)

    # 未來背景備份會用這個 helper 控制 UI 狀態
    dialog._set_manual_backup_running(True)
    assert dialog.btn_backup_now.isEnabled() is False
    assert dialog.btn_backup_now.text() == "備份中..."
    assert dialog.btn_save.isEnabled() is False
    assert dialog.btn_refresh.isEnabled() is False

    dialog._set_manual_backup_running(False)
    assert dialog.btn_backup_now.isEnabled() is True
    assert dialog.btn_backup_now.text() == "立即備份"


def test_backup_settings_dialog_format_bytes_human():
    assert BackupSettingsDialog._format_bytes_human(0) == "0 B"
    assert BackupSettingsDialog._format_bytes_human(512) == "512 B"
    assert BackupSettingsDialog._format_bytes_human(1024) == "1.0 KB"
    assert BackupSettingsDialog._format_bytes_human(1536) == "1.5 KB"
    assert BackupSettingsDialog._format_bytes_human(1024 * 1024) == "1.0 MB"
    assert BackupSettingsDialog._format_bytes_human(1024 * 1024 * 1024) == "1.0 GB"


def test_schedule_settings_dialog_hidden_cli_always_returns_false(qtbot):
    dialog = ScheduleSettingsDialog(
        enabled=True,
        frequency="daily",
        time_text="20:45",
        weekday=1,
        monthday=1,
        use_cli_scheduler=True,  # 模擬舊設定殘留
    )
    qtbot.addWidget(dialog)

    values = dialog.get_values()
    assert values["use_cli_scheduler"] is False
    assert dialog.chk_use_cli_scheduler.isHidden() is True


def test_backup_settings_dialog_runtime_scheduler_status_text():
    text = BackupSettingsDialog._build_runtime_scheduler_status_text(
        service_running=True,
        backup_job_enabled=True,
        schedule_enabled=True,
        last_run_at_text="2026-02-23 07:06:25",
    )
    assert "排程服務：運行中" in text
    assert "備份排程：已啟用" in text
    assert "排程設定：已啟用" in text
    assert "上次排程執行：2026-02-23 07:06:25" in text


def test_backup_settings_dialog_google_summary_token_from_secret_store(qtbot, monkeypatch):
    monkeypatch.setattr(
        "app.dialogs.backup_settings_dialog.secret_store.has_secret",
        lambda _k: True,
    )
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    text = dialog.lbl_google_summary.text()
    assert "憑證：未設定" in text
    assert "Token：已設定（安全儲存）" in text
    assert "資料夾：未設定" in text


def test_google_settings_dialog_authorize_button_state_restored(qtbot, monkeypatch):
    ctrl = DummyController()
    dialog = GoogleSettingsDialog(
        controller=ctrl,
        drive_folder_id="",
        oauth_client_secret_path="/tmp/credentials.json",
        oauth_token_path="",
    )
    qtbot.addWidget(dialog)

    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.information", lambda *a, **k: None)
    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.warning", lambda *a, **k: None)

    dialog.btn_google_auth.setText("Google 授權（首次）")
    dialog._authorize_google()

    assert dialog.btn_google_auth.isEnabled() is True
    assert dialog.btn_google_auth.text() == "Google 授權（首次）"
