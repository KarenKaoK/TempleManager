from unittest.mock import MagicMock
from pathlib import Path
from PyQt5.QtCore import Qt

from app.dialogs.backup_settings_dialog import BackupHelpDialog, BackupSettingsDialog, GoogleSettingsDialog, ScheduleSettingsDialog


class DummyController:
    def __init__(self):
        self._cfg_path = str(Path("app/scheduler/scheduler_config.yaml").resolve())

    def get_backup_settings(self):
        return {
            "keep_latest": 20,
            "local_dir": "",
            "drive_folder_id": "",
            "drive_credentials_path": "",
            "enable_local": True,
            "enable_drive": False,
        }

    def get_scheduler_feature_settings(self):
        return {"mail_enabled": True, "backup_enabled": True}

    def get_scheduler_config_path(self):
        return self._cfg_path

    def save_scheduler_config_path(self, path, *, request_reload=True):
        self._cfg_path = path

    def save_backup_settings(self, _settings):
        return None

    def list_backup_logs(self, limit=200):
        return [{"created_at": "2026-04-01 17:10:00", "job_id": "daily_backup", "status": "SUCCESS", "detail": "file=/tmp/x.db.enc"}]

    def authorize_google_drive_oauth(self, _client):
        return {"email": "test@example.com"}

    def create_local_backup(self, manual=True):
        return {"backup_file": "x.db", "file_size_bytes": 1}

    def mark_backup_run(self):
        return None

    def _request_worker_reload(self):
        return None


def test_backup_settings_dialog_has_help_button(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    assert dialog.btn_help_doc.text() == "說明文件"
    assert "由外部常駐 worker 執行" in dialog.lbl_runtime_summary.text()
    assert dialog.edt_config_path.isReadOnly() is True
    assert hasattr(dialog, "_left_form_labels") is True


def test_backup_settings_dialog_uses_padding_based_styles(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    css = dialog.styleSheet()
    assert "QLineEdit, QSpinBox" in css
    assert "padding: 8px 10px;" in css
    assert "QCheckBox" in css
    assert "QPushButton" in css


def test_backup_settings_dialog_support_labels_use_rich_text(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    assert dialog.lbl_runtime_summary.textFormat() == Qt.RichText
    assert dialog.lbl_cli_help.textFormat() == Qt.RichText
    assert dialog.lbl_google_summary.textFormat() == Qt.RichText
    assert "line-height:1.5" in dialog.lbl_cli_help.text()


def test_backup_settings_dialog_buttons_share_rows(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)

    assert dialog.edt_config_path.parentWidget() is dialog.btn_select_config.parentWidget()
    assert dialog.lbl_google_summary.parentWidget() is dialog.btn_google_settings.parentWidget()
    assert dialog.btn_google_settings.parentWidget() is dialog.btn_rotate_cloud_key.parentWidget()

    action_parent = dialog.btn_save.parentWidget()
    assert dialog.btn_backup_now.parentWidget() is action_parent
    assert dialog.btn_reload_schedule.parentWidget() is action_parent
    assert dialog.btn_toggle_backup_schedule.parentWidget() is action_parent
    assert dialog.btn_restore_encrypted.parentWidget() is action_parent
    assert dialog.btn_decrypt_help.parentWidget() is action_parent
    assert dialog.btn_help_doc.parentWidget() is action_parent
    assert dialog.btn_close.parentWidget() is action_parent
    assert dialog.btn_select_config.objectName() == "compactButton"
    assert dialog.btn_google_settings.objectName() == "compactButton"


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


def test_backup_settings_dialog_log_section_hidden(qtbot):
    dialog = BackupSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    assert dialog.lbl_logs_title.isHidden() is True
    assert dialog.table_logs.isHidden() is True
    assert dialog.table_logs.rowCount() == 0


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
        drive_credentials_path="/tmp/credentials.json",
    )
    qtbot.addWidget(dialog)

    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.information", lambda *a, **k: None)
    monkeypatch.setattr("app.dialogs.backup_settings_dialog.QMessageBox.warning", lambda *a, **k: None)

    dialog.btn_google_auth.setText("Google 授權（首次）")
    dialog._authorize_google()

    assert dialog.btn_google_auth.isEnabled() is True
    assert dialog.btn_google_auth.text() == "Google 授權（首次）"
