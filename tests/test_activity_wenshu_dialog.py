from unittest.mock import patch, MagicMock

from PyQt5.QtCore import Qt

from app.widgets.activity_detail_panel import WenshuPrintDialog


def test_wenshu_dialog_print_uses_activity_birthday_template(qtbot):
    rows = [
        {
            "person_name": "王小明",
            "person_birthday_ad": "1990/01/01",
            "person_birthday_lunar": "1989/12/05",
            "person_lunar_is_leap": 0,
            "person_address": "台北市",
        }
    ]
    mock_controller = MagicMock()
    dlg = WenshuPrintDialog(mock_controller, rows)
    qtbot.addWidget(dlg)

    dlg.chk_activity_birthday_format.setChecked(True)
    dlg.chk_apply_default_prayer.setChecked(True)
    dlg.edt_prayer_default.setText("平安順遂")
    dlg.tbl.item(0, 0).setCheckState(Qt.Checked)

    with patch("app.widgets.activity_detail_panel.PrintHelper.print_wenshu_report") as m:
        dlg._on_print()
        assert m.called
        kwargs = m.call_args.kwargs
        assert kwargs.get("template") == "activity_birthday"
        payload_rows = m.call_args.args[0]
        assert dlg.tbl.columnCount() == 5
        assert payload_rows[0]["name"] == "王小明"
        assert payload_rows[0]["prayer"] == "平安順遂"
        assert "農曆" in payload_rows[0]["birthday"]


def test_wenshu_dialog_apply_default_prayer_checkbox(qtbot):
    rows = [
        {
            "person_name": "王小明",
            "person_birthday_ad": "1990/01/01",
            "person_birthday_lunar": "",
            "person_lunar_is_leap": 0,
            "person_address": "台北市",
        }
    ]
    mock_controller = MagicMock()
    dlg = WenshuPrintDialog(mock_controller, rows)
    qtbot.addWidget(dlg)

    # 未勾選：payload prayer 應為空
    dlg.edt_prayer_default.setText("闔家平安")
    dlg.tbl.item(0, 0).setCheckState(Qt.Checked)
    with patch("app.widgets.activity_detail_panel.PrintHelper.print_wenshu_report") as m:
        dlg._on_print()
        payload_rows = m.call_args.args[0]
        assert payload_rows[0]["prayer"] == ""

    # 勾選後：payload prayer 應帶入上方預設祈求
    dlg.chk_apply_default_prayer.setChecked(True)
    assert dlg.tbl.item(0, 4).text() == "闔家平安"
    with patch("app.widgets.activity_detail_panel.PrintHelper.print_wenshu_report") as m:
        dlg._on_print()
        payload_rows = m.call_args.args[0]
        assert payload_rows[0]["prayer"] == "闔家平安"

    # 允許手動覆蓋該列祈求
    dlg.tbl.item(0, 4).setText("改為手動祈求")
    with patch("app.widgets.activity_detail_panel.PrintHelper.print_wenshu_report") as m:
        dlg._on_print()
        payload_rows = m.call_args.args[0]
        assert payload_rows[0]["prayer"] == "改為手動祈求"

def test_wenshu_dialog_save_prayer(qtbot):
    mock_controller = MagicMock()
    mock_controller.update_signup_prayer.return_value = True
    rows = [
        {
            "signup_id": "S123",
            "person_name": "王小明",
            "prayer": "原本的祈求"
        }
    ]
    dlg = WenshuPrintDialog(mock_controller, rows)
    qtbot.addWidget(dlg)
    
    # 勾選並修改祈求內容
    dlg.tbl.item(0, 4).setText("更新後的祈求")
    dlg.tbl.item(0, 0).setCheckState(Qt.Checked)
    
    with patch("app.widgets.activity_detail_panel.QMessageBox.information") as mock_msg:
        dlg._on_save_prayer()
        
    mock_controller.update_signup_prayer.assert_called_once_with("S123", "更新後的祈求")
    assert rows[0]["prayer"] == "更新後的祈求"
    assert mock_msg.called
