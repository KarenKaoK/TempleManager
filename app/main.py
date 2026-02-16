# app/main.py
import sys
from PyQt5.QtWidgets import QApplication, QDialog
from app.controller.app_controller import AppController
from app.auth.login import LoginDialog
from app.main_window import MainWindow
from app.utils.font_manager import GlobalFontManager

def run_app():
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
    """)
    app.font_manager = GlobalFontManager(app)

    while True:
        login_dialog = LoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            break  # 使用者取消登入 → 結束程式

        username = login_dialog.username
        role = login_dialog.role
        controller = AppController()
        main_window = MainWindow(username, role, controller)
        main_window._is_logout = False
        main_window.showMaximized()
        app.exec_()

        # 檢查是否為「登出」→ 回到登入畫面；否則直接結束
        if not getattr(main_window, '_is_logout', False):
            break

    sys.exit(0)

if __name__ == "__main__":
    run_app()
