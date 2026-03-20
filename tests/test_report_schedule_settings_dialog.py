from app.dialogs.report_schedule_settings_dialog import ReportScheduleSettingsDialog


class DummyController:
    def __init__(self):
        self._flags = {"mail_enabled": True, "backup_enabled": True}
        self._cfg_path = "app/scheduler/scheduler_config.yaml"
        self._mail_username = "test@gmail.com"
        self._mail_pwd_set = True

    def get_scheduler_feature_settings(self):
        return dict(self._flags)

    def save_scheduler_feature_settings(self, settings):
        self._flags = {
            "mail_enabled": bool(settings.get("mail_enabled", True)),
            "backup_enabled": bool(settings.get("backup_enabled", True)),
        }

    def get_scheduler_config_path(self):
        return self._cfg_path

    def save_scheduler_config_path(self, path):
        self._cfg_path = path

    def get_scheduler_mail_settings(self):
        return {
            "smtp_username": self._mail_username,
            "smtp_password_set": self._mail_pwd_set,
            "secret_backend": "Windows Credential Manager",
            "secret_error": "",
        }

    def save_scheduler_mail_settings(self, smtp_username, smtp_password=""):
        self._mail_username = smtp_username
        if smtp_password:
            self._mail_pwd_set = True


def test_report_schedule_settings_dialog_has_readonly_config_path(qtbot):
    dialog = ReportScheduleSettingsDialog(DummyController())
    qtbot.addWidget(dialog)
    assert dialog.edt_config_path.isReadOnly() is True
    assert dialog.edt_config_path.text() != ""
    assert dialog.btn_select_config.text() == "選擇檔案"
    assert dialog.edt_smtp_username.text() == "test@gmail.com"
    assert dialog.btn_save_mail_secret.text() == "儲存郵件帳密"
    assert dialog.lbl_scheduler_status.text() == "由外部常駐 worker 執行"
    assert hasattr(dialog, "btn_reload") is False
    assert dialog.btn_worker_help.text() == "外部常駐 worker 設定說明"


def test_report_schedule_settings_dialog_worker_help_mentions_windows_and_macos():
    html = ReportScheduleSettingsDialog._external_worker_help_html()
    assert "工作排程器" in html
    assert "LaunchAgents" in html
    assert "app.scheduler.worker" in html
    assert "temple_venv" in html
