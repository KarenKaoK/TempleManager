from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QSpinBox, QVBoxLayout, QWidget


class SpinWithArrows(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        parent=None,
        *,
        spin_min_height: int = 30,
        button_width: int = 22,
        button_height: int = 14,
    ):
        super().__init__(parent)
        self.spinbox = QSpinBox(self)
        self.spinbox.setButtonSymbols(QSpinBox.NoButtons)
        self.spinbox.setAlignment(Qt.AlignCenter)
        self.spinbox.setReadOnly(False)
        self.spinbox.setKeyboardTracking(False)
        if self.spinbox.lineEdit():
            self.spinbox.lineEdit().setReadOnly(False)
            self.spinbox.lineEdit().setAlignment(Qt.AlignCenter)
        self.spinbox.setStyleSheet(
            f"""
            QSpinBox {{
                min-height: {spin_min_height}px;
                max-height: {spin_min_height}px;
                padding-right: 2px;
                border-radius: 6px;
            }}
            """
        )

        btn_up = QPushButton("▲", self)
        btn_dn = QPushButton("▼", self)
        for b in (btn_up, btn_dn):
            b.setFixedSize(button_width, button_height)
            b.setStyleSheet(
                """
                QPushButton {
                    background: #F4ECE3;
                    border: 1px solid #D8C2AA;
                    border-radius: 0px;
                    padding: 0px;
                    color: #5A3D29;
                    font-weight: 800;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #EEDFCC;
                    border: 1px solid #CFAE8D;
                }
                QPushButton:pressed {
                    background: #E6D0B6;
                }
                """
            )

        btn_up.clicked.connect(self.spinbox.stepUp)
        btn_dn.clicked.connect(self.spinbox.stepDown)

        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(0)
        btn_col.addWidget(btn_up)
        btn_col.addWidget(btn_dn)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        lay.addWidget(self.spinbox, 1)
        lay.addLayout(btn_col, 0)

        self.spinbox.valueChanged.connect(self.valueChanged.emit)

