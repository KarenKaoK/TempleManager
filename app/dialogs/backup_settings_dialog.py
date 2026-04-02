from html import escape
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, QTimer
import os
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QHeaderView,
)

from app.controller.app_controller import AppController
from app.utils import secret_store


class BackupHelpDialog(QDialog):
    def __init__(self, title: str, html: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(980, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        content = QTextBrowser(self)
        content.setOpenExternalLinks(False)
        content.setReadOnly(True)
        content.setHtml(html)
        content.setStyleSheet(
            "QTextBrowser {"
            "  background: #ffffff;"
            "  border: 1px solid #D1D5DB;"
            "  padding: 10px;"
            "}"
        )
        root.addWidget(content, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


class ScheduleSettingsDialog(QDialog):
    def __init__(
        self,
        enabled: bool,
        frequency: str,
        time_text: str,
        weekday: int,
        monthday: int,
        use_cli_scheduler: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("排程設定")
        self.resize(640, 420)
        self.setMinimumSize(560, 360)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setFormAlignment(Qt.AlignTop)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        self.chk_enabled = QCheckBox("啟用自動備份")
        form.addRow("自動備份", self.chk_enabled)

        self.cmb_frequency = QComboBox()
        self.cmb_frequency.addItem("每日", "daily")
        self.cmb_frequency.addItem("每週", "weekly")
        self.cmb_frequency.addItem("每月", "monthly")
        form.addRow("頻率", self.cmb_frequency)

        self.edt_time = QLineEdit()
        self.edt_time.setPlaceholderText("HH:MM，例如 23:00")
        form.addRow("時間", self.edt_time)

        self.cmb_weekday = QComboBox()
        self.cmb_weekday.addItem("週一", 1)
        self.cmb_weekday.addItem("週二", 2)
        self.cmb_weekday.addItem("週三", 3)
        self.cmb_weekday.addItem("週四", 4)
        self.cmb_weekday.addItem("週五", 5)
        self.cmb_weekday.addItem("週六", 6)
        self.cmb_weekday.addItem("週日", 7)
        form.addRow("每週星期", self.cmb_weekday)

        self.spin_monthday = QSpinBox()
        self.spin_monthday.setRange(1, 31)
        form.addRow("每月日期", self.spin_monthday)
        # 相容模式保留：UI 先隱藏 CLI/OS 排程選項，但仍保留設定值讀寫
        self.chk_use_cli_scheduler = QCheckBox("改用 CLI/作業系統排程（登出或未開啟程式也能備份）")
        self.chk_use_cli_scheduler.hide()
        self.chk_use_cli_scheduler.setVisible(False)
        # 不加入 form row，避免在 UI 顯示

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._set_combo_data(self.cmb_frequency, frequency or "daily")
        self.chk_enabled.setChecked(bool(enabled))
        self.edt_time.setText(time_text or "23:00")
        self._set_combo_data(self.cmb_weekday, int(weekday or 1))
        self.spin_monthday.setValue(int(monthday or 1))
        self.chk_use_cli_scheduler.setChecked(bool(use_cli_scheduler))

        self.cmb_frequency.currentIndexChanged.connect(self._sync_frequency_ui)
        self._sync_frequency_ui()

    def _set_combo_data(self, combo: QComboBox, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _sync_frequency_ui(self):
        freq = self.cmb_frequency.currentData()
        self.cmb_weekday.setEnabled(freq == "weekly")
        self.spin_monthday.setEnabled(freq == "monthly")

    def get_values(self) -> dict:
        return {
            "enabled": self.chk_enabled.isChecked(),
            "frequency": self.cmb_frequency.currentData(),
            "time": (self.edt_time.text() or "").strip(),
            "weekday": int(self.cmb_weekday.currentData()),
            "monthday": int(self.spin_monthday.value()),
            # UI 已隱藏 CLI 模式，避免舊設定值殘留造成桌面版自動備份被停用
            "use_cli_scheduler": False,
        }


class GoogleSettingsDialog(QDialog):
    def __init__(
        self,
        controller,
        drive_folder_id: str,
        drive_credentials_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Google 設定")
        self.resize(760, 360)
        self.setMinimumSize(640, 320)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setFormAlignment(Qt.AlignTop)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.edt_drive_folder = QLineEdit()
        self.edt_drive_folder.setPlaceholderText("Google Drive folder id")
        self.edt_drive_folder.setText(drive_folder_id or "")
        form.addRow("Drive 資料夾 ID", self.edt_drive_folder)

        self.edt_oauth_client_secret = QLineEdit()
        self.edt_oauth_client_secret.setPlaceholderText("OAuth client credentials.json 路徑")
        self.edt_oauth_client_secret.setText(drive_credentials_path or "")
        self.btn_pick_oauth_client = QPushButton("選擇檔案")
        self.btn_pick_oauth_client.clicked.connect(self._pick_oauth_client_file)
        form.addRow("OAuth 憑證 JSON", self._line_with_button(self.edt_oauth_client_secret, self.btn_pick_oauth_client))

        self.btn_google_auth = QPushButton("Google 授權（首次）")
        self.btn_google_auth.clicked.connect(self._authorize_google)
        form.addRow("Google 連線", self.btn_google_auth)

        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _line_with_button(self, line: QLineEdit, button: QPushButton) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line, 1)
        row.addWidget(button)
        return wrap

    def _pick_oauth_client_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 OAuth credentials.json",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.edt_oauth_client_secret.setText(path)

    def _authorize_google(self):
        old_text = self.btn_google_auth.text()
        try:
            client_path = (self.edt_oauth_client_secret.text() or "").strip()
            if not client_path:
                QMessageBox.warning(self, "設定錯誤", "請先設定 OAuth 憑證 JSON")
                return
            self.btn_google_auth.setEnabled(False)
            self.btn_google_auth.setText("授權中...")
            QApplication.processEvents()
            result = self.controller.authorize_google_drive_oauth(client_path)
            email = result.get("email", "")
            tip = f"Google 授權成功\n帳號：{email}" if email else "Google 授權成功"
            QMessageBox.information(self, "成功", tip)
        except Exception as e:
            QMessageBox.warning(self, "授權失敗", str(e))
        finally:
            self.btn_google_auth.setEnabled(True)
            self.btn_google_auth.setText(old_text)

    def get_values(self) -> dict:
        return {
            "drive_folder_id": (self.edt_drive_folder.text() or "").strip(),
            "drive_credentials_path": (self.edt_oauth_client_secret.text() or "").strip(),
        }


class BackupWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, controller, manual: bool):
        super().__init__()
        self.controller = controller
        self.manual = bool(manual)

    def run(self):
        worker_controller = None
        result = None
        error_text = None
        try:
            # 背景 thread 不可共用主執行緒的 sqlite connection，需建立獨立 controller
            db_path = getattr(self.controller, "db_path", None)
            worker_controller = AppController(db_path=db_path) if db_path else AppController()
            result = worker_controller.create_local_backup(manual=self.manual)
        except Exception as e:
            error_text = str(e)
        finally:
            # 先釋放 worker thread 內的 sqlite connection，避免主執行緒 callback 卡在 DB lock
            try:
                conn = getattr(worker_controller, "conn", None)
                if conn is not None:
                    conn.close()
            except Exception:
                pass

        if error_text is not None:
            self.failed.emit(error_text)
            return
        self.finished.emit(result or {})


class BackupSettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._google_drive_folder_id = ""
        self._google_oauth_client_secret_path = ""
        self._saved_config_path = ""
        self._backup_job_enabled = True
        self._scheduler_service_running = False
        self._backup_thread = None
        self._backup_worker = None
        self._backup_running = False
        self.setWindowTitle("資料備份")
        self._resize_like_main_window(parent)
        self._build_ui()
        self._load_settings()
        self._log_reload_pending = False
        self._backup_notice_reset_timer = None
        self._apply_dialog_styles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        form_box = QWidget()
        form = QGridLayout(form_box)
        self._form = form
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(14)
        form.setColumnStretch(1, 1)

        config_label = QLabel("設定檔路徑")
        self.edt_config_path = QLineEdit("")
        self.edt_config_path.setReadOnly(True)
        self.edt_config_path.setPlaceholderText("scheduler_config.yaml 路徑")
        self.btn_select_config = QPushButton("選擇檔案")
        self.btn_select_config.setObjectName("compactButton")
        self.btn_select_config.clicked.connect(self._select_config_file)
        config_wrap = QWidget()
        config_layout = QHBoxLayout(config_wrap)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(10)
        config_layout.addWidget(self.edt_config_path, 1)
        config_layout.addWidget(self.btn_select_config, 0)
        self.btn_select_config.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_select_config.setMinimumWidth(160)
        self.btn_select_config.setMaximumWidth(220)
        self._config_wrap = config_wrap
        form.addWidget(config_label, 0, 0, Qt.AlignRight | Qt.AlignTop)
        form.addWidget(config_wrap, 0, 1)

        keep_label = QLabel("保留最新備份數")
        self.spin_keep = QSpinBox()
        self.spin_keep.setRange(1, 500)
        form.addWidget(keep_label, 1, 0, Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(self.spin_keep, 1, 1)

        local_dir_label = QLabel("本機備份路徑")
        self.edt_local_dir = QLineEdit()
        self.edt_local_dir.setPlaceholderText("可留空，使用預設 app/database/backups")
        form.addWidget(local_dir_label, 2, 0, Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(self.edt_local_dir, 2, 1)

        target_label = QLabel("備份目的地")
        self.chk_enable_local = QCheckBox("本機備份")
        self.chk_enable_local.setChecked(True)
        self.chk_enable_drive = QCheckBox("Google Drive（OAuth）")
        target_row = QHBoxLayout()
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.setSpacing(18)
        target_row.addWidget(self.chk_enable_local)
        target_row.addWidget(self.chk_enable_drive)
        target_row.addStretch()
        target_wrap = QWidget()
        target_wrap.setLayout(target_row)
        target_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._target_wrap = target_wrap
        form.addWidget(target_label, 3, 0, Qt.AlignRight | Qt.AlignTop)
        form.addWidget(target_wrap, 3, 1)

        google_label = QLabel("Google Drive 設定")
        self.lbl_google_summary = QLabel("")
        self.lbl_google_summary.setWordWrap(True)
        self.btn_google_settings = QPushButton("Google 設定")
        self.btn_google_settings.setObjectName("compactButton")
        self.btn_rotate_cloud_key = QPushButton("更新雲端加密金鑰")
        self.btn_rotate_cloud_key.setObjectName("compactButton")
        self.btn_google_settings.clicked.connect(self._open_google_settings_dialog)
        self.btn_rotate_cloud_key.clicked.connect(self._rotate_cloud_backup_key)
        google_wrap = QWidget()
        google_layout = QHBoxLayout(google_wrap)
        google_layout.setContentsMargins(0, 0, 0, 0)
        google_layout.setSpacing(10)
        google_layout.addWidget(self.lbl_google_summary, 1)
        google_layout.addWidget(self.btn_google_settings, 0)
        google_layout.addWidget(self.btn_rotate_cloud_key, 0)
        self.btn_google_settings.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_rotate_cloud_key.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_google_settings.setMinimumWidth(150)
        self.btn_google_settings.setMaximumWidth(220)
        self.btn_rotate_cloud_key.setMinimumWidth(190)
        self.btn_rotate_cloud_key.setMaximumWidth(260)
        self._google_wrap = google_wrap
        google_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addWidget(google_label, 4, 0, Qt.AlignRight | Qt.AlignTop)
        form.addWidget(google_wrap, 4, 1)

        self._left_form_labels = [
            config_label,
            keep_label,
            local_dir_label,
            target_label,
            google_label,
        ]
        for lbl in self._left_form_labels:
            lbl.setProperty("ui_role", "form_label")

        root.addWidget(form_box)
        root.addSpacing(8)

        self.lbl_runtime_summary = QLabel("")
        self.lbl_runtime_summary.setWordWrap(True)
        self.lbl_runtime_summary.setProperty("ui_role", "support_label")
        root.addWidget(self.lbl_runtime_summary)

        help_text = (
            "備份排程規則由外部常駐 worker 依 scheduler_config.yaml 執行。\n"
            "此頁只負責設定備份目的地、手動立即備份與通知 worker reload。"
        )
        self.lbl_cli_help = QLabel(help_text)
        self.lbl_cli_help.setWordWrap(True)
        self.lbl_cli_help.setProperty("ui_role", "support_label")
        self._set_support_label_text(self.lbl_cli_help, help_text)
        root.addWidget(self.lbl_cli_help)

        self.lbl_google_summary.setProperty("ui_role", "support_label")
        self._set_support_label_text(self.lbl_runtime_summary, "")

        action_tertiary_wrap = QWidget()
        action_tertiary = QHBoxLayout(action_tertiary_wrap)
        action_tertiary.setContentsMargins(0, 0, 0, 0)
        action_tertiary.setSpacing(10)
        self.btn_toggle_backup_schedule = QPushButton("停用自動備份")
        self.btn_reload_schedule = QPushButton("重新載入排程")
        self.btn_save = QPushButton("儲存設定")
        self.btn_backup_now = QPushButton("立即備份")
        self.btn_restore_encrypted = QPushButton("從加密備份還原")
        self.btn_decrypt_help = QPushButton("解密備份說明")
        self.btn_help_doc = QPushButton("說明文件")
        self.btn_close = QPushButton("關閉")
        self.btn_toggle_backup_schedule.clicked.connect(self._toggle_backup_schedule)
        self.btn_reload_schedule.clicked.connect(self._reload_schedule)
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_backup_now.clicked.connect(self._run_manual_backup)
        self.btn_restore_encrypted.clicked.connect(self._restore_from_encrypted_backup)
        self.btn_decrypt_help.clicked.connect(self._open_decrypt_help_document)
        self.btn_help_doc.clicked.connect(self._open_help_document)
        self.btn_close.clicked.connect(self.accept)
        action_tertiary.addWidget(self.btn_save)
        action_tertiary.addWidget(self.btn_backup_now)
        action_tertiary.addWidget(self.btn_reload_schedule)
        action_tertiary.addWidget(self.btn_toggle_backup_schedule)
        action_tertiary.addWidget(self.btn_restore_encrypted)
        action_tertiary.addWidget(self.btn_decrypt_help)
        action_tertiary.addWidget(self.btn_help_doc)
        action_tertiary.addStretch()
        action_tertiary.addWidget(self.btn_close)
        self._action_bar = action_tertiary_wrap
        root.addWidget(action_tertiary_wrap)

        self.lbl_backup_notice = QLabel("")
        self.lbl_backup_notice.setWordWrap(True)
        self.lbl_backup_notice.setProperty("ui_role", "support_label")
        self._set_support_label_text(self.lbl_backup_notice, "")
        root.addWidget(self.lbl_backup_notice)

        self.lbl_logs_title = QLabel("備份紀錄")
        self.lbl_logs_title.hide()
        self.table_logs = QTableWidget(0, 4)
        self.table_logs.hide()

        self._apply_form_field_width_policy()

    def _apply_form_field_width_policy(self):
        """
        避免 QComboBox/QSpinBox 在 FormLayout 中被壓成窄欄。
        """
        expand_widgets = [
            self.spin_keep,
            self.btn_google_settings,
        ]
        for w in expand_widgets:
            sp = w.sizePolicy()
            sp.setHorizontalPolicy(QSizePolicy.Expanding)
            w.setSizePolicy(sp)

        self.spin_keep.setMinimumWidth(170)
        self.edt_config_path.setMinimumWidth(520)

    def _apply_dialog_styles(self):
        self.setStyleSheet("""
            QLineEdit, QSpinBox {
                padding: 8px 10px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
            }
            QCheckBox {
                spacing: 8px;
                padding: 6px 0;
            }
            QPushButton {
                padding: 8px 14px;
            }
            QPushButton#compactButton {
                padding: 6px 12px;
            }
            QLabel[ui_role="form_label"] {
                padding: 6px 0;
            }
            QLabel[ui_role="support_label"] {
                color: #6B7280;
            }
        """)

    def _set_support_label_text(self, label: QLabel, text: str):
        html = escape(text or "").replace("\n", "<br>")
        label.setTextFormat(Qt.RichText)
        label.setText(f"<div style='line-height:1.5; color:#6B7280;'>{html}</div>")

    def _resize_like_main_window(self, parent):
        """
        跟主視窗尺寸策略一致：以主視窗為基準，但限制最大寬度，
        避免在較小螢幕上過寬。
        """
        default_w, default_h = 1000, 700
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry() if screen else None

        try:
            parent_w = int(parent.width()) if parent is not None else default_w
            parent_h = int(parent.height()) if parent is not None else default_h
            max_w = screen_rect.width() - 40 if screen_rect else 1400
            max_h = screen_rect.height() - 40 if screen_rect else 980

            # 直接對齊主視窗尺寸（仍受螢幕可用範圍限制）
            w = int(parent_w)
            h = int(parent_h)
            w = max(920, min(max_w, w))
            h = max(680, min(max_h, h))
            self.resize(w, h)
        except Exception:
            self.resize(default_w, default_h)

        self.setMinimumSize(920, 680)
        if screen_rect:
            self.setMaximumSize(screen_rect.width(), screen_rect.height())

    def _line_with_button(self, line: QLineEdit, button: QPushButton) -> QWidget:
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(line, 1)
        row.addWidget(button)
        return wrap

    def _load_settings(self):
        s = self.controller.get_backup_settings()
        feature_getter = getattr(self.controller, "get_scheduler_feature_settings", None)
        if callable(feature_getter):
            try:
                self._backup_job_enabled = bool((feature_getter() or {}).get("backup_enabled", True))
            except Exception:
                self._backup_job_enabled = True
        else:
            self._backup_job_enabled = True
        self.spin_keep.setValue(int(s.get("keep_latest", 20)))
        self.edt_local_dir.setText(str(s.get("local_dir", "")))
        self.chk_enable_local.setChecked(bool(s.get("enable_local", True)))
        self.chk_enable_drive.setChecked(bool(s.get("enable_drive", False)))
        self._google_oauth_client_secret_path = str(s.get("drive_credentials_path", ""))
        self._google_drive_folder_id = str(s.get("drive_folder_id", ""))
        cfg_getter = getattr(self.controller, "get_scheduler_config_path", None)
        if callable(cfg_getter):
            try:
                self._saved_config_path = str(cfg_getter() or "")
            except Exception:
                self._saved_config_path = ""
        self.edt_config_path.setText(self._saved_config_path)
        self._update_google_summary()
        self._refresh_scheduler_status()

    def _set_combo_data(self, combo: QComboBox, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _refresh_scheduler_status(self):
        enabled_text = "已啟用" if self._backup_job_enabled else "未啟用"
        self.btn_toggle_backup_schedule.setText("停用自動備份" if self._backup_job_enabled else "啟用自動備份")
        self.edt_config_path.setToolTip(self.edt_config_path.text() or "")
        self._set_support_label_text(
            self.lbl_runtime_summary, f"由外部常駐 worker 執行｜自動備份：{enabled_text}"
        )

    def _select_config_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 scheduler_config.yaml",
            self.edt_config_path.text() or "",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        self.edt_config_path.setText(os.path.abspath(path))

    def _toggle_backup_schedule(self):
        saver = getattr(self.controller, "save_scheduler_feature_settings", None)
        if not callable(saver):
            QMessageBox.warning(self, "操作失敗", "目前控制器不支援自動備份排程設定。")
            return
        try:
            saver({"mail_enabled": True, "backup_enabled": not self._backup_job_enabled})
        except Exception as e:
            QMessageBox.warning(self, "操作失敗", str(e))
            return
        self._backup_job_enabled = not self._backup_job_enabled
        self._refresh_scheduler_status()

    def _reload_schedule(self):
        requester = getattr(self.controller, "_request_worker_reload", None)
        if not callable(requester):
            QMessageBox.warning(self, "操作失敗", "目前控制器不支援重新載入排程。")
            return
        try:
            requester()
        except Exception as e:
            QMessageBox.warning(self, "操作失敗", str(e))
            return
        QMessageBox.information(self, "完成", "已通知背景 worker 重新載入排程設定。")

    def _update_google_summary(self):
        cred_text = "已設定" if (self._google_oauth_client_secret_path or "").strip() else "未設定"
        token_secret_set = False
        try:
            token_secret_set = bool(secret_store.has_secret(AppController.BACKUP_DRIVE_OAUTH_TOKEN_SECRET_KEY))
        except Exception:
            token_secret_set = False
        token_text = "已設定（安全儲存）" if token_secret_set else "未設定"
        key_text = "未設定"
        getter = getattr(self.controller, "get_cloud_backup_encryption_status", None)
        if callable(getter):
            try:
                ks = getter() or {}
                if bool(ks.get("current_set")):
                    key_text = "已設定"
                    if bool(ks.get("previous_set")):
                        key_text = "已設定（含上一版）"
            except Exception:
                key_text = "未設定"
        folder_text = self._google_drive_folder_id if (self._google_drive_folder_id or "").strip() else "未設定"
        self._set_support_label_text(
            self.lbl_google_summary,
            f"憑證：{cred_text}\n"
            f"Token：{token_text}\n"
            f"雲端加密金鑰：{key_text}\n"
            f"資料夾：{folder_text}",
        )

    def _open_google_settings_dialog(self):
        self._update_google_summary()
        dialog = GoogleSettingsDialog(
            controller=self.controller,
            drive_folder_id=self._google_drive_folder_id,
            drive_credentials_path=self._google_oauth_client_secret_path,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.get_values()
        self._google_drive_folder_id = values.get("drive_folder_id", "")
        self._google_oauth_client_secret_path = values.get("drive_credentials_path", "")
        self._update_google_summary()

    def _rotate_cloud_backup_key(self):
        rotator = getattr(self.controller, "rotate_cloud_backup_encryption_key", None)
        if not callable(rotator):
            QMessageBox.warning(self, "功能不可用", "目前控制器不支援雲端加密金鑰更新。")
            return
        reply = QMessageBox.question(
            self,
            "確認更新",
            "更新後新上傳的雲端備份會使用新金鑰。\n"
            "舊備份仍需舊金鑰解密（系統會保留上一版）。\n\n"
            "確定要更新雲端加密金鑰嗎？",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            rotator()
            self._update_google_summary()
            QMessageBox.information(self, "成功", "雲端加密金鑰已更新，並保留上一版相容。")
        except Exception as e:
            QMessageBox.warning(self, "更新失敗", str(e))

    def _restore_from_encrypted_backup(self):
        restorer = getattr(self.controller, "restore_database_from_encrypted_backup", None)
        if not callable(restorer):
            QMessageBox.warning(self, "功能不可用", "目前控制器不支援加密備份還原。")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇加密備份檔",
            "",
            "Encrypted Backup (*.db.enc);;All Files (*)",
        )
        if not path:
            return
        reply = QMessageBox.question(
            self,
            "確認還原",
            "此操作會以選取備份覆蓋目前資料庫。\n建議先手動再做一次立即備份。\n\n是否繼續？",
        )
        if reply != QMessageBox.Yes:
            return
        try:
            restorer(path)
            QMessageBox.information(self, "還原完成", "已完成加密備份還原。")
        except Exception as e:
            QMessageBox.warning(self, "還原失敗", str(e))

    def _build_settings_payload(self) -> dict:
        return {
            "keep_latest": int(self.spin_keep.value()),
            "local_dir": (self.edt_local_dir.text() or "").strip(),
            "enable_local": self.chk_enable_local.isChecked(),
            "enable_drive": self.chk_enable_drive.isChecked(),
            "drive_credentials_path": (self._google_oauth_client_secret_path or "").strip(),
            "drive_folder_id": (self._google_drive_folder_id or "").strip(),
        }

    def _save_settings(self, show_success: bool = True) -> bool:
        try:
            if not self.chk_enable_local.isChecked() and not self.chk_enable_drive.isChecked():
                QMessageBox.warning(self, "設定錯誤", "請至少勾選一種備份目的地")
                return False
            if self.chk_enable_drive.isChecked() and not (self._google_oauth_client_secret_path or "").strip():
                QMessageBox.warning(self, "設定錯誤", "已啟用 Google Drive，請先設定 OAuth 憑證 JSON")
                return False

            payload = self._build_settings_payload()
            cfg_path = os.path.abspath(self.edt_config_path.text() or "")
            path_saver = getattr(self.controller, "save_scheduler_config_path", None)
            reload_requester = getattr(self.controller, "_request_worker_reload", None)
            self.controller.save_backup_settings(payload)
            if callable(path_saver) and cfg_path:
                path_saver(cfg_path, request_reload=False)
            if callable(reload_requester):
                reload_requester()
            if show_success:
                QMessageBox.information(self, "成功", "備份設定已儲存")
            return True
        except Exception as e:
            QMessageBox.warning(self, "儲存失敗", str(e))
            return False

    def _run_manual_backup(self):
        try:
            if self._backup_running:
                return
            # 立即備份前先用目前 UI 狀態覆寫設定，避免吃到舊值
            if not self._save_settings(show_success=False):
                return
            self._set_manual_backup_running(True)
            # 先讓 UI repaint，避免按鈕文字/disabled 狀態延後更新造成「像卡住」
            QApplication.processEvents()
            self._backup_thread = QThread(self)
            self._backup_worker = BackupWorker(self.controller, manual=True)
            self._backup_worker.moveToThread(self._backup_thread)

            self._backup_thread.started.connect(self._backup_worker.run)
            self._backup_worker.finished.connect(self._on_manual_backup_finished)
            self._backup_worker.failed.connect(self._on_manual_backup_failed)

            self._backup_worker.finished.connect(self._backup_thread.quit)
            self._backup_worker.failed.connect(self._backup_thread.quit)
            self._backup_thread.finished.connect(self._cleanup_manual_backup_thread)

            self._backup_thread.start()
        except Exception as e:
            self._reload_logs(auto_resize=False)
            self._set_manual_backup_running(False)
            QMessageBox.warning(self, "備份失敗", str(e))

    def _on_manual_backup_finished(self, result: dict):
        # 手動備份成功後，也標記本期已完成，避免同分鐘排程再跑一次
        mark_run = getattr(self.controller, "mark_backup_run", None)
        mark_run_error = ""
        if callable(mark_run):
            try:
                mark_run()
            except Exception as e:
                mark_run_error = str(e)
        self._set_manual_backup_running(False)
        self._show_backup_notice(
            (
                f"備份完成：{result.get('backup_file','')}（{result.get('file_size_bytes',0)} bytes）"
                + (f"；更新執行時間失敗：{mark_run_error}" if mark_run_error else "")
            ),
            is_error=bool(mark_run_error),
        )
        self._schedule_log_reload()

    def _on_manual_backup_failed(self, error_text: str):
        self._schedule_log_reload()
        self._set_manual_backup_running(False)
        self._show_backup_notice(f"備份失敗：{error_text}", is_error=True)
        QMessageBox.warning(self, "備份失敗", error_text)

    def _show_backup_notice(self, text: str, is_error: bool = False):
        color = "#B91C1C" if is_error else "#065F46"
        self.lbl_backup_notice.setTextFormat(Qt.RichText)
        self.lbl_backup_notice.setText(
            f"<div style='line-height:1.5; color:{color};'>{escape(text or '')}</div>"
        )
        if self._backup_notice_reset_timer is None:
            self._backup_notice_reset_timer = QTimer(self)
            self._backup_notice_reset_timer.setSingleShot(True)
            self._backup_notice_reset_timer.timeout.connect(self._clear_backup_notice)
        self._backup_notice_reset_timer.start(8000)
        self._refresh_scheduler_status()

    def _clear_backup_notice(self):
        self._set_support_label_text(self.lbl_backup_notice, "")

    def _schedule_log_reload(self):
        if self._log_reload_pending:
            return
        self._log_reload_pending = True
        QTimer.singleShot(0, self._run_scheduled_log_reload)

    def _run_scheduled_log_reload(self):
        self._log_reload_pending = False
        self._reload_logs(auto_resize=False, limit=80)

    def _cleanup_manual_backup_thread(self):
        if self._backup_worker is not None:
            self._backup_worker.deleteLater()
        if self._backup_thread is not None:
            self._backup_thread.deleteLater()
        self._backup_worker = None
        self._backup_thread = None

    def _set_manual_backup_running(self, running: bool):
        self._backup_running = bool(running)
        self.btn_backup_now.setEnabled(not running)
        self.btn_save.setEnabled(not running)
        self.btn_decrypt_help.setEnabled(not running)
        self.btn_restore_encrypted.setEnabled(not running)
        self.btn_backup_now.setText("備份中..." if running else "立即備份")

    def _reload_logs(self, auto_resize: bool = True, limit: int = 200):
        if not hasattr(self, "table_logs") or self.table_logs is None:
            return
        if self.table_logs.isHidden():
            return
        rows = self.controller.list_backup_logs(limit=limit)
        self.table_logs.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [
                str(r.get("created_at") or ""),
                str(r.get("job_id") or ""),
                str(r.get("status") or ""),
                str(r.get("detail") or ""),
            ]
            for j, v in enumerate(vals):
                self.table_logs.setItem(i, j, QTableWidgetItem(v))
        if auto_resize:
            self.table_logs.resizeColumnsToContents()

    @staticmethod
    def _format_bytes_human(size_bytes) -> str:
        """將 bytes 轉為人類可讀格式（B / KB / MB / GB / TB）。"""
        try:
            size = float(size_bytes or 0)
        except Exception:
            size = 0.0
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024.0
            idx += 1
        if idx == 0:
            return f"{int(size)} {units[idx]}"
        return f"{size:.1f} {units[idx]}"

    def _open_help_document(self):
        html = self._build_help_document_html()
        dialog = BackupHelpDialog("備份說明文件", html, self)
        dialog.exec_()

    def _open_decrypt_help_document(self):
        html = self._build_decrypt_help_html()
        dialog = BackupHelpDialog("解密備份說明", html, self)
        dialog.exec_()

    def _build_help_document_html(self) -> str:
        return f"""
<style>
  body {{ line-height: 1.5; margin: 0; padding: 0 0 18px 0; }}
  pre {{ white-space: pre-wrap; word-break: break-all; }}
  h2, h3 {{ margin-top: 10px; margin-bottom: 6px; }}
  p {{ margin: 6px 0; }}
  ol {{ margin-top: 4px; margin-bottom: 10px; }}
</style>
<h2>資料備份說明文件</h2>
<h3>1. 備份邏輯</h3>
<ol>
  <li><b>外部常駐 worker</b>：自動備份由 worker 依 <code>scheduler_config.yaml</code> 執行，不依賴主程式是否開啟。</li>
  <li><b>立即備份</b>：按下就執行，不看排程時間，依當下勾選目的地備份（本機 / Drive / 雙寫）。</li>
  <li><b>雲端加密</b>：若啟用 Google Drive，上傳前會先轉為 <code>.db.enc</code> 再上傳；本機仍保留 <code>.db</code>。</li>
  <li><b>還原</b>：可從 <code>.db.enc</code> 還原到目前資料庫（會覆蓋現有資料）。</li>
  <li>Google Drive 採 OAuth 模式：首次需人工授權一次，後續由 token 自動續期。</li>
</ol>

<h3>2. 建議設定流程（先後順序）</h3>
<ol>
  <li>步驟 1：先完成 Google OAuth 設定取得credentials.json</li>
  <li>步驟 2：回到系統內設定 scheduler_config.yaml 路徑、JSON 路徑、資料夾 ID、目的地與保留數量</li>
  <li>步驟 3：按「Google 授權（首次）」並儲存設定</li>
  <li>步驟 4：通知 worker reload，或重新啟動 worker</li>
  <li>步驟 5：執行「立即備份」驗證一次</li>
</ol>

<h3>3. Google Drive OAuth 設定</h3>
<p><b>第一步：準備 OAuth 憑證</b></p>
<ol>
  <li>Google Cloud Console →「API 和服務」→「憑證」</li>
  <li>點擊「+ 建立憑證」→「OAuth 用戶端 ID」</li>
  <li>應用程式類型選擇「桌面應用程式 (Desktop App)」</li>
  <li>名稱可自訂（例如 <code>MyPCBackup</code>），建立後下載 JSON</li>
  <li>將下載檔案重新命名為 <code>credentials.json</code>，建議放在專案外路徑</li>
  <li>進入「OAuth 同意畫面」，確認 User Type 為「外部」</li>
  <li>在「測試使用者 (Test users)」加入你的 Gmail（未加入可能出現 403 Access Blocked）</li>
</ol>

<p><b>第二步：確認 API 已啟用</b></p>
<ol>
  <li>Google Cloud Console → API 和服務 → 啟用 API 和服務</li>
  <li>確認 Google Drive API 顯示為「已啟用」</li>
</ol>

<p><b>第三步：系統內填寫路徑與資料夾</b></p>
<ol>
  <li>填入 OAuth 憑證 JSON 路徑（credentials.json）</li>
  <li>OAuth token 由系統安全儲存管理，不需指定 token.json 路徑</li>
  <li>按「Google 授權（首次）」完成授權後，token 會存入系統安全儲存</li>
  <li>填入 Drive 資料夾 ID</li>
</ol>

<p><b>第四步：首次人工授權</b></p>
<ol>
  <li>按「Google 授權（首次）」並完成瀏覽器登入同意</li>
  <li>系統會更新安全儲存中的 token，後續可自動 refresh</li>
</ol>

<h3>4. 備份目的地與驗證</h3>
<ol>
  <li>回到系統內設定備份目的地（本機 / Google Drive，可雙寫）</li>
  <li>設定保留最新備份數</li>
  <li>按「立即備份」執行一次測試備份</li>
  <li>確認備份紀錄狀態為 <code>SUCCESS</code></li>
  <li>若有啟用 Google Drive，確認「檔案」欄位顯示 <code>DRIVE:資料夾名稱/檔名</code></li>
</ol>
"""

    def _build_decrypt_help_html(self) -> str:
        return """
<style>
  body { line-height: 1.5; margin: 0; padding: 0 0 18px 0; }
  pre { white-space: pre-wrap; word-break: break-all; background: #FAF5EF; padding: 10px; border-radius: 6px; }
  h2, h3 { margin-top: 10px; margin-bottom: 6px; }
  p { margin: 6px 0; }
  ol { margin-top: 4px; margin-bottom: 10px; }
</style>
<h2>解密備份說明</h2>
<p>此功能頁提供的是<strong>管理員人工維運說明</strong>。目前正式保存格式為 <code>temple.db.enc</code>，不是明文 <code>temple.db</code>。</p>

<h3>1. 金鑰存放位置</h3>
<ol>
  <li>地端資料庫金鑰：<code>local/data_encryption_key/current</code></li>
  <li>雲端備份金鑰：<code>backup/cloud_encryption_key/current</code></li>
  <li>Windows 透過 <code>Credential Manager</code> 保存，macOS 透過 <code>Keychain</code> 保存。</li>
</ol>

<h3>2. 取得地端資料庫金鑰</h3>
<pre>source temple_venv/bin/activate
python -c "from app.utils.secret_store import get_secret; print(get_secret('local/data_encryption_key/current'))"</pre>

<h3>3. 手動解開既有 temple.db.enc 供檢查</h3>
<p>先將正式保存的 <code>temple.db.enc</code> 放在目前工作目錄，再執行：</p>
<pre>source temple_venv/bin/activate
python -c "from pathlib import Path; from cryptography.fernet import Fernet; from app.utils.secret_store import get_secret; key = get_secret('local/data_encryption_key/current').encode('utf-8'); plain = Fernet(key).decrypt(Path('temple.db.enc').read_bytes()); Path('temple_manual_open.db').write_bytes(plain); print(Path('temple_manual_open.db').resolve())"</pre>
<p>完成後會得到可人工查看的明文 SQLite 檔：<code>temple_manual_open.db</code></p>

<h3>4. 手動搬入新的資料庫（例如 b_DB 取代原本 a_DB）</h3>
<p>若你已經手動準備好新的明文 SQLite 檔，例如 <code>b_DB</code>，正式流程是<strong>先加密成 .enc，再取代正式資料檔</strong>，不建議再直接以明文 DB 覆蓋。</p>
<ol>
  <li>先關閉 TempleManager。</li>
  <li>將新的明文 SQLite 檔放在目前工作目錄，例如檔名為 <code>b_DB</code>。</li>
  <li>執行下列指令，將 <code>b_DB</code> 加密成新的 <code>temple.db.enc</code>：</li>
</ol>
<pre>source temple_venv/bin/activate
python -c "from pathlib import Path; from cryptography.fernet import Fernet; from app.utils.secret_store import get_secret; key = get_secret('local/data_encryption_key/current').encode('utf-8'); token = Fernet(key).encrypt(Path('b_DB').read_bytes()); Path('temple.db.enc').write_bytes(token); print(Path('temple.db.enc').resolve())"</pre>
<ol>
  <li>用新產生的 <code>temple.db.enc</code> 取代正式保存位置的檔案。</li>
  <li>重新開啟程式驗證資料內容。</li>
</ol>

<h3>5. 正式維運原則</h3>
<ol>
  <li>正式保存格式應為 <code>temple.db.enc</code>。</li>
  <li>若要人工搬資料，請先把新的明文 DB 加密成 <code>.enc</code> 後再替換。</li>
  <li>不要把明文 DB 當成正式保存檔長期保留。</li>
</ol>

<h3>6. 安全提醒</h3>
<ol>
  <li>僅限管理員維運用途。</li>
  <li>解出的 <code>temple_manual_open.db</code> 為明文資料庫，查看後應立即刪除。</li>
  <li>不要將明文 DB 上傳雲端、留在共用資料夾、或直接拿來當正式保存檔。</li>
</ol>
"""
