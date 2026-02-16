import re
from PyQt5.QtCore import QObject, QEvent, QSettings
from PyQt5.QtWidgets import QApplication, QLabel, QDialog


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

        self.app.installEventFilter(self)
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

        f = self.app.font()
        f.setPointSize(pt)
        self.app.setFont(f)

        # Scale QApplication stylesheet once from its original source.
        self.app.setStyleSheet(self._scale_css(self._base_app_stylesheet, pt))

        for w in self.app.allWidgets():
            self._apply_widget_font(w, pt)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Show, QEvent.Polish):
            pt = self.SIZE_MAP.get(self.current_label, self.BASE_SIZE)
            self._apply_widget_font(obj, pt)
        return False

    def _apply_widget_font(self, widget, pt: int):
        if widget is None:
            return

        try:
            f = widget.font()
            f.setPointSize(pt)
            widget.setFont(f)
        except Exception:
            pass

        try:
            ss = widget.styleSheet()
            if ss:
                base_ss = widget.property("_base_stylesheet")
                if base_ss is None:
                    widget.setProperty("_base_stylesheet", ss)
                    base_ss = ss
                scaled_ss = self._scale_css(base_ss, pt)
                if scaled_ss != ss:
                    widget.setStyleSheet(scaled_ss)
        except Exception:
            pass

        # Dialog 視窗也跟著字體比例放大，避免字體變大後吃字
        if isinstance(widget, QDialog):
            try:
                base_size = widget.property("_base_dialog_size")
                if base_size is None:
                    base_size = (widget.width(), widget.height())
                    widget.setProperty("_base_dialog_size", base_size)
                bw, bh = base_size
                scale = pt / float(self.BASE_SIZE)
                nw = max(int(bw), int(bw * scale))
                nh = max(int(bh), int(bh * scale))
                widget.resize(nw, nh)
            except Exception:
                pass

        # 表格列高隨字體調整，避免內容裁切
        try:
            if hasattr(widget, "verticalHeader"):
                vh = widget.verticalHeader()
                if vh is not None:
                    vh.setDefaultSectionSize(max(24, pt + 14))
        except Exception:
            pass

        # Scale rich-text inline font-size for labels created before/after switch.
        if isinstance(widget, QLabel):
            txt = widget.text() or ""
            if "font-size" in txt and "<" in txt and ">" in txt:
                base_txt = widget.property("_base_rich_text")
                if base_txt is None:
                    widget.setProperty("_base_rich_text", txt)
                    base_txt = txt
                scaled_txt = self._scale_css(base_txt, pt)
                if scaled_txt != txt:
                    widget.setText(scaled_txt)

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
