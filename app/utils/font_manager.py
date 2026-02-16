import re

from PyQt5.QtCore import QObject, QSettings
from PyQt5.QtWidgets import QApplication


class GlobalFontManager(QObject):
    SIZE_MAP = {"小": 14, "中": 16, "大": 18}
    DEFAULT_LABEL = "中"
    BASE_SIZE = 16

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self.settings = QSettings("TempleManager", "TempleManager")
        self._base_app_stylesheet = app.styleSheet() or ""
        self.current_label = self._load_label()
        self.apply(self.current_label)

    def _load_label(self) -> str:
        label = self.settings.value("ui/font_size_label", self.DEFAULT_LABEL, type=str)
        return label if label in self.SIZE_MAP else self.DEFAULT_LABEL

    def get_label(self) -> str:
        return self.current_label

    def apply(self, label: str):
        if label not in self.SIZE_MAP:
            label = self.DEFAULT_LABEL

        self.current_label = label
        self.settings.setValue("ui/font_size_label", label)

        pt = self.SIZE_MAP[label]
        font = self.app.font()
        font.setPointSize(pt)
        self.app.setFont(font)

        # Use only app-level stylesheet scaling. Avoid runtime per-widget
        # mutation/event-filter hooks to keep Qt shutdown stable.
        self.app.setStyleSheet(self._scale_css(self._base_app_stylesheet, pt))

    def _scale_css(self, css: str, target_pt: int) -> str:
        if not css:
            return css
        delta = target_pt - self.BASE_SIZE

        def repl(m):
            raw = int(m.group(1))
            unit = m.group(2)
            new_size = max(8, raw + delta)
            return f"font-size: {new_size}{unit}"

        return re.sub(r"font-size\s*:\s*(\d+)\s*(px|pt)", repl, css)
