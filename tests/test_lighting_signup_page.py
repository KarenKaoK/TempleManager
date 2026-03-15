from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit

from app.widgets.lighting_signup_page import LightingSignupPage


class _FakeLightingController:
    def get_lighting_hint_settings(self):
        return {
            "year": "2026",
            "tai_sui_text": "犯太歲：馬（太歲）\n鼠（歲破）",
            "ji_gai_text": "祭改：龍（喪門）\n兔（男制太陰女制桃花）",
            "peaceful_text": "平安無沖：蛇（太陽）\n雞（吉星臨照）",
        }

    def _default_lighting_hint_texts(self, year):
        return self.get_lighting_hint_settings()

    def list_lighting_items(self, include_inactive=False):
        return []

    def list_lighting_signups(self, signup_year, keyword="", unpaid_only=False):
        return []

    def get_lighting_signup_item_totals(self, signup_year, keyword=""):
        return []


def test_lighting_hint_boxes_stay_single_line_and_scrollable(qtbot):
    page = LightingSignupPage(controller=_FakeLightingController())
    qtbot.addWidget(page)

    for widget in (page.txt_tai_sui_hint, page.txt_ji_gai_hint, page.txt_peaceful_hint):
        assert isinstance(widget, QTextEdit)
        assert widget.height() == 56
        assert widget.lineWrapMode() == QTextEdit.NoWrap
        assert widget.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
        assert widget.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        assert "\n" not in widget.toPlainText()
