from app.dialogs.account_management_dialog import AccountManagementDialog


class _FakeController:
    def list_users(self):
        return [
            {
                "username": "active_user",
                "display_name": "啟用使用者",
                "role": "工作人員",
                "is_active": 1,
                "created_at": "2026-01-01 10:00:00",
                "password_changed_at": "2026-01-01 10:00:00",
                "last_login_at": "2026-01-01 10:00:00",
            },
            {
                "username": "inactive_user",
                "display_name": "停用使用者",
                "role": "工作人員",
                "is_active": 0,
                "created_at": "2026-01-01 10:00:00",
                "password_changed_at": "2026-01-01 10:00:00",
                "last_login_at": "2026-01-01 10:00:00",
            },
        ]

    def get_password_reminder_days(self):
        return 30

    def get_idle_logout_minutes(self):
        return 15


def test_selected_is_active_reads_status_column_correctly(qtbot):
    dialog = AccountManagementDialog(controller=_FakeController(), actor_username="admin")
    qtbot.addWidget(dialog)

    dialog.table.selectRow(0)
    assert dialog._selected_is_active() is True

    dialog.table.selectRow(1)
    assert dialog._selected_is_active() is False
