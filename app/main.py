# app/main.py
import sys
import sqlite3
from pathlib import Path
from app.config import DB_NAME
from app.database.setup_db import initialize_database
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5 import sip as pyqt_sip
from app.controller.app_controller import AppController
from app.auth.login import LoginDialog
from app.main_window import MainWindow
from app.scheduler.service import SchedulerService
from app.utils.dialog_localizer import install_dialog_localizer
from app.utils.font_manager import GlobalFontManager

def _has_required_schema(db_file: Path) -> bool:
    conn = None
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_settings' LIMIT 1"
        )
        return cursor.fetchone() is not None
    except sqlite3.DatabaseError:
        return False
    finally:
        if conn is not None:
            conn.close()


def ensure_database_ready(db_path=DB_NAME):
    db_file = Path(db_path)
    if db_file.is_file():
        if _has_required_schema(db_file):
            return
    db_file.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(str(db_file))


def run_app():
    ensure_database_ready()
    # 避免 PyQt5 在 Python 結束階段清理 QObject 時偶發 segfault
    # （常見於 macOS / PyQt5 / sip 組合）
    try:
        if hasattr(pyqt_sip, "setdestroyonexit"):
            pyqt_sip.setdestroyonexit(False)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        /* === 全域基礎 === */
        QWidget {
            background-color: #FFFFFF;
            color: #2B2B2B;
        }

        /* === 輸入元件 === */
        QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
            background: #FFFFFF;
            border: 1px solid #DADADA;
            border-radius: 8px;
            padding: 4px 8px;
            color: #222;
            min-height: 24px;
        }
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
            border: 1px solid #F29B38;
        }
        QComboBox::drop-down, QDateEdit::drop-down {
            border: 0px;
            width: 22px;
        }
        QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background: #F7F2EC;
            border-left: 1px solid #D9CCBE;
            min-width: 20px;
        }
        QComboBox::drop-down:hover, QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
            background: #EFE6DC;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            border-bottom: 1px solid #D9CCBE;
        }
        QComboBox QAbstractItemView {
            background: #FFFFFF;
            color: #2B2B2B;
            border: 1px solid #D2C4B6;
            selection-background-color: #FBECDD;
            selection-color: #1F2937;
            outline: 0;
            show-decoration-selected: 1;
            alternate-background-color: #FFF8EF;
        }
        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 5px 10px;
            border-bottom: 1px solid #E9DED2;
        }
        QComboBox QAbstractItemView::item:last {
            border-bottom: none;
        }

        /* === 按鈕 === */
        QPushButton {
            padding: 5px 12px;
            border: 1px solid #E6D8C7;
            border-radius: 8px;
            background: #FFFFFF;
            color: #2B2B2B;
        }
        QPushButton:hover {
            border: 1px solid #F0B060;
            background: #FFF7EE;
        }
        QPushButton:pressed {
            background: #FDEBD0;
        }
        QPushButton:disabled {
            color: #9E9E9E;
            background: #F3EFEA;
            border: 1px solid #E0D8CF;
        }

        /* === 表格 === */
        QTableWidget {
            border: 1px solid #E6D8C7;
            border-radius: 0px;
            gridline-color: #F0ECE6;
            background: #FFFFFF;
            alternate-background-color: #FFF9F3;
        }

        QTableWidget::item:selected {
            background: #FFF3E3;
            color: #2B2B2B;
        }
        QHeaderView::section {
            background: #FAF5EF;
            border: none;
            border-bottom: 1px solid #E6D8C7;
            padding: 6px 8px;
            font-weight: 600;
            color: #5A4A3A;
        }

        /* === 標籤 === */
        QLabel {
            background: transparent;
            border: none;
        }

        /* === GroupBox（戶長/戶員明細等） === */
        QGroupBox {
            border: 1px solid #E6D8C7;
            border-radius: 0px;
            margin-top: 6px;
            padding-top: 18px;
            background: transparent;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 8px;
            color: #5A4A3A;
            font-weight: 600;
        }

        /* === TabWidget（收入/支出分頁等） === */
        QTabWidget::pane {
            border: 1px solid #E6D8C7;
            border-radius: 6px;
            background: #FFFFFF;
        }
        QTabBar::tab {
            padding: 6px 16px;
            border: 1px solid #E6D8C7;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            background: #FAF5EF;
            color: #5A4A3A;
        }
        QTabBar::tab:selected {
            background: #FFFFFF;
            font-weight: 600;
        }
        QTabBar::tab:hover:!selected {
            background: #FFF7EE;
        }

        /* === ListWidget（搜尋結果等） === */
        QListWidget {
            border: 1px solid #DADADA;
            border-radius: 6px;
            background: #FFFFFF;
        }
        QListWidget::item {
            padding: 4px 8px;
        }
        QListWidget::item:selected {
            background: #FFF3E3;
            color: #2B2B2B;
        }
        QListWidget::item:hover {
            background: #FFF7EE;
        }

        /* === 選單列 === */
        QMenuBar {
            background: #FAF5EF;
            border-bottom: 1px solid #E6D8C7;
            padding: 2px;
        }
        QMenuBar::item {
            padding: 6px 14px;
            border-radius: 6px;
        }
        QMenuBar::item:selected {
            background: #FFF7EE;
        }
        QMenu {
            background: #FFFFFF;
            border: 1px solid #E6D8C7;
            border-radius: 8px;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background: #FFF7EE;
        }

        /* === 分隔線 === */
        QFrame[frameShape="4"] {
            color: #E6E6E6;
        }

        /* === 滾動條 === */
        QScrollBar:vertical {
            width: 8px;
            background: transparent;
        }
        QScrollBar::handle:vertical {
            background: #D6CFC6;
            border-radius: 4px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: #C0B8AE;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            height: 10px;
            background: transparent;
        }
        QScrollBar::handle:horizontal {
            background: #D6CFC6;
            border-radius: 4px;
            min-width: 30px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #C0B8AE;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
    """)
    app.font_manager = GlobalFontManager(app)
    install_dialog_localizer(app)

    init_controller = AppController()
    try:
        scheduler_feature_flags = init_controller.get_scheduler_feature_settings()
        scheduler_db_path = getattr(init_controller, "db_path", None)
        scheduler_config_path = init_controller.get_scheduler_config_path()
    finally:
        try:
            init_controller.conn.close()
        except Exception:
            pass

    scheduler_service = SchedulerService(
        config_path=scheduler_config_path,
        feature_flags=scheduler_feature_flags,
        db_path_override=scheduler_db_path,
    )
    scheduler_service.start()
    app.scheduler_service = scheduler_service

    try:
        while True:
            login_dialog = LoginDialog()
            if login_dialog.exec_() != QDialog.Accepted:
                break  # 使用者取消登入 → 結束程式

            username = login_dialog.username
            role = login_dialog.role
            display_name = (getattr(login_dialog, "display_name", None) or "").strip()
            operator_name = f"{display_name}({username})" if display_name and display_name != username else username
            controller = AppController()
            main_window = MainWindow(username, role, controller)
            main_window.operator_name = operator_name
            main_window._is_logout = False
            main_window.showMaximized()
            app.exec_()

            # 檢查是否為「登出」→ 回到登入畫面；否則直接結束
            if not getattr(main_window, '_is_logout', False):
                break
    finally:
        scheduler_service.stop()
        app.scheduler_service = None

    sys.exit(0)

if __name__ == "__main__":
    run_app()
