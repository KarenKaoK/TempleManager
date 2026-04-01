import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class ReportScheduleSettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("報表排程設定")
        self._mail_settings = {
            "smtp_username": "",
            "smtp_password_set": False,
        }
        self._saved_config_path = ""
        self.resize(980, 500)
        self.setMinimumSize(860, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setFormAlignment(Qt.AlignTop)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.lbl_scheduler_status = QLabel("")
        self.lbl_mail_enabled = QLabel("")
        self.edt_smtp_username = QLineEdit("")
        self.edt_smtp_username.setPlaceholderText("Gmail 帳號（例如 your@gmail.com）")
        self.edt_smtp_password = QLineEdit("")
        self.edt_smtp_password.setEchoMode(QLineEdit.Password)
        self.edt_smtp_password.setPlaceholderText("App Password（留空表示不變更）")
        self.btn_save_settings = QPushButton("儲存設定")
        self.btn_save_settings.setEnabled(False)
        self.btn_save_settings.clicked.connect(self._save_settings)
        self.edt_smtp_username.textChanged.connect(self._update_save_button_state)
        self.edt_config_path = QLineEdit("")
        self.edt_config_path.setReadOnly(True)
        self.edt_config_path.setPlaceholderText("scheduler_config.yaml 路徑")
        self.btn_select_config = QPushButton("選擇檔案")
        self.btn_select_config.clicked.connect(self._select_config_file)
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(8)
        path_row.addWidget(self.edt_config_path, 1)
        path_row.addWidget(self.btn_select_config)
        path_wrap = QWidget()
        path_wrap.setLayout(path_row)

        form.addRow("排程服務", self.lbl_scheduler_status)
        form.addRow("報表郵件排程", self.lbl_mail_enabled)
        form.addRow("Gmail 帳號", self.edt_smtp_username)
        form.addRow("Gmail 密碼", self.edt_smtp_password)
        form.addRow("設定檔路徑", path_wrap)
        form.addRow("", self.btn_save_settings)
        self.lbl_toggle_hint = QLabel("提示：手動修改 scheduler_config.yaml 後，外部排程 worker 會依最新設定執行。")
        self.lbl_toggle_hint.setWordWrap(True)
        self.lbl_toggle_hint.setStyleSheet("QLabel { color:#6B7280; }")
        hint_wrap = QWidget()
        hint_layout = QVBoxLayout(hint_wrap)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.setSpacing(0)
        hint_layout.addWidget(self.lbl_toggle_hint, 0, Qt.AlignLeft)
        form.addRow("", hint_wrap)
        root.addWidget(form_wrap)

        root.addSpacing(4)

        row_btn = QHBoxLayout()
        self.btn_toggle_mail = QPushButton("停用 Email 排程")
        self.btn_reload_schedule = QPushButton("重新載入排程")
        self.btn_reload_schedule.clicked.connect(self._reload_schedule)
        self.btn_toggle_mail.clicked.connect(self._toggle_mail_schedule)
        self.btn_open_config_dir = QPushButton("開啟設定檔位置")
        self.btn_worker_help = QPushButton("外部常駐 worker 設定說明")
        self.btn_close = QPushButton("關閉")
        self.btn_open_config_dir.clicked.connect(self._open_config_dir)
        self.btn_worker_help.clicked.connect(self._show_external_worker_help)
        self.btn_close.clicked.connect(self.accept)
        row_btn.addWidget(self.btn_toggle_mail)
        row_btn.addWidget(self.btn_reload_schedule)
        row_btn.addWidget(self.btn_open_config_dir)
        row_btn.addWidget(self.btn_worker_help)
        row_btn.addWidget(self.btn_close)
        row_btn.addStretch()
        root.addLayout(row_btn)

        self._refresh_status()

    def _config_path(self) -> str:
        getter = getattr(self.controller, "get_scheduler_config_path", None)
        cfg_path = ""
        if callable(getter):
            try:
                cfg_path = str(getter() or "")
            except Exception:
                cfg_path = ""
        if not cfg_path:
            cfg_path = "app/scheduler/scheduler_config.yaml"
        return os.path.abspath(cfg_path)

    def _feature_flags(self):
        flags = {"mail_enabled": True, "backup_enabled": True}
        getter = getattr(self.controller, "get_scheduler_feature_settings", None)
        if callable(getter):
            try:
                flags.update(getter() or {})
            except Exception:
                pass
        return flags

    def _refresh_status(self):
        self.lbl_scheduler_status.setText("由外部常駐 worker 執行")

        mail_enabled = bool(self._feature_flags().get("mail_enabled", True))
        mail_info = self._current_mail_settings()
        self._mail_settings = {
            "smtp_username": str(mail_info.get("smtp_username") or ""),
            "smtp_password_set": bool(mail_info.get("smtp_password_set")),
        }
        self.edt_smtp_username.setText(self._mail_settings["smtp_username"])
        self.edt_smtp_password.clear()
        pwd_text = "已設定" if self._mail_settings["smtp_password_set"] else "未設定"
        backend = str(mail_info.get("secret_backend") or "")
        backend_text = f"｜安全儲存：{backend}" if backend else ""
        self.lbl_mail_enabled.setText(("已啟用" if mail_enabled else "未啟用") + f"｜密碼：{pwd_text}{backend_text}")
        self.btn_toggle_mail.setText("停用 Email 排程" if mail_enabled else "啟用 Email 排程")
        path = self._config_path()
        self._saved_config_path = path
        self.edt_config_path.setText(path)
        self.edt_config_path.setCursorPosition(0)
        self.edt_config_path.setToolTip(path)
        self._update_save_button_state()

    def _current_mail_settings(self):
        getter = getattr(self.controller, "get_scheduler_mail_settings", None)
        mail_info = {"smtp_username": "", "smtp_password_set": False, "secret_backend": "", "secret_error": ""}
        if callable(getter):
            try:
                mail_info.update(getter() or {})
            except Exception:
                pass
        return mail_info

    def _update_save_button_state(self):
        username_changed = (self.edt_smtp_username.text() or "").strip() != self._mail_settings.get("smtp_username", "")
        password_changed = bool(self.edt_smtp_password.text())
        path_changed = os.path.abspath(self.edt_config_path.text() or "") != os.path.abspath(self._saved_config_path or "")
        self.btn_save_settings.setEnabled(username_changed or password_changed or path_changed)

    def _open_config_dir(self):
        cfg_path = os.path.abspath(self.edt_config_path.text() or self._config_path())
        folder = os.path.dirname(cfg_path)
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "路徑不存在", f"找不到設定檔資料夾：\n{folder}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    @staticmethod
    def _external_worker_help_html() -> str:
        return """
<style>
  body { font-family: sans-serif; line-height: 1.55; }
  h3 { margin: 10px 0 6px; }
  p { margin: 6px 0; }
  li { margin: 4px 0; }
  pre {
    white-space: pre-wrap;
    word-break: break-all;
    background: #FAF5EF;
    padding: 10px;
    border-radius: 6px;
  }
</style>
<h3>用途</h3>
<p>主程式 / EXE 與 worker 已分離；UI 只負責設定，正式寄信與報表排程請由外部常駐 worker 獨立執行。</p>

<h3>執行指令</h3>
<pre>python -m app.scheduler.worker</pre>
<p>建議使用專案虛擬環境的 Python。</p>

<h3>設定檔</h3>
<p>目前畫面中的「設定檔路徑」就是 worker 會使用的 <code>scheduler_config.yaml</code>。首次使用時，系統會先將模板複製到使用者資料目錄，也可以自行改選其他外部檔案。</p>
<p>「儲存設定」用在 Gmail 帳密或 <code>scheduler_config.yaml</code> 路徑變更；「重新載入排程」用在 <code>scheduler_config.yaml</code> 內容變更。</p>
<p>reload 會先寫入 worker DB 註記，背景 worker 每 5 秒檢查一次並套用新設定。</p>

<h3>Windows</h3>
<ol>
  <li>開啟「工作排程器」，建議使用「建立工作」而非「建立基本工作」。</li>
  <li>觸發程序可設為「使用者登入時」或「開機時」。</li>
  <li>Windows 建議透過「工作排程器」啟動 worker。</li>
  <li>動作請填：</li>
</ol>
<pre>Program/script: temple_venv\\Scripts\\python.exe
Add arguments: -m app.scheduler.worker
Start in: 專案根目錄</pre>
<ol start="5">
  <li>若使用 UI 儲存 Gmail 帳號與 App Password，工作排程器的執行 Windows 使用者必須與當初儲存該密碼的 Windows 使用者一致，否則無法從 Credential Manager 讀到密碼。</li>
  <li>儲存後可先手動執行一次，確認 worker 能正常常駐。</li>
</ol>

<h3>macOS</h3>
<ol>
  <li>在 <code>~/Library/LaunchAgents/</code> 建立 plist。</li>
  <li><code>ProgramArguments</code> 指向虛擬環境 Python，例如：</li>
</ol>
<pre>./temple_venv/bin/python -m app.scheduler.worker</pre>
<ol start="3">
  <li><code>WorkingDirectory</code> 設為專案根目錄。</li>
  <li>使用 <code>launchctl load</code> 或 <code>launchctl bootstrap</code> 啟用。</li>
  <li>可用 <code>launchctl list</code> 確認是否成功載入。</li>
</ol>

<h3>注意</h3>
<ul>
  <li>請勿同時恢復主程式內建 scheduler 啟動入口，避免重複寄送。</li>
  <li>worker 啟動時會優先讀取 UI 已儲存的設定檔路徑與功能旗標；若無法載入正式 app 設定，會直接報錯。</li>
</ul>
"""

    def _show_external_worker_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("外部常駐 worker 設定說明")
        dialog.resize(720, 620)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._external_worker_help_html())
        root.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        root.addWidget(buttons)

        dialog.exec_()

    def _select_config_file(self):
        start_path = self._config_path()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 scheduler_config.yaml",
            start_path,
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        path = os.path.abspath(path)
        self.edt_config_path.setText(path)
        self.edt_config_path.setCursorPosition(0)
        self.edt_config_path.setToolTip(path)
        self._update_save_button_state()

    def _toggle_mail_schedule(self):
        flags = self._feature_flags()
        next_mail = not bool(flags.get("mail_enabled", True))
        cfg_path = os.path.abspath(self.edt_config_path.text() or self._config_path())

        if next_mail and not os.path.isfile(cfg_path):
            QMessageBox.warning(self, "無法啟用", "請先選擇有效的 scheduler_config.yaml 檔案。")
            return
        if next_mail:
            getter = getattr(self.controller, "get_scheduler_mail_settings", None)
            if callable(getter):
                try:
                    info = getter() or {}
                    if str(info.get("secret_error") or "").strip():
                        QMessageBox.warning(
                            self,
                            "無法啟用",
                            f"安全儲存異常：{info.get('secret_error')}",
                        )
                        return
                    if not info.get("smtp_username"):
                        QMessageBox.warning(self, "無法啟用", "請先設定 Gmail 帳號。")
                        return
                    if not bool(info.get("smtp_password_set")):
                        QMessageBox.warning(self, "無法啟用", "請先儲存 Gmail 密碼。")
                        return
                except Exception as e:
                    QMessageBox.warning(self, "無法啟用", f"檢查郵件設定失敗：{e}")
                    return

        saver = getattr(self.controller, "save_scheduler_feature_settings", None)
        if callable(saver):
            try:
                saver(
                    {
                        "mail_enabled": next_mail,
                        "backup_enabled": bool(flags.get("backup_enabled", True)),
                    }
                )
            except Exception as e:
                QMessageBox.warning(self, "儲存失敗", str(e))
                return
        self._refresh_status()
        QMessageBox.information(self, "完成", "Email 排程設定已更新。")

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

    def _save_settings(self):
        username = (self.edt_smtp_username.text() or "").strip()
        password = self.edt_smtp_password.text() or ""
        if not username:
            QMessageBox.warning(self, "設定錯誤", "請先輸入 Gmail 帳號。")
            return
        current_getter = getattr(self.controller, "get_scheduler_mail_settings", None)
        current = {}
        if callable(current_getter):
            try:
                current = current_getter() or {}
            except Exception:
                current = {}
        if not password and not bool(current.get("smtp_password_set")):
            QMessageBox.warning(self, "設定錯誤", "首次儲存需輸入 Gmail 密碼。")
            return
        config_path = os.path.abspath(self.edt_config_path.text() or "")
        if not config_path:
            QMessageBox.warning(self, "設定錯誤", "請先選擇 scheduler_config.yaml 檔案。")
            return
        mail_saver = getattr(self.controller, "save_scheduler_mail_settings", None)
        path_saver = getattr(self.controller, "save_scheduler_config_path", None)
        reload_requester = getattr(self.controller, "_request_worker_reload", None)
        if not callable(mail_saver) or not callable(path_saver) or not callable(reload_requester):
            QMessageBox.warning(self, "儲存失敗", "目前控制器不支援報表排程設定。")
            return
        try:
            mail_saver(username, password, request_reload=False)
            path_saver(config_path, request_reload=False)
            reload_requester()
        except Exception as e:
            QMessageBox.warning(self, "儲存失敗", str(e))
            return
        self._refresh_status()
        QMessageBox.information(self, "完成", "報表排程設定已儲存，已通知背景 worker 重新載入設定。")
