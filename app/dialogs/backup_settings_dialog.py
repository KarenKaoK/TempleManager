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
    QWidget,
    QHeaderView,
)

from app.controller.app_controller import AppController


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
        form.setVerticalSpacing(10)

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

        self.chk_use_cli_scheduler = QCheckBox("改用 CLI/作業系統排程（登出或未開啟程式也能備份）")
        form.addRow("排程模式", self.chk_use_cli_scheduler)

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
            "use_cli_scheduler": self.chk_use_cli_scheduler.isChecked(),
        }


class GoogleSettingsDialog(QDialog):
    def __init__(
        self,
        controller,
        drive_folder_id: str,
        oauth_client_secret_path: str,
        oauth_token_path: str,
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
        self.edt_oauth_client_secret.setText(oauth_client_secret_path or "")
        self.btn_pick_oauth_client = QPushButton("選擇檔案")
        self.btn_pick_oauth_client.clicked.connect(self._pick_oauth_client_file)
        form.addRow("OAuth 憑證 JSON", self._line_with_button(self.edt_oauth_client_secret, self.btn_pick_oauth_client))

        self.edt_oauth_token = QLineEdit()
        self.edt_oauth_token.setPlaceholderText("OAuth token.json 路徑（必填，第一次可留空）")
        self.edt_oauth_token.setText(oauth_token_path or "")
        self.btn_pick_oauth_token = QPushButton("選擇檔案")
        self.btn_pick_oauth_token.clicked.connect(self._pick_oauth_token_file)
        form.addRow("OAuth Token 檔案", self._line_with_button(self.edt_oauth_token, self.btn_pick_oauth_token))

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

    def _pick_oauth_token_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "選擇 OAuth token.json",
            self.edt_oauth_token.text() or "",
            "JSON Files (*.json);;All Files (*)",
        )
        if path:
            self.edt_oauth_token.setText(path)

    def _authorize_google(self):
        try:
            client_path = (self.edt_oauth_client_secret.text() or "").strip()
            token_path = (self.edt_oauth_token.text() or "").strip()
            if not client_path:
                QMessageBox.warning(self, "設定錯誤", "請先設定 OAuth 憑證 JSON")
                return
            result = self.controller.authorize_google_drive_oauth(client_path, token_path)
            self.edt_oauth_token.setText(result.get("token_path", token_path))
            email = result.get("email", "")
            tip = f"Google 授權成功\n帳號：{email}" if email else "Google 授權成功"
            QMessageBox.information(self, "成功", tip)
        except Exception as e:
            QMessageBox.warning(self, "授權失敗", str(e))

    def get_values(self) -> dict:
        return {
            "drive_folder_id": (self.edt_drive_folder.text() or "").strip(),
            "oauth_client_secret_path": (self.edt_oauth_client_secret.text() or "").strip(),
            "oauth_token_path": (self.edt_oauth_token.text() or "").strip(),
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
        self._schedule_enabled = False
        self._schedule_frequency = "daily"
        self._schedule_time = "23:00"
        self._schedule_weekday = 1
        self._schedule_monthday = 1
        self._google_drive_folder_id = ""
        self._google_oauth_client_secret_path = ""
        self._google_oauth_token_path = ""
        self._schedule_use_cli = False
        self._backup_thread = None
        self._backup_worker = None
        self._backup_running = False
        self.setWindowTitle("資料備份")
        self._resize_like_main_window(parent)
        self._build_ui()
        self._load_settings()
        self._reload_logs(limit=80)
        self._log_reload_pending = False
        self._backup_notice_reset_timer = None
        self._apply_font_safe_heights()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        form_box = QWidget()
        form = QFormLayout(form_box)
        self._form = form
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setFormAlignment(Qt.AlignTop)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.lbl_schedule_summary = QLabel("")
        self.lbl_schedule_summary.setWordWrap(True)
        self.btn_schedule_settings = QPushButton("排程設定")
        self.btn_schedule_settings.clicked.connect(self._open_schedule_settings_dialog)
        schedule_row = QHBoxLayout()
        schedule_row.setContentsMargins(0, 0, 0, 0)
        schedule_row.setSpacing(8)
        schedule_row.addWidget(self.lbl_schedule_summary, 1)
        schedule_row.addWidget(self.btn_schedule_settings)
        schedule_wrap = QWidget()
        schedule_wrap.setLayout(schedule_row)
        form.addRow("排程", schedule_wrap)

        self.spin_keep = QSpinBox()
        self.spin_keep.setRange(1, 500)
        form.addRow("保留最新備份數", self.spin_keep)

        self.edt_local_dir = QLineEdit()
        self.edt_local_dir.setPlaceholderText("可留空，使用預設 app/database/backups")
        form.addRow("本機備份路徑", self.edt_local_dir)

        self.chk_enable_local = QCheckBox("本機備份")
        self.chk_enable_local.setChecked(True)
        self.chk_enable_drive = QCheckBox("Google Drive（OAuth）")
        target_row = QHBoxLayout()
        target_row.addWidget(self.chk_enable_local)
        target_row.addWidget(self.chk_enable_drive)
        target_row.addStretch()
        target_wrap = QWidget()
        target_wrap.setLayout(target_row)
        form.addRow("備份目的地", target_wrap)

        self.lbl_google_summary = QLabel("")
        self.lbl_google_summary.setWordWrap(True)
        self.btn_google_settings = QPushButton("Google 設定")
        self.btn_google_settings.clicked.connect(self._open_google_settings_dialog)
        google_row = QHBoxLayout()
        google_row.setContentsMargins(0, 0, 0, 0)
        google_row.setSpacing(8)
        google_row.addWidget(self.lbl_google_summary, 1)
        google_row.addWidget(self.btn_google_settings)
        google_wrap = QWidget()
        google_wrap.setLayout(google_row)
        form.addRow("Google", google_wrap)

        root.addWidget(form_box)

        runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backup_runner.py"))
        py_exec = sys.executable or "python"
        cli_module_cmd = f"{py_exec} -m app.backup_runner --run-once"
        cli_file_cmd = f"{py_exec} {runner_path} --run-once"
        help_text = (
            "詳細設定流程請按「說明文件」。"
        )
        self.lbl_cli_help = QLabel(help_text)
        self.lbl_cli_help.setWordWrap(True)
        self.lbl_cli_help.setStyleSheet("QLabel { color:#6B7280; }")
        root.addWidget(self.lbl_cli_help)

        row_btn = QHBoxLayout()
        self.btn_save = QPushButton("儲存設定")
        self.btn_backup_now = QPushButton("立即備份")
        self.btn_refresh = QPushButton("重新整理紀錄")
        self.btn_help_doc = QPushButton("說明文件")
        self.btn_close = QPushButton("關閉")
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_backup_now.clicked.connect(self._run_manual_backup)
        self.btn_refresh.clicked.connect(lambda: self._reload_logs(auto_resize=True, limit=200))
        self.btn_help_doc.clicked.connect(self._open_help_document)
        self.btn_close.clicked.connect(self.accept)
        row_btn.addWidget(self.btn_save)
        row_btn.addWidget(self.btn_backup_now)
        row_btn.addWidget(self.btn_refresh)
        row_btn.addWidget(self.btn_help_doc)
        row_btn.addStretch()
        row_btn.addWidget(self.btn_close)
        root.addLayout(row_btn)

        self.lbl_backup_notice = QLabel("")
        self.lbl_backup_notice.setWordWrap(True)
        self.lbl_backup_notice.setStyleSheet("QLabel { color:#6B7280; }")
        root.addWidget(self.lbl_backup_notice)

        root.addWidget(QLabel("備份紀錄"))
        self.table_logs = QTableWidget(0, 6)
        self.table_logs.setHorizontalHeaderLabels(["時間", "觸發", "狀態", "檔案", "大小", "錯誤訊息"])
        self.table_logs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_logs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setStretchLastSection(False)
        self.table_logs.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_logs.setTextElideMode(Qt.ElideNone)
        self.table_logs.verticalHeader().setDefaultSectionSize(30)
        self.table_logs.setMinimumHeight(260)
        root.addWidget(self.table_logs, 1)

        self._apply_form_field_width_policy()

    def _apply_form_field_width_policy(self):
        """
        避免 QComboBox/QSpinBox 在 FormLayout 中被壓成窄欄。
        """
        expand_widgets = [
            self.spin_keep,
            self.btn_google_settings,
            self.btn_schedule_settings,
        ]
        for w in expand_widgets:
            sp = w.sizePolicy()
            sp.setHorizontalPolicy(QSizePolicy.Expanding)
            w.setSizePolicy(sp)

        # 下拉與數字欄給最小寬度，避免只顯示 1~2 個字
        self.spin_keep.setMinimumWidth(170)

    def _apply_font_safe_heights(self):
        """
        依目前字體大小動態撐高控制項，避免字體放大後輸入框吃字。
        """
        fm_h = max(18, self.fontMetrics().height())
        line_h = fm_h + 16
        btn_h = fm_h + 14

        line_like = [
            self.edt_local_dir,
            self.spin_keep,
        ]
        for w in line_like:
            w.setMinimumHeight(max(w.minimumHeight(), line_h))

        controls = [
            self.btn_google_settings,
            self.btn_schedule_settings,
            self.btn_save,
            self.btn_backup_now,
            self.btn_refresh,
            self.btn_help_doc,
            self.btn_close,
            self.lbl_backup_notice,
        ]
        for b in controls:
            if hasattr(b, "setMinimumHeight"):
                b.setMinimumHeight(max(b.minimumHeight(), btn_h))
        self.lbl_google_summary.setMinimumHeight(max(self.lbl_google_summary.minimumHeight(), line_h))
        self.lbl_schedule_summary.setMinimumHeight(max(self.lbl_schedule_summary.minimumHeight(), line_h))

        # 同步調整左側標籤欄，避免字體放大後重疊
        max_label_w = 0
        for row in range(self._form.rowCount()):
            item = self._form.itemAt(row, QFormLayout.LabelRole)
            if not item or not item.widget():
                continue
            lbl = item.widget()
            lbl.setMinimumHeight(max(lbl.minimumHeight(), line_h))
            try:
                max_label_w = max(max_label_w, lbl.fontMetrics().horizontalAdvance(lbl.text()))
            except Exception:
                pass
        if max_label_w > 0:
            target_label_w = min(320, max(150, max_label_w + 20))
            for row in range(self._form.rowCount()):
                item = self._form.itemAt(row, QFormLayout.LabelRole)
                if item and item.widget():
                    item.widget().setMinimumWidth(target_label_w)

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

            # 接近主視窗尺寸（預留少量邊距）
            w = int(parent_w * 0.94)
            h = int(parent_h * 0.90)
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
        self._schedule_enabled = bool(s.get("enabled"))
        self._schedule_frequency = str(s.get("frequency", "daily"))
        self._schedule_time = str(s.get("time", "23:00"))
        self._schedule_weekday = int(s.get("weekday", 1))
        self._schedule_monthday = int(s.get("monthday", 1))
        self._schedule_use_cli = bool(s.get("use_cli_scheduler"))
        self.spin_keep.setValue(int(s.get("keep_latest", 20)))
        self.edt_local_dir.setText(str(s.get("local_dir", "")))
        self.chk_enable_local.setChecked(bool(s.get("enable_local", True)))
        self.chk_enable_drive.setChecked(bool(s.get("enable_drive", False)))
        self._google_oauth_client_secret_path = str(s.get("oauth_client_secret_path", ""))
        self._google_oauth_token_path = str(s.get("oauth_token_path", ""))
        self._google_drive_folder_id = str(s.get("drive_folder_id", ""))
        self._update_google_summary()
        self._update_schedule_summary()

    def _set_combo_data(self, combo: QComboBox, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _weekday_label(self, weekday: int) -> str:
        mapping = {1: "週一", 2: "週二", 3: "週三", 4: "週四", 5: "週五", 6: "週六", 7: "週日"}
        return mapping.get(int(weekday or 1), "週一")

    def _frequency_label(self, frequency: str) -> str:
        mapping = {"daily": "每日", "weekly": "每週", "monthly": "每月"}
        return mapping.get(frequency or "daily", "每日")

    def _update_schedule_summary(self):
        freq_label = self._frequency_label(self._schedule_frequency)
        enabled_text = "已啟用" if self._schedule_enabled else "未啟用"
        if self._schedule_frequency == "weekly":
            detail = f"{freq_label} {self._weekday_label(self._schedule_weekday)} {self._schedule_time}"
        elif self._schedule_frequency == "monthly":
            detail = f"{freq_label} 每月 {self._schedule_monthday} 日 {self._schedule_time}"
        else:
            detail = f"{freq_label} {self._schedule_time}"
        mode_text = "CLI/OS 排程" if self._schedule_use_cli else "程式內建排程"
        self.lbl_schedule_summary.setText(f"{enabled_text}｜{detail}｜{mode_text}")

    def _open_schedule_settings_dialog(self):
        dialog = ScheduleSettingsDialog(
            enabled=self._schedule_enabled,
            frequency=self._schedule_frequency,
            time_text=self._schedule_time,
            weekday=self._schedule_weekday,
            monthday=self._schedule_monthday,
            use_cli_scheduler=self._schedule_use_cli,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.get_values()
        self._schedule_enabled = bool(values.get("enabled"))
        self._schedule_frequency = str(values.get("frequency", "daily"))
        self._schedule_time = str(values.get("time", "23:00"))
        self._schedule_weekday = int(values.get("weekday", 1))
        self._schedule_monthday = int(values.get("monthday", 1))
        self._schedule_use_cli = bool(values.get("use_cli_scheduler"))
        self._update_schedule_summary()

    def _update_google_summary(self):
        cred_text = "已設定" if (self._google_oauth_client_secret_path or "").strip() else "未設定"
        token_text = "已設定" if (self._google_oauth_token_path or "").strip() else "未設定"
        folder_text = self._google_drive_folder_id if (self._google_drive_folder_id or "").strip() else "未設定"
        self.lbl_google_summary.setText(f"憑證：{cred_text}｜Token：{token_text}｜資料夾：{folder_text}")

    def _open_google_settings_dialog(self):
        dialog = GoogleSettingsDialog(
            controller=self.controller,
            drive_folder_id=self._google_drive_folder_id,
            oauth_client_secret_path=self._google_oauth_client_secret_path,
            oauth_token_path=self._google_oauth_token_path,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.get_values()
        self._google_drive_folder_id = values.get("drive_folder_id", "")
        self._google_oauth_client_secret_path = values.get("oauth_client_secret_path", "")
        self._google_oauth_token_path = values.get("oauth_token_path", "")
        self._update_google_summary()

    def _build_settings_payload(self) -> dict:
        return {
            "enabled": self._schedule_enabled,
            "frequency": self._schedule_frequency,
            "time": self._schedule_time,
            "weekday": self._schedule_weekday,
            "monthday": self._schedule_monthday,
            "keep_latest": int(self.spin_keep.value()),
            "local_dir": (self.edt_local_dir.text() or "").strip(),
            "enable_local": self.chk_enable_local.isChecked(),
            "enable_drive": self.chk_enable_drive.isChecked(),
            "oauth_client_secret_path": (self._google_oauth_client_secret_path or "").strip(),
            "oauth_token_path": (self._google_oauth_token_path or "").strip(),
            "drive_folder_id": (self._google_drive_folder_id or "").strip(),
            "use_cli_scheduler": self._schedule_use_cli,
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
            self.controller.save_backup_settings(payload)
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
        if callable(mark_run):
            try:
                mark_run()
            except Exception:
                pass
        self._set_manual_backup_running(False)
        self._show_backup_notice(
            f"備份完成：{result.get('backup_file','')}（{result.get('file_size_bytes',0)} bytes）",
            is_error=False,
        )
        self._schedule_log_reload()

    def _on_manual_backup_failed(self, error_text: str):
        self._schedule_log_reload()
        self._set_manual_backup_running(False)
        self._show_backup_notice(f"備份失敗：{error_text}", is_error=True)
        QMessageBox.warning(self, "備份失敗", error_text)

    def _show_backup_notice(self, text: str, is_error: bool = False):
        self.lbl_backup_notice.setText(text or "")
        color = "#B91C1C" if is_error else "#065F46"
        self.lbl_backup_notice.setStyleSheet(f"QLabel {{ color:{color}; }}")
        if self._backup_notice_reset_timer is None:
            self._backup_notice_reset_timer = QTimer(self)
            self._backup_notice_reset_timer.setSingleShot(True)
            self._backup_notice_reset_timer.timeout.connect(self._clear_backup_notice)
        self._backup_notice_reset_timer.start(8000)

    def _clear_backup_notice(self):
        self.lbl_backup_notice.setText("")
        self.lbl_backup_notice.setStyleSheet("QLabel { color:#6B7280; }")

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
            try:
                self._backup_worker.deleteLater()
            except Exception:
                pass
        if self._backup_thread is not None:
            try:
                self._backup_thread.deleteLater()
            except Exception:
                pass
        self._backup_worker = None
        self._backup_thread = None

    def _set_manual_backup_running(self, running: bool):
        self._backup_running = bool(running)
        self.btn_backup_now.setEnabled(not running)
        self.btn_save.setEnabled(not running)
        self.btn_refresh.setEnabled(not running)
        self.btn_backup_now.setText("備份中..." if running else "立即備份")

    def _reload_logs(self, auto_resize: bool = True, limit: int = 200):
        rows = self.controller.list_backup_logs(limit=limit)
        self.table_logs.setRowCount(len(rows))
        for i, r in enumerate(rows):
            size_bytes = r.get("file_size_bytes")
            vals = [
                str(r.get("created_at") or ""),
                str(r.get("trigger_mode") or ""),
                str(r.get("status") or ""),
                str(r.get("backup_file") or ""),
                self._format_bytes_human(size_bytes),
                str(r.get("error_message") or ""),
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

    def _build_help_document_html(self) -> str:
        runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backup_runner.py"))
        py_exec = sys.executable or "python"
        cli_module_cmd = f"{py_exec} -m app.backup_runner --run-once"
        cli_file_cmd = f"{py_exec} {runner_path} --run-once"
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
  <li><b>啟用自動備份</b>：代表允許排程判斷生效。</li>
  <li><b>改用 CLI/作業系統排程</b>：
    <ul>
      <li>勾選：由 OS 排程器呼叫 CLI（登出或程式未開啟也可執行）</li>
      <li>未勾選：由程式內建排程觸發（程式需開啟）</li>
    </ul>
  </li>
  <li><b>CLI 模式仍會看 UI 頻率</b>：OS 只負責呼叫，是否真的備份仍依 UI 設定（每日/每週/每月、時間、週幾/幾號）。</li>
  <li><b>立即備份</b>：按下就執行，不看排程時間，依當下勾選目的地備份（本機 / Drive / 雙寫）。</li>
  <li>Google Drive 採 OAuth 模式：首次需人工授權一次，後續由 token 自動續期。</li>
</ol>

<h3>2. 建議設定流程（先後順序）</h3>
<p>
  若目標是「登出狀態也要自動備份」，建議：
  1) 先準備 credentials.json 並完成首次 OAuth 授權，
  2) 再設定 CLI/OS 排程，
  3) 最後回系統填目的地與參數。
</p>
<ol>
  <li>步驟 1：先完成 Google OAuth 設定與首次授權</li>
  <li>步驟 2：設定 CLI/OS 排程（Windows 工作排程器或 macOS launchd）</li>
  <li>步驟 3：回到系統內填入 JSON 路徑、資料夾 ID、目的地與保留數量</li>
  <li>步驟 4：執行「立即備份」與 CLI <code>--run-once</code> 各驗證一次</li>
</ol>

<h3>3. CLI 指令（給 OS 排程器呼叫）</h3>
<pre>Module: {cli_module_cmd}
File:   {cli_file_cmd}</pre>

<h3>4. Google Drive OAuth 設定</h3>
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

<p><b>第二步：系統內填寫路徑與資料夾</b></p>
<ol>
  <li>填入 OAuth 憑證 JSON 路徑（credentials.json）</li>
  <li>OAuth token 路徑建議先指定儲存位置（建議專案外；首次授權後會建立/更新）</li>
  <li>按「Google 授權（首次）」後，系統才會建立/更新 token.json</li>
  <li>填入 Drive 資料夾 ID</li>
</ol>

<p><b>第三步：首次人工授權</b></p>
<ol>
  <li>按「Google 授權（首次）」並完成瀏覽器登入同意</li>
  <li>系統會產生/更新 token.json，後續可自動 refresh</li>
</ol>

<p><b>第四步：確認 API 已啟用</b></p>
<ol>
  <li>Google Cloud Console → API 和服務 → 啟用 API 和服務</li>
  <li>確認 Google Drive API 顯示為「已啟用」</li>
</ol>

<h3>5. Windows（工作排程器）</h3>
<ol>
  <li>開啟「工作排程器」→ 建立工作</li>
  <li>觸發條件設每日 / 每週 / 每月</li>
  <li>動作填入：<code>python -m app.backup_runner --run-once</code></li>
  <li>起始於（Start in）設為專案根目錄（含 <code>app/</code> 的資料夾）</li>
</ol>

<h3>6. macOS（launchd）</h3>
<ol>
  <li>建立 plist 呼叫：<code>python -m app.backup_runner --run-once</code></li>
  <li>WorkingDirectory 指向專案根目錄</li>
  <li>以 <code>launchctl load</code> 啟用排程</li>
</ol>
"""
